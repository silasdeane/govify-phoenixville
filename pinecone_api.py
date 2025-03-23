#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import sys
import shutil
import random
from datetime import datetime
from typing import List, Optional
from fastapi.responses import FileResponse
from pinecone import Pinecone
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

class Document(BaseModel):
    content: str
    source: str

class QueryResponse(BaseModel):
    result: str
    source_documents: Optional[List[Document]] = None
    processing_time: Optional[float] = None
    map_data: Optional[dict] = None  # Add this line

class IngestResponse(BaseModel):
    status: str
    documents_processed: int

# Add this to your pinecone_api.py file, right after the imports and before the app definition

# Map-related keywords to detect map queries
MAP_KEYWORDS = [
    "where is", "location of", "map", "show me", "directions to", "zoning",
    "find", "show on map", "navigate to", "borough boundaries", "district map",
    "utility service", "water service area", "sewer service", "permits",
    "permit status"
]

# Add this to your pinecone_api.py file, right after the MAP_KEYWORDS and before the LOCATION_MAPPINGS

# Form-related keywords to detect permit form queries
FORM_KEYWORDS = [
    "permit", "application", "form", "apply for", "how do i get a", 
    "need a permit", "building permit", "construction permit", 
    "deck permit", "patio permit", "renovation permit", "demolition permit",
    "home improvement", "how to apply", "permit application"
]

# Mapping of form types to their details
FORM_MAPPINGS = {
    "deck": {
        "form_id": "deck-patio-permit",
        "title": "Deck/Patio Permit Application",
        "description": "Application for construction of a deck or patio"
    },
    "patio": {
        "form_id": "deck-patio-permit",
        "title": "Deck/Patio Permit Application",
        "description": "Application for construction of a deck or patio"
    },
   
}

def is_form_query(query: str) -> bool:
    """
    Check if the query is asking for permit form information.
    """
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in FORM_KEYWORDS)

def get_form_type(query: str) -> dict:
    """
    Determine which specific form the user is asking about.
    Returns form details if a match is found.
    """
    query_lower = query.lower()
    
    # First check for specific form types
    for form_type, details in FORM_MAPPINGS.items():
        if form_type in query_lower:
            return details
    
    # If no specific form type is mentioned, default to building permit
    # since it's the most general form
    return FORM_MAPPINGS["building"]

def generate_form_response(query: str) -> dict:
    """
    Generate a response for form-related queries.
    """
    form_details = get_form_type(query)
    
    # Create contextual message based on the query and form type
    message = f"Here's the {form_details['title']} you requested. You can fill it out directly or download it for submission to the Borough offices."
    
    # Create a form portal tag similar to the payment portal
    form_portal = f"<form_portal>{message}|{form_details['form_id']}|{form_details['title']}</form_portal>"
    
    # Return the response object
    return {
        "result": form_portal,
        "processing_time": 0.1,
        "source_documents": [],
        "form_data": form_details
    }

# Location-specific mapping for precise coordinates
LOCATION_MAPPINGS = {
    "borough hall": {"lat": 40.1308, "lng": -75.5146, "zoom": 18, "layer": "locations"},
    "police": {"lat": 40.1307, "lng": -75.5131, "zoom": 18, "layer": "locations"},
    "fire": {"lat": 40.1309, "lng": -75.5135, "zoom": 18, "layer": "locations"},
    "library": {"lat": 40.1306, "lng": -75.5172, "zoom": 18, "layer": "locations"},
    "reeves park": {"lat": 40.1337, "lng": -75.5171, "zoom": 17, "layer": "locations"},
    "black rock": {"lat": 40.1463, "lng": -75.5392, "zoom": 16, "layer": "locations"},
    "zoning": {"lat": 40.1308, "lng": -75.5146, "zoom": 14, "layer": "zoning"},
    "residential district": {"lat": 40.1300, "lng": -75.5130, "zoom": 15, "layer": "zoning"},
    "commercial district": {"lat": 40.1320, "lng": -75.5200, "zoom": 15, "layer": "zoning"},
    "historic district": {"lat": 40.1315, "lng": -75.5135, "zoom": 16, "layer": "zoning"},
    "industrial district": {"lat": 40.1275, "lng": -75.5050, "zoom": 16, "layer": "zoning"},
    "utility": {"lat": 40.1308, "lng": -75.5146, "zoom": 14, "layer": "utilities"},
    "water service": {"lat": 40.1308, "lng": -75.5146, "zoom": 14, "layer": "utilities"},
    "sewer": {"lat": 40.1308, "lng": -75.5146, "zoom": 14, "layer": "utilities"},
    "permits": {"lat": 40.1308, "lng": -75.5146, "zoom": 15, "layer": "permits"}
}

def is_map_query(query: str) -> bool:
    """
    Check if the query is asking for map-related information.
    """
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in MAP_KEYWORDS)

def get_location_focus(query: str) -> dict:
    """
    Determine if the query is focusing on a specific location.
    Returns map coordinates if a match is found.
    """
    query_lower = query.lower()
    
    for location, coords in LOCATION_MAPPINGS.items():
        if location in query_lower:
            return coords
    
    # Default to center of Phoenixville
    return {"lat": 40.1308, "lng": -75.5146, "zoom": 14, "layer": "locations"}

def generate_map_response(query: str) -> dict:
    """
    Generate a response for map-related queries.
    """
    location_focus = get_location_focus(query)
    
    # Create contextual message based on the query and location
    if "zoning" in query.lower():
        message = "Here's the zoning map for Phoenixville Borough. The colored areas represent different zoning districts."
        location_focus["layer"] = "zoning"
    elif "utility" in query.lower() or "water service" in query.lower() or "sewer" in query.lower():
        message = "Here's the utility service map for Phoenixville Borough. The shaded areas show water and sewer service coverage."
        location_focus["layer"] = "utilities"
    elif "permit" in query.lower():
        message = "Here's a map showing recent permits issued in Phoenixville Borough. Click on the markers for details about each permit."
        location_focus["layer"] = "permits"
    elif any(place in query.lower() for place in ["borough hall", "police", "fire", "library", "reeves park", "black rock"]):
        place = next((place for place in ["borough hall", "police", "fire", "library", "reeves park", "black rock"] if place in query.lower()), "")
        message = f"Here's the location of {place.title()} in Phoenixville Borough. You can click on the marker for more details."
    else:
        message = "Here's an interactive map of Phoenixville Borough. You can toggle between different map layers using the controls below the map."
    
    # Create a map portal tag similar to the payment portal
    map_portal = f"<map_portal>{message}</map_portal>"
    
    # Return the response object
    return {
        "result": map_portal,
        "processing_time": 0.1,
        "source_documents": [],
        "map_data": location_focus
    }

# Find the @app.post("/query") function in pinecone_api.py and update it as follows:



# First create the FastAPI app instance
app = FastAPI(title="Phoenixville Municipal AI")

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest = Body(...)):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Check if this is a payment-related query
    payment_keywords = ["pay water bill", "water bill payment", "pay my water", 
                      "how do i pay my water", "pay utility bill", "water payment"]
    
    # If the query contains payment keywords, return the payment portal indicator
    if any(keyword in request.query.lower() for keyword in payment_keywords):
        return {
            "result": "<payment_portal>I can help you pay your water bill right here. Please use the secure payment form below:</payment_portal>",
            "processing_time": 0.1,
            "source_documents": []
        }
    
    # Check if this is a form-related query
    if is_form_query(request.query):
        return generate_form_response(request.query)
    
    # Check if this is a map-related query
    if is_map_query(request.query):
        return generate_map_response(request.query)
    
    try:
        # Sanitize the query
        clean_query = request.query.strip()
        if not clean_query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        result = process_query(clean_query)
        
        # Format the response with better error handling
        response = {
            "result": str(result.get("result", "An error occurred during processing.")),
            "processing_time": result.get("processing_time", 0)
        }
        
        # Include source documents if available
        source_docs = []
        if "source_documents" in result and result["source_documents"]:
            for doc in result["source_documents"]:
                if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                    source_docs.append({
                        "content": str(doc.page_content),
                        "source": str(doc.metadata.get("source", "Unknown Source"))
                    })
            
        response["source_documents"] = source_docs
        
        return response
    
    except Exception as e:
        import traceback
        print(f"Error in query endpoint: {e}")
        print(traceback.format_exc())
        # Return a more user-friendly error
        return {
            "result": f"I encountered an error while processing your query. Please try again with a different question.",
            "processing_time": 0,
            "source_documents": []
        }

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files to serve your front-end website
app.mount("/static", StaticFiles(directory="static"), name="static")

# Define the payment request model
class PaymentRequest(BaseModel):
    account_number: str
    amount: float
    payment_method: str
    email: str

# Add the payment simulation endpoint
@app.post("/simulate-payment")
async def simulate_payment(request: PaymentRequest):
    """
    Simulates processing a water bill payment.
    No actual payment is processed - this is for demonstration only.
    """
    # This would connect to your payment processor in a real implementation
    # For now, just return a success response with a transaction ID
    return {
        "status": "success",
        "transaction_id": f"PHX-{random.randint(100000, 999999)}",
        "date": datetime.now().isoformat(),
        "amount": request.amount,
        "account_number": request.account_number
    }

# Import your privateGPT modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from pinecone_new_private_gpt import create_qa_chain, process_query
    from pinecone_ingest import process_documents, initialize_pinecone, does_index_exist
    from langchain.embeddings import HuggingFaceEmbeddings
    # Import our custom embeddings adapter
    from lanchain_pinecone_adapter import CustomHuggingFaceEmbeddings
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")

@app.get("/")
async def root():
    return FileResponse("static/modern-index.html")

# Load Pinecone configuration
pinecone_api_key = os.environ.get('PINECONE_API_KEY', 'pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e')
pinecone_environment = os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1')
index_name = os.environ.get('PINECONE_INDEX_NAME', 'phoenixville-municipal-code')

# Initialize the QA chain on startup
@app.on_event("startup")
async def startup_event():
    try:
        # Initialize Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if the index exists
        indexes = pc.list_indexes()
        index_exists = index_name in indexes.names()
        
        # If index exists, try to create QA chain
        if index_exists:
            print(f"Initializing QA chain with existing Pinecone index: {index_name}")
            try:
                create_qa_chain()
                print("QA chain initialized with Pinecone vectorstore")
            except Exception as e:
                print(f"Error initializing QA chain: {e}")
                print("You can still use the API, but you'll need to ingest documents first")
        else:
            print(f"Pinecone index '{index_name}' does not exist. Upload documents to create it.")
    except Exception as e:
        print(f"Error during startup: {e}")
        print("Application will start, but you may need to create a Pinecone index first")

# Models for request/response




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
        # Process documents from your source directory
        texts = process_documents()
        if not texts:
            return {
                "status": "no_documents",
                "documents_processed": 0
            }
        
        # Create embeddings using the specified model
        print("Creating embeddings...")
        try:
            # Try using our custom embeddings adapter for 1024 dimensions
            embeddings = CustomHuggingFaceEmbeddings()
            print("Using custom 1024-dimensional embeddings compatible with llama-text-embed-v2")
        except Exception as e:
            # Fall back to standard embeddings if there's any issue
            print(f"Error with custom embeddings: {e}")
            embeddings = HuggingFaceEmbeddings(
                model_name=os.environ.get("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
            )
            print(f"Using standard embeddings")
        
        # Initialize or get existing Pinecone index
        pc = Pinecone(api_key=pinecone_api_key)
        index = initialize_pinecone()
        
        # We'll use our custom function to add vectors directly to Pinecone
        # This is imported from pinecone_ingest.py
        from pinecone_ingest import add_embeddings_to_pinecone
        add_embeddings_to_pinecone(texts, embeddings)
        
        print("Vectors added to Pinecone successfully!")
        
        # Reinitialize the QA chain to use the updated vectorstore
        create_qa_chain()
        
        return {
            "status": "success",
            "documents_processed": len(texts)
        }
    
    except Exception as e:
        print(f"Error during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-documents")
async def analyze_documents():
    try:
        import subprocess
        result = subprocess.run(["python", "pinecone_municipal_doc_extractor.py"], 
                               capture_output=True, text=True)
        return {
            "status": "success",
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        print(f"Error during document analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    # Initialize Pinecone
    try:
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if the index exists
        indexes = pc.list_indexes()
        index_exists = index_name in indexes.names()
        
        # If index exists, get stats
        stats = None
        if index_exists:
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            
        return {
            "database_initialized": index_exists,
            "model": os.environ.get("MODEL", "mistral"),
            "embeddings_model": os.environ.get("EMBEDDINGS_MODEL_NAME", "llama-text-embed-v2"),
            "vector_count": stats.total_vector_count if stats else 0,
            "dimension": stats.dimension if stats else None,
            "index_fullness": stats.index_fullness if stats else 0,
            "namespaces": list(stats.namespaces.keys()) if stats and hasattr(stats, 'namespaces') else []
        }
    except Exception as e:
        print(f"Error checking Pinecone status: {e}")
        return {
            "database_initialized": False,
            "model": os.environ.get("MODEL", "mistral"),
            "embeddings_model": os.environ.get("EMBEDDINGS_MODEL_NAME", "llama-text-embed-v2"),
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)