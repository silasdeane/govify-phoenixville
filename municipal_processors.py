# Add this to your project
from langchain.text_splitter import RecursiveCharacterTextSplitter

def process_municipal_code(document):
    """Special processor for municipal code documents"""
    # Extract metadata
    metadata = {
        "source": document.metadata.get("source", "Unknown"),
        "document_type": "municipal_code",
    }
    
    # Custom chunking for code documents
    code_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\nChapter ", "\nPart ", "\n§ ", "\n"]
    )
    
    # Extract section information
    for chunk in code_splitter.split_documents([document]):
        # Extract section headings
        heading = extract_heading(chunk.page_content)
        chunk.metadata = {**metadata, "section_heading": heading}
        
    return chunks