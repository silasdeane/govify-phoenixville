#!/usr/bin/env python3
import os
import glob
from typing import List
from multiprocessing import Pool
from tqdm import tqdm
import uuid
import time

# Import the correct version of Pinecone for direct API access
from pinecone import Pinecone, ServerlessSpec

# We still need these imports for document processing
from langchain.document_loaders import (
    CSVLoader,
    EverNoteLoader,
    PyMuPDFLoader,
    TextLoader,
    UnstructuredEmailLoader,
    UnstructuredEPubLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredODTLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from lanchain_pinecone_adapter import CustomHuggingFaceEmbeddings

# Load environment variables
pinecone_api_key = os.environ.get('PINECONE_API_KEY', 'pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e')
pinecone_environment = os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1')
index_name = os.environ.get('PINECONE_INDEX_NAME', 'phoenixville-municipal-code')
source_directory = os.environ.get('SOURCE_DIRECTORY', 'source_documents')
chunk_size = 500
chunk_overlap = 50

# Custom document loader for emails
class MyElmLoader(UnstructuredEmailLoader):
    """Wrapper to fallback to text/plain when default does not work"""
    def load(self) -> List[Document]:
        try:
            try:
                doc = UnstructuredEmailLoader.load(self)
            except ValueError as e:
                if 'text/html content not found in email' in str(e):
                    self.unstructured_kwargs["content_source"] = "text/plain"
                    doc = UnstructuredEmailLoader.load(self)
                else:
                    raise
        except Exception as e:
            raise type(e)(f"{self.file_path}: {e}") from e
        return doc

# Map file extensions to document loaders and their arguments
LOADER_MAPPING = {
    ".csv": (CSVLoader, {}),
    ".doc": (UnstructuredWordDocumentLoader, {}),
    ".docx": (UnstructuredWordDocumentLoader, {}),
    ".enex": (EverNoteLoader, {}),
    ".eml": (MyElmLoader, {}),
    ".epub": (UnstructuredEPubLoader, {}),
    ".html": (UnstructuredHTMLLoader, {}),
    ".md": (UnstructuredMarkdownLoader, {}),
    ".odt": (UnstructuredODTLoader, {}),
    ".pdf": (PyMuPDFLoader, {}),
    ".ppt": (UnstructuredPowerPointLoader, {}),
    ".pptx": (UnstructuredPowerPointLoader, {}),
    ".txt": (TextLoader, {"encoding": "utf8"}),
}

def load_single_document(file_path: str) -> List[Document]:
    ext = "." + file_path.rsplit(".", 1)[-1]
    if ext in LOADER_MAPPING:
        loader_class, loader_args = LOADER_MAPPING[ext]
        loader = loader_class(file_path, **loader_args)
        return loader.load()
    raise ValueError(f"Unsupported file extension '{ext}'")

def load_documents(source_dir: str, ignored_files: List[str] = []) -> List[Document]:
    all_files = []
    for ext in LOADER_MAPPING:
        all_files.extend(glob.glob(os.path.join(source_dir, f"**/*{ext}"), recursive=True))
    filtered_files = [file_path for file_path in all_files if file_path not in ignored_files]
    with Pool(processes=os.cpu_count()) as pool:
        results = []
        with tqdm(total=len(filtered_files), desc='Loading new documents', ncols=80) as pbar:
            for i, docs in enumerate(pool.imap_unordered(load_single_document, filtered_files)):
                results.extend(docs)
                pbar.update()
    return results

# Custom separators to capture municipal code structure
custom_separators = [
    "\nChapter ",   # Separate by chapter headings
    "\nPart ",      # Separate by parts within chapters
    "\n§ ",         # Separate by section symbol (common in codes)
    "\n"           # Fallback: newline
]

def extract_heading(text: str) -> str:
    # Look for common code markers in the first few lines
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Chapter") or stripped.startswith("Part") or stripped.startswith("§"):
            return stripped
    return "Unknown Section"

def initialize_pinecone():
    """Initialize Pinecone client and ensure the index exists"""
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Check if index already exists
    indexes = pc.list_indexes()
    if index_name not in indexes.names():
        # Create the index with appropriate dimension
        pc.create_index(
            name=index_name,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"Created new Pinecone index: {index_name}")
    
    return pc.Index(index_name)

def process_documents(ignored_files: List[str] = []) -> List[Document]:
    print(f"Loading documents from {source_directory}")
    documents = load_documents(source_directory, ignored_files)
    if not documents:
        print("No new documents to load")
        return []
    print(f"Loaded {len(documents)} new documents from {source_directory}")
    # Use our custom separators in the text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        separators=custom_separators
    )
    texts = text_splitter.split_documents(documents)
    # Attach metadata to each chunk
    for chunk in texts:
        heading = extract_heading(chunk.page_content)
        if not chunk.metadata:
            chunk.metadata = {}
        chunk.metadata["section_heading"] = heading
    print(f"Split into {len(texts)} chunks of text (max. {chunk_size} tokens each)")
    return texts

def does_index_exist() -> bool:
    """Check if Pinecone index exists"""
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        indexes = pc.list_indexes()
        return index_name in indexes.names()
    except Exception as e:
        print(f"Error checking Pinecone index: {e}")
        return False

def add_embeddings_to_pinecone(texts, embeddings_model):
    """Add document embeddings directly to Pinecone using the new API"""
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)
    
    # Process in smaller batches to avoid timeouts
    batch_size = 50
    total_vectors = len(texts)
    
    print(f"Adding {total_vectors} vectors to Pinecone in batches of {batch_size}")
    
    for i in range(0, total_vectors, batch_size):
        batch_end = min(i + batch_size, total_vectors)
        current_batch = texts[i:batch_end]
        
        # Generate IDs for the batch
        ids = [str(uuid.uuid4()) for _ in range(len(current_batch))]
        
        # Create embeddings for the texts
        texts_to_embed = [doc.page_content for doc in current_batch]
        embeddings = embeddings_model.embed_documents(texts_to_embed)
        
        # Create metadata
        metadatas = [doc.metadata for doc in current_batch]
    
        # Prepare vectors with enhanced metadata
        vectors = []
        for j, (id, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
            # Add the text content to metadata for retrieval
            metadata['text'] = texts_to_embed[j]
            
            # Add document type inference based on content
            if "Zoning Hearing Board" in texts_to_embed[j]:
                metadata['document_type'] = 'zoning_board'
            
            # Add more specific metadata extraction here
            
            vectors.append({
                'id': id,
                'values': embedding,
                'metadata': metadata
        })
        
        # Upsert to Pinecone
        index.upsert(vectors=vectors)
        
        print(f"Added batch {i//batch_size + 1}/{(total_vectors + batch_size - 1)//batch_size}")
    
    print(f"Successfully added {total_vectors} vectors to Pinecone")

def main():
    # Initialize embeddings
    try:
        # Try using our custom embeddings adapter for 1024 dimensions
        embeddings = CustomHuggingFaceEmbeddings()
        print("Using custom 1024-dimensional embeddings compatible with llama-text-embed-v2")
    except Exception as e:
        print(f"Error initializing custom embeddings: {e}")
        from langchain.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("Using standard HuggingFace embeddings model: all-MiniLM-L6-v2")
    
    # Check if index exists
    if does_index_exist():
        print(f"Appending to existing Pinecone index: {index_name}")
        
        # Process new documents
        texts = process_documents([])
        if not texts:
            print("No new documents to process")
            return
            
        print("Creating embeddings. May take some minutes...")
        add_embeddings_to_pinecone(texts, embeddings)
    else:
        print("Creating new Pinecone index")
        
        # Process documents
        texts = process_documents()
        if not texts:
            print("No documents to process")
            return
            
        print("Creating embeddings. May take some minutes...")
        # Initialize Pinecone index
        initialize_pinecone()
        
        # Add embeddings directly to Pinecone
        add_embeddings_to_pinecone(texts, embeddings)
    
    print("Ingestion complete! You can now run privateGPT.py to query your documents")
    
    print("Running specialized municipal document extractor...")
    import subprocess
    subprocess.run(["python", "pinecone_municipal_doc_extractor.py"])

if __name__ == "__main__":
    main()