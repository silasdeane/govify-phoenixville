# Phoenixville AI Document Assistant

A customizable RAG (Retrieval-Augmented Generation) application to enable question-answering on municipal documents. This system uses Pinecone for vector storage, local embedding models, and Ollama for LLM integration, all in a self-contained environment without requiring external API calls.

## Overview

The Phoenixville AI Document Assistant is designed to allow municipal staff and citizens to upload, index, and query local government documents. The system processes various document formats, creates semantic embeddings, stores these in Pinecone vector database, and uses a local LLM via Ollama to generate responses based on retrieved relevant content.

![Screenshot of the application interface](path/to/screenshot.png)

## Features

- **Document Processing:** Support for multiple file formats (PDF, DOCX, TXT, CSV, etc.)
- **Vector Storage:** Secure storage and retrieval using Pinecone
- **Local Embeddings:** Uses HuggingFace's smaller embedding models with custom dimension adapter
- **Local LLM Integration:** Works with Ollama for self-hosted AI inference
- **Web Interface:** Modern, responsive UI with real-time feedback
- **Municipal Document Extraction:** Special handling for municipal codes, board documents, etc.
- **Namespace Management:** Proper organization of vector data
- **Real-time Progress Updates:** Streaming feedback during document processing

## System Requirements

- Python 3.9+
- Node.js (optional, for frontend development)
- Ollama with a compatible model (default: `mistral`)
- At least 8GB RAM
- 4GB disk space for models and dependencies

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/govify.git
cd govify
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r pinecone_requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the project root with:

```
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=phoenixville-kb
MODEL=mistral
EMBEDDINGS_MODEL_NAME=all-MiniLM-L6-v2
```

### 5. Install Ollama

Follow the instructions at [ollama.ai](https://ollama.ai) to install Ollama for your platform.

Pull the required model:

```bash
ollama pull mistral
```

## Running the Application

### 1. Start the API server

```bash
python pinecone_api.py
```

The server will start at http://localhost:8000.

### 2. Open in browser

Navigate to http://localhost:8000 in your web browser.

## Using the Application

### Document Management

1. **Upload Documents:**
   - Click "Upload Files" button
   - Select document files to upload
   - Click "Upload & Process"
   - Monitor real-time progress as documents are processed

2. **Clear Vector Database:**
   - To reset the system, use the provided script:
   ```bash
   python pinecone_clear_vectors.py
   ```

### Querying Documents

1. Type your question in the input field
2. Press Enter or click the send button
3. View the AI-generated response with source citations
4. Start a new conversation with the "New Chat" button

## Code Structure

- `pinecone_api.py`: FastAPI server and main application entry point
- `pinecone_ingest.py`: Document processing and vector database ingestion
- `pinecone_new_private_gpt.py`: Query processing and response generation
- `pinecone_clear_vectors.py`: Utility to clear vector database
- `municipal_processors.py`: Specialized document processors
- `pinecone_municipal_doc_extractor.py`: Entity extraction for municipal documents
- `lanchain_pinecone_adapter.py`: Custom embedding dimension adapter
- `pinecone_embeddings.py`: Embedding model initialization and testing
- `static/index.html`: Web interface

## Configuration Options

### Index Management

The system supports multiple Pinecone indexes. For consistency, it's recommended to use a single index name across all files:

- `phoenixville-kb`: Main knowledge base (default)
- `phoenixville-municipal-code`: Alternative index for municipal codes
- `phoenixville-gpt`: Alternative general-purpose index

To switch between indexes, update the `PINECONE_INDEX_NAME` environment variable or modify the default values in the code.

### Embedding Models

The system uses `all-MiniLM-L6-v2` by default but supports other HuggingFace models. The custom adapter pads embeddings to the required dimensions for Pinecone compatibility.

### LLM Models

The system uses Ollama with the `mistral` model by default. You can switch to other compatible models by:

1. Pulling the model with Ollama: `ollama pull <model_name>`
2. Setting the `MODEL` environment variable: `MODEL=llama2`

## Troubleshooting

### Namespace Issues

If vectors aren't being cleared properly, check which namespace they're stored in:

```python
stats = index.describe_index_stats()
print(f"Namespaces: {stats.namespaces}")
```

Then clear the specific namespace:

```python
index.delete(delete_all=True, namespace="ns1")
```

### Dimension Mismatch

If you get dimension errors, verify that:

1. Your Pinecone index is configured for the correct dimensions (1024 or 1536)
2. Your custom embedding adapter is using the same target dimension
3. All imports are using the same index name consistently

## Advanced Usage

### Custom Document Processors

Create specialized document processors for different document types by extending the code in `municipal_processors.py`.

### Real-time Progress Updates

The system implements streaming responses for document ingestion. Monitor progress in real-time through the web UI.

## Security Considerations

- The system stores your Pinecone API key in the code. For production use, move this to environment variables or secure storage.
- No data leaves your environment - all processing occurs locally.
- No API keys or credentials are exposed to users of the web interface.

## License

[Add your license information here]

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Uses [Pinecone](https://www.pinecone.io/) for vector storage
- Powered by [Ollama](https://ollama.ai/) for local LLM inference
- Embedding models from [Hugging Face](https://huggingface.co/)