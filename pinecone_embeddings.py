import os
import numpy as np
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

# Load environment variables
pinecone_api_key = os.environ.get('PINECONE_API_KEY', 'pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e')
pinecone_environment = os.environ.get('PINECONE_ENVIRONMENT', 'us-east-1')
index_name = os.environ.get('PINECONE_INDEX_NAME', 'phoenixville-municipal-code')

def initialize_embedding_model():
    """Initialize a SentenceTransformer model that's smaller but we'll adjust its output dimensions"""
    
    # Use a smaller model (about 90MB instead of 1.3GB)
    # This will be much faster to download
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    return model

def padded_embedding(model, text, target_dim=1024):
    """Create an embedding and pad it to the target dimension"""
    # Get the original embedding
    original_embedding = model.encode(text)
    original_dim = len(original_embedding)
    
    # Print the original dimension
    print(f"Original embedding dimension: {original_dim}")
    
    # If already at target dimension, return as is
    if original_dim == target_dim:
        return original_embedding
    
    # If smaller than target, pad with zeros
    if original_dim < target_dim:
        # Calculate padding needed
        padding_size = target_dim - original_dim
        
        # Create padded embedding
        padded = np.pad(original_embedding, (0, padding_size), 'constant')
        
        print(f"Padded embedding to {len(padded)} dimensions by adding {padding_size} zeros")
        return padded
    
    # If larger than target (unlikely), truncate
    if original_dim > target_dim:
        truncated = original_embedding[:target_dim]
        print(f"Truncated embedding from {original_dim} to {target_dim} dimensions")
        return truncated

def test_embedding_model():
    """Test the embedding model with padding to ensure it produces correct dimensions"""
    model = initialize_embedding_model()
    
    # Test with a simple text
    text = "This is a test document to check embedding dimensions."
    
    # Get padded embedding vector
    embedding = padded_embedding(model, text, target_dim=1024)
    
    # Print the dimension
    print(f"Final embedding dimension: {len(embedding)}")
    
    # Confirm if it matches what we need for Pinecone
    if len(embedding) == 1024:
        print("✅ Embedding dimension matches Pinecone index requirement (1024)")
    else:
        print(f"❌ Embedding dimension ({len(embedding)}) does not match Pinecone requirement (1024)")
    
    return embedding

def test_pinecone_connection():
    """Test connection to Pinecone using the new API"""
    try:
        # Initialize with new API
        pc = Pinecone(api_key=pinecone_api_key)
        
        print("✅ Successfully connected to Pinecone")
        
        # List available indexes
        indexes = pc.list_indexes()
        print(f"Available indexes: {indexes.names()}")
        
        if index_name in indexes.names():
            print(f"✅ Index '{index_name}' exists")
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            print(f"Index stats: {stats}")
        else:
            print(f"❌ Index '{index_name}' does not exist yet")
        
    except Exception as e:
        print(f"❌ Error connecting to Pinecone: {e}")

if __name__ == "__main__":
    print("Testing embedding model...")
    test_embedding_model()
    
    print("\nTesting Pinecone connection...")
    test_pinecone_connection()
    
    print("\n==== IMPORTANT ====")
    print("If both tests passed, you're ready to ingest documents.")
    print("Run: python pinecone_ingest.py")