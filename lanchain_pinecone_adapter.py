# Replace your current lanchain_pinecone_adapter.py with this improved version

from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
import numpy as np

class CustomHuggingFaceEmbeddings(Embeddings):
    """
    Enhanced implementation of Embeddings using HuggingFace's SentenceTransformers
    with dimension padding for Pinecone compatibility
    """
    
    def __init__(self, model_name="all-MiniLM-L6-v2", target_dim=1024):
        """Initialize with a SentenceTransformer model"""
        self.model = SentenceTransformer(model_name)
        self.target_dim = target_dim
    
    def _pad_embedding(self, embedding):
        """Pad or truncate embedding to target dimension"""
        current_dim = len(embedding)
        
        # If already correct dimension, return as is
        if current_dim == self.target_dim:
            return embedding
        
        # If smaller, pad with zeros
        if current_dim < self.target_dim:
            padding = np.zeros(self.target_dim - current_dim)
            return np.concatenate([embedding, padding])
            
        # If larger, truncate
        return embedding[:self.target_dim]
    
    def _preprocess_text(self, text):
        """Preprocess text for better embedding quality"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        return text
    
    def embed_documents(self, texts):
        """Embed a list of documents"""
        # Preprocess texts
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # Get embeddings
        embeddings = self.model.encode(processed_texts)
        
        # Pad embeddings to target dimension
        return [self._pad_embedding(emb) for emb in embeddings]
    
    def embed_query(self, text):
        """Embed a query"""
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Get embedding
        embedding = self.model.encode(processed_text)
        
        # Pad embedding to target dimension
        padded_embedding = self._pad_embedding(embedding)
        
        # Convert NumPy array to list before returning
        if hasattr(padded_embedding, 'tolist'):
            return padded_embedding.tolist()
        
        return padded_embedding