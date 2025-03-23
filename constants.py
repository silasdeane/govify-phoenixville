# constants.py
import os
from chromadb.config import Settings

# Define the folder for storing documents
SOURCE_DIRECTORY = os.environ.get('SOURCE_DIRECTORY', 'source_documents')

# Define the folder for the database
PERSIST_DIRECTORY = os.environ.get('PERSIST_DIRECTORY', 'db')

# Chroma settings
CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    is_persistent=True
)