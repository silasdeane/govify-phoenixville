#!/usr/bin/env python3
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma
from langchain.llms import Ollama
import os
import time
from constants import CHROMA_SETTINGS

# Global configuration
model = os.environ.get("MODEL", "mistral")
embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
persist_directory = os.environ.get("PERSIST_DIRECTORY", "db")
target_source_chunks = int(os.environ.get("TARGET_SOURCE_CHUNKS", 4))

# Global QA chain instance
qa_chain = None

def create_qa_chain(hide_source: bool = False, mute_stream: bool = False):
    """Initializes and returns the QA chain for processing queries."""
    global qa_chain
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": target_source_chunks})
    callbacks = [] if mute_stream else [StreamingStdOutCallbackHandler()]
    llm = Ollama(model=model, callbacks=callbacks)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=not hide_source
    )
    return qa_chain

def process_query(query: str):
    """
    Processes a query string using the QA chain and returns a dictionary
    with the answer, source documents, and processing time.
    """
    global qa_chain
    if qa_chain is None:
        # Initialize with default settings if not already done.
        qa_chain = create_qa_chain()
    if not query.strip():
        return {"result": "Please enter a valid query.", "source_documents": []}
    start = time.time()
    res = qa_chain(query)
    end = time.time()
    res["processing_time"] = end - start
    return res

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
