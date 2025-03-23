#!/usr/bin/env python3
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from lanchain_pinecone_adapter import CustomHuggingFaceEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.llms import Ollama
from langchain.schema import Document, BaseRetriever
from typing import List, Dict, Any
import os
import time
from pinecone import Pinecone
from langchain.prompts import PromptTemplate

# Global configuration
model = os.environ.get("MODEL", "mistral")
embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL_NAME", "llama-text-embed-v2")
pinecone_api_key = os.environ.get("PINECONE_API_KEY", "pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e")
pinecone_environment = os.environ.get("PINECONE_ENVIRONMENT", "us-east-1")
index_name = os.environ.get("PINECONE_INDEX_NAME", "phoenixville-municipal-code")
target_source_chunks = int(os.environ.get("TARGET_SOURCE_CHUNKS", 10))

# Global QA chain instance
qa_chain = None

# Standalone functions to avoid setting any attributes on BaseRetriever subclasses
def get_documents_from_pinecone(query: str) -> List[Document]:
    """Query Pinecone for relevant documents."""
    try:
        # Initialize Pinecone client
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if index exists 
        indexes = pc.list_indexes()
        if index_name not in indexes.names():
            print(f"Index {index_name} not found")
            return []
            
        # Get the index
        index = pc.Index(index_name)
        
        # Initialize embeddings
        try:
            embedding_model = CustomHuggingFaceEmbeddings()
        except Exception as e:
            print(f"Error with custom embeddings: {e}")
            embedding_model = HuggingFaceEmbeddings(model_name=embeddings_model_name)
        
        # Create query embedding
        query_embedding = embedding_model.embed_query(query)
        
        # Convert to list if needed
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        
        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=target_source_chunks,
            include_metadata=True
        )
        
        # Convert to Documents
        documents = []
        for match in results.matches:
            if 'text' in match.metadata:
                page_content = match.metadata.pop('text')
                doc = Document(page_content=page_content, metadata=match.metadata)
                documents.append(doc)
            else:
                print(f"Warning: Missing text content in document {match.id}")
        
        return documents
    
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        import traceback
        traceback.print_exc()
        return []

# Class definition must be minimal with overridden _get_relevant_documents method
class MinimalRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Get documents relevant to the query."""
        return get_documents_from_pinecone(query)
        
def create_qa_chain(hide_source: bool = False, mute_stream: bool = False):
    """Initializes and returns the QA chain for processing queries."""
    global qa_chain
    
    try:
        # Create our minimal retriever
        retriever = MinimalRetriever()
        
        # Configure callbacks for the LLM
        callbacks = [] if mute_stream else [StreamingStdOutCallbackHandler()]
        
        # Initialize the LLM
        llm = Ollama(model=model, callbacks=callbacks)
        
        # Define a better prompt template that instructs the model to use the content directly
        prompt_template = """You are an AI assistant for answering questions about Phoenixville municipal documents.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say you don't know. DO NOT try to make up an answer.
If the answer is not contained within the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

When answering:
1. Be direct and factual - only provide information explicitly present in the context
2. If the information is incomplete, acknowledge the limitations of what you know
3. If you're unsure about any detail, express that uncertainty rather than guessing

Answer:"""

        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        # Create the QA chain with the custom prompt
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=not hide_source,
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        return qa_chain
    except Exception as e:
        print(f"Error creating QA chain: {e}")
        import traceback
        traceback.print_exc()
        raise

def process_query(query: str) -> Dict[str, Any]:
    """
    Processes a query string using the QA chain and returns a dictionary
    with the answer, source documents, and processing time.
    """
    global qa_chain
    if qa_chain is None:
        # Initialize with default settings if not already done.
        qa_chain = create_qa_chain()
        
    # Sanitize the query to prevent errors
    if not query or not isinstance(query, str):
        return {"result": "Please enter a valid query.", "source_documents": []}
        
    query = query.strip()
    if not query:
        return {"result": "Please enter a valid query.", "source_documents": []}
    
    try:
        start = time.time()
        res = qa_chain(query)
        end = time.time()
        res["processing_time"] = end - start
        return res
    except Exception as e:
        import traceback
        print(f"Error processing query: {e}")
        print(traceback.format_exc())
        return {"result": f"An error occurred while processing your query: {str(e)}", "source_documents": []}

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='privateGPT: Ask questions to your documents without an internet connection, using the power of LLMs.'
    )
    parser.add_argument("--hide-source", "-S", action='store_true',
                        help='Disable printing of source documents used for answers.')
    parser.add_argument("--mute-stream", "-M", action='store_true',
                        help='Disable the streaming StdOut callback for LLMs.')
    args = parser.parse_args()

    # Initialize the QA chain with desired settings.
    create_qa_chain(hide_source=args.hide_source, mute_stream=args.mute_stream)

    # CLI loop for interactive querying.
    while True:
        query = input("\nEnter a query: ")
        if query == "exit":
            break
        if query.strip() == "":
            continue
        res = process_query(query)
        answer = res.get('result', '')
        print("\n> Question:")
        print(query)
        print("\n> Answer:")
        print(answer)
        if not args.hide_source and res.get("source_documents"):
            for doc in res["source_documents"]:
                print("\n> " + doc.metadata.get("source", "Unknown Source") + ":")
                print(doc.page_content)

if __name__ == "__main__":
    main()