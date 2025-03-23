from langchain.vectorstores.base import VectorStore
from langchain.embeddings.base import Embeddings
from langchain.schema import Document, BaseRetriever
from typing import List, Optional, Any, Dict, Tuple, Iterable
from pinecone import Pinecone
import uuid

class PineconeVectorStore(VectorStore):
    """Adapter for using Pinecone with LangChain, compatible with Pinecone SDK v2+"""
    
    def __init__(
        self,
        pinecone_api_key: str,
        index_name: str,
        embedding: Embeddings,
        text_key: str = "text",
        namespace: Optional[str] = None
    ):
        """Initialize with Pinecone client"""
        self.embedding = embedding
        self.text_key = text_key
        self.namespace = namespace
        self.pinecone_api_key = pinecone_api_key
        self.index_name = index_name
        
        # Initialize the modern Pinecone client (v2+)
        pc = Pinecone(api_key=pinecone_api_key)
        self.index = pc.Index(index_name)
    
    def add_texts(
        self, 
        texts: Iterable[str], 
        metadatas: Optional[List[dict]] = None, 
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Add texts to the vectorstore.
        
        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of IDs to associate with the texts.
            
        Returns:
            List of IDs of the added texts.
        """
        # Generate embeddings for the texts
        embeddings = self.embedding.embed_documents(list(texts))
        
        # Process each text item
        vectors = []
        ids_out = []
        
        # If no IDs are provided, generate UUIDs
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # If no metadatas are provided, use empty dicts
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Create vectors
        for i, (text, embedding, metadata, id) in enumerate(zip(texts, embeddings, metadatas, ids)):
            # Include text in metadata
            metadata[self.text_key] = text
            
            # Create vector
            vector = {
                "id": id,
                "values": embedding,
                "metadata": metadata
            }
            
            vectors.append(vector)
            ids_out.append(id)
        
        # Upsert to Pinecone
        self.index.upsert(vectors=vectors, namespace=self.namespace)
        
        return ids_out
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        pinecone_api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        **kwargs: Any,
    ) -> "PineconeVectorStore":
        """Create a PineconeVectorStore from a list of texts.
        
        Args:
            texts: List of texts to add to the vectorstore.
            embedding: Embedding function to use to embed the texts.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of IDs to associate with the texts.
            pinecone_api_key: API key for Pinecone.
            index_name: Name of the Pinecone index to use.
            
        Returns:
            A new PineconeVectorStore containing the texts.
        """
        # Required parameters
        if pinecone_api_key is None:
            raise ValueError("pinecone_api_key is required")
        if index_name is None:
            raise ValueError("index_name is required")
        
        # Extract additional parameters
        text_key = kwargs.get("text_key", "text")
        namespace = kwargs.get("namespace", None)
        
        # Create the vectorstore
        vectorstore = cls(
            pinecone_api_key=pinecone_api_key,
            index_name=index_name,
            embedding=embedding,
            text_key=text_key,
            namespace=namespace
        )
        
        # Add the texts
        vectorstore.add_texts(texts, metadatas, ids)
        
        return vectorstore
    
    def similarity_search(
        self, query: str, k: int = 4, **kwargs
    ) -> List[Document]:
        """Search for similar documents to the query"""
        query_embedding = self.embedding.embed_query(query)
        
        # Convert numpy array to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        
        # Using the modern Pinecone API
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            namespace=self.namespace
        )
        
        # Convert to LangChain documents
        documents = []
        
        for match in results.matches:
            # Make sure the text content is in the metadata
            if self.text_key in match.metadata:
                page_content = match.metadata.pop(self.text_key)
                doc = Document(page_content=page_content, metadata=match.metadata)
                documents.append(doc)
            else:
                print(f"Warning: Missing text content in document {match.id}")
        
        return documents
    
    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs
    ) -> List[Tuple[Document, float]]:
        """Return documents and relevance scores in the range [0, 1]."""
        query_embedding = self.embedding.embed_query(query)
        
        # Convert numpy array to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
            
        # Using the modern Pinecone API
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            namespace=self.namespace
        )
        
        # Convert to LangChain documents with scores
        documents_with_scores = []
        
        for match in results.matches:
            # Make sure the text content is in the metadata
            if self.text_key in match.metadata:
                page_content = match.metadata.pop(self.text_key)
                doc = Document(page_content=page_content, metadata=match.metadata)
                # Scores are already between 0 and 1
                documents_with_scores.append((doc, match.score))
            else:
                print(f"Warning: Missing text content in document {match.id}")
        
        return documents_with_scores
    
    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20, lambda_mult: float = 0.5, **kwargs
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance."""
        # Not fully implemented - this is a placeholder that falls back to regular search
        print("Warning: MMR search not implemented for PineconeVectorStore, falling back to regular search")
        return self.similarity_search(query, k, **kwargs)
    
    # Custom retriever implementation compatible with newer LangChain versions
    def as_retriever(self, search_kwargs=None):
        """Create a retriever from this vectorstore"""
        search_kwargs = search_kwargs or {}
        
        # Create a simple retriever that delegates to our vectorstore
        class CustomRetriever(BaseRetriever):
            def __init__(self, vectorstore, search_kwargs):
                super().__init__()
                self.vectorstore = vectorstore
                self.search_kwargs = search_kwargs
            
            def get_relevant_documents(self, query):
                return self.vectorstore.similarity_search(query, **self.search_kwargs)
            
            async def aget_relevant_documents(self, query):
                # Synchronous fallback
                return self.get_relevant_documents(query)
        
        return CustomRetriever(self, search_kwargs)