import os
import json
import re
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

# Step 1: Document Text Extraction and Processing
class DocumentProcessor:
    def __init__(self):
        self.documents = []
        
    def extract_text_from_pdf(self, text_content: str, source: str) -> Dict[str, Any]:
        """
        Process text extracted from PDF files.
        In a real implementation, you would use a PDF library like PyPDF2 or pdfplumber.
        
        For this example, we use the provided text content.
        """
        # Create document metadata
        document = {
            "source": source,
            "content": text_content,
            "date_processed": datetime.now().isoformat(),
            "metadata": {
                "type": "pdf",
                "filename": source,
                "department": self._extract_department(source, text_content),
                "topic": self._extract_topic(source, text_content),
            }
        }
        
        self.documents.append(document)
        return document
    
    def _extract_department(self, source: str, text: str) -> str:
        """Extract the department from the document"""
        if "HARB" in text or "Historical Architectural Review Board" in text:
            return "Historical Architectural Review Board"
        elif "Memorial Bench" in source:
            return "Borough Services"
        elif "Planning Commission" in text:
            return "Chester County Planning Commission"
        return "Unknown Department"
    
    def _extract_topic(self, source: str, text: str) -> str:
        """Extract the topic from the document"""
        if "Signs and Awnings" in text:
            return "Signs and Awnings Guidelines"
        elif "Memorial Bench" in source:
            return "Memorial Bench Program"
        elif "Planning Commission" in text:
            return "Planning Services"
        return "General Information"
    
    def chunk_documents(self, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Split documents into smaller chunks for better embedding and retrieval
        """
        all_chunks = []
        
        for doc in self.documents:
            content = doc["content"]
            chunks = self._split_text(content, max_chunk_size)
            
            for i, chunk in enumerate(chunks):
                chunk_doc = {
                    "source": doc["source"],
                    "content": chunk,
                    "chunk_id": i,
                    "total_chunks": len(chunks),
                    "metadata": doc["metadata"]
                }
                all_chunks.append(chunk_doc)
        
        return all_chunks
    
    def _split_text(self, text: str, max_chunk_size: int) -> List[str]:
        """
        Split text into chunks of approximately max_chunk_size characters,
        trying to break at paragraph or sentence boundaries
        """
        # First split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds the chunk size and we already have content,
            # save the current chunk and start a new one
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
                
            # If the current chunk is getting too big, we need to break it up by sentences
            while len(current_chunk) > max_chunk_size:
                # Try to find a sentence break
                sentence_match = re.search(r'[.!?]\s+', current_chunk[:max_chunk_size])
                if sentence_match:
                    split_point = sentence_match.end()
                    chunks.append(current_chunk[:split_point].strip())
                    current_chunk = current_chunk[split_point:]
                else:
                    # If no sentence break, just split at max_chunk_size
                    chunks.append(current_chunk[:max_chunk_size].strip())
                    current_chunk = current_chunk[max_chunk_size:]
        
        # Add the final chunk if there's content left
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks

# Step 2: Generate Embeddings
class EmbeddingGenerator:
    """
    Class to generate embeddings for text using an embedding model.
    
    In a real implementation, you would use a library like sentence-transformers,
    or connect to an API like OpenAI to generate embeddings.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        print(f"Initializing embedding model: {model_name}")
        # In a real implementation: 
        # self.model = SentenceTransformer(model_name)
        
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text - simplified version.
        
        In a real implementation, this would call:
        self.model.encode(text)
        
        For this example, we return a small random vector
        """
        # Simulate embedding by generating a small random vector (for demo only)
        # Real embeddings would typically be 384, 768, or 1536 dimensions
        np.random.seed(hash(text) % 2**32)
        return list(np.random.rand(384).astype(float))
    
    def embed_documents(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of document chunks
        """
        embedded_chunks = []
        
        for chunk in chunks:
            embedding = self.generate_embedding(chunk["content"])
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding["embedding"] = embedding
            embedded_chunks.append(chunk_with_embedding)
            
        return embedded_chunks

# Step 3: Pinecone Integration
class PineconeClient:
    """
    Class to handle interactions with Pinecone vector database.
    
    In a real implementation, you would use the Pinecone Python client.
    """
    
    def __init__(self, api_key: Optional[str] = None, environment: str = "us-west1-gcp"):
        self.api_key = api_key or os.environ.get("PINECONE_API_KEY", "your-api-key")
        self.environment = environment
        print(f"Initializing Pinecone client in {environment}")
        # In a real implementation:
        # import pinecone
        # pinecone.init(api_key=self.api_key, environment=self.environment)
        
    def create_index(self, index_name: str, dimension: int = 384, metric: str = "cosine"):
        """
        Create a new index in Pinecone.
        
        In a real implementation:
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(index_name, dimension=dimension, metric=metric)
        """
        print(f"Creating Pinecone index: {index_name} with dimension {dimension}")
        
    def get_index(self, index_name: str):
        """
        Get a reference to the Pinecone index.
        
        In a real implementation:
        return pinecone.Index(index_name)
        """
        print(f"Getting Pinecone index: {index_name}")
        return MockPineconeIndex(index_name)
        
    def upsert_documents(self, index, documents: List[Dict[str, Any]], batch_size: int = 100):
        """
        Insert documents into Pinecone index.
        
        In a real implementation, you would batch documents and use:
        index.upsert(vectors=vectors)
        """
        print(f"Upserting {len(documents)} documents to Pinecone")
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            vectors = [(doc["source"] + "-" + str(doc["chunk_id"]), 
                       doc["embedding"], 
                       {k: v for k, v in doc.items() if k != "embedding"})
                      for doc in batch]
            
            print(f"Upserting batch {i//batch_size + 1}/{len(documents)//batch_size + 1} with {len(vectors)} vectors")
            # In a real implementation:
            # index.upsert(vectors=vectors)
            
            # Mock implementation:
            index.upsert(vectors)

class MockPineconeIndex:
    """Mock Pinecone index for demonstration purposes only"""
    
    def __init__(self, name: str):
        self.name = name
        self.vectors = []
    
    def upsert(self, vectors):
        """Mock upsert method"""
        self.vectors.extend(vectors)
        print(f"Upserted {len(vectors)} vectors to {self.name}, total vectors: {len(self.vectors)}")
    
    def query(self, vector, top_k: int = 5, include_metadata: bool = True):
        """Mock query method"""
        print(f"Querying {self.name} for top {top_k} results")
        return {"matches": [{"id": v[0], "score": 0.9 - (i * 0.1), "metadata": v[2]} 
                           for i, v in enumerate(self.vectors[:top_k])]}

# Main workflow function
def process_phoenixville_documents(documents: List[Dict[str, str]], index_name: str = "phoenixville-docs"):
    """
    Process Phoenixville documents and load them into Pinecone.
    
    Args:
        documents: List of documents with "source" and "content" keys
        index_name: Name of the Pinecone index to create/use
    """
    # Step 1: Process documents
    processor = DocumentProcessor()
    for doc in documents:
        processor.extract_text_from_pdf(doc["content"], doc["source"])
    
    # Chunk documents for better embedding and retrieval
    chunks = processor.chunk_documents(max_chunk_size=1000)
    print(f"Created {len(chunks)} chunks from {len(processor.documents)} documents")
    
    # Step 2: Generate embeddings
    embedding_generator = EmbeddingGenerator()
    embedded_chunks = embedding_generator.embed_documents(chunks)
    print(f"Generated embeddings for {len(embedded_chunks)} chunks")
    
    # Step 3: Load into Pinecone
    pinecone_client = PineconeClient()
    pinecone_client.create_index(index_name, dimension=384)
    index = pinecone_client.get_index(index_name)
    pinecone_client.upsert_documents(index, embedded_chunks)
    
    return {
        "processed_documents": len(processor.documents),
        "chunks_created": len(chunks),
        "vectors_uploaded": len(embedded_chunks),
        "index_name": index_name
    }

# Helper function to search the Pinecone index
def search_phoenixville_docs(query: str, top_k: int = 5, index_name: str = "phoenixville-docs"):
    """
    Search the Pinecone index for documents matching the query.
    
    Args:
        query: The search query
        top_k: Number of results to return
        index_name: Name of the Pinecone index to search
    
    Returns:
        List of relevant document chunks with metadata
    """
    embedding_generator = EmbeddingGenerator()
    query_embedding = embedding_generator.generate_embedding(query)
    
    pinecone_client = PineconeClient()
    index = pinecone_client.get_index(index_name)
    
    # In a real implementation, you would:
    # results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
    
    # For this demo, we use the mock client:
    results = index.query(vector=query_embedding, top_k=top_k)
    
    return results["matches"]

# Example usage
if __name__ == "__main__":
    # Example document list (normally this would come from your PDF extraction)
    sample_documents = [
        {
            "source": "Guidelines_for_Signs_and_Awnings.pdf",
            "content": "Borough of Phoenixville Historical Architectural Review Board GUIDELINES FOR SIGNS AND AWNINGS..."
        },
        {
            "source": "Memorial_Bench_Order_Form.pdf",
            "content": "The Borough of Phoenixville 351 Bridge Street - 2nd Floor Phoenixville, PA 19460 Memorial Bench Order Form..."
        }
    ]
    
    # Process documents and load into Pinecone
    results = process_phoenixville_documents(sample_documents)
    print(f"Processing complete: {results}")
    
    # Example search query
    search_results = search_phoenixville_docs("What are the guidelines for signs in the historic district?")
    print(f"Search results: {search_results}")