#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import sys
import shutil
from typing import List, Optional
from fastapi.responses import FileResponse

# Import your privateGPT modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from new_private_gpt import create_qa_chain, process_query
from ingest import process_documents, does_vectorstore_exist

app = FastAPI(title="PrivateGPT API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve your front-end website
# Place your index.html and other static assets inside the "static" folder.
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Initialize the QA chain on startup
@app.on_event("startup")
async def startup_event():
    create_qa_chain()
    print("QA chain initialized")

# Models for request/response
class QueryRequest(BaseModel):
    query: str

class Document(BaseModel):
    content: str
    source: str

class QueryResponse(BaseModel):
    result: str
    source_documents: Optional[List[Document]] = None
    processing_time: Optional[float] = None

class IngestResponse(BaseModel):
    status: str
    documents_processed: int

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest = Body(...)):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        result = process_query(request.query)
        
        # Format the response
        response = {
            "result": result.get("result", ""),
            "processing_time": result.get("processing_time", 0)
        }
        
        # Include source documents if available
        if "source_documents" in result:
            response["source_documents"] = [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown Source")
                }
                for doc in result["source_documents"]
            ]
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-documents")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents to be processed by the ingest system.
    """
    source_dir = os.environ.get('SOURCE_DIRECTORY', 'source_documents')
    
    # Create the directory if it doesn't exist
    os.makedirs(source_dir, exist_ok=True)
    
    uploaded_files = []
    
    # Save each uploaded file
    for file in files:
        file_path = os.path.join(source_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": os.path.getsize(file_path),
            "path": file_path
        })
    
    return {
        "status": "success",
        "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
        "files": uploaded_files
    }

@app.post("/ingest", response_model=IngestResponse)
async def ingest():
    try:
        from langchain.embeddings import HuggingFaceEmbeddings
        from langchain.vectorstores import Chroma
        from constants import CHROMA_SETTINGS
        
        # Process documents from your source directory
        texts = process_documents()
        if not texts:
            return {
                "status": "no_documents",
                "documents_processed": 0
            }
        
        # Create embeddings using the specified model
        print("Creating embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name=os.environ.get("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
        )
        
        persist_directory = os.environ.get('PERSIST_DIRECTORY', 'db')
        
        # Create the vectorstore with your documents
        print(f"Creating vector database in {persist_directory}...")
        db = Chroma.from_documents(
            documents=texts,
            embedding=embeddings,
            persist_directory=persist_directory,
            client_settings=CHROMA_SETTINGS
        )
        
        # Persist the vectorstore to disk
        print("Persisting database...")
        db.persist()
        print("Database persisted successfully!")
        
        return {
            "status": "success",
            "documents_processed": len(texts)
        }
    
    except Exception as e:
        print(f"Error during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    persist_directory = os.environ.get('PERSIST_DIRECTORY', 'db')
    
    # Check if the database is initialized
    db_initialized = os.path.exists(persist_directory) and \
                     os.path.exists(os.path.join(persist_directory, 'chroma.sqlite3'))
    
    return {
        "database_initialized": db_initialized,
        "model": os.environ.get("MODEL", "mistral"),
        "embeddings_model": os.environ.get("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
