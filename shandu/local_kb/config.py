# Configuration for Local Knowledge Base Retriever
import os

# Path to the sentence transformer model
# Ensure this path is correct and the model is accessible.
# Using an environment variable or a more robust configuration system might be preferable
# for production, but a hardcoded path is used here as per the prompt.
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "/media/sc/AI/self-llm/embed_model/sentence-transformers/all-MiniLM-L6-v2")

# Default paths for the FAISS index and its metadata
DEFAULT_VECTOR_STORE_PARENT_DIR = "local_kb_data"
DEFAULT_VECTOR_STORE_FILENAME = "vector_store.faiss"
DEFAULT_INDEX_METADATA_FILENAME = "index_metadata.json"

DEFAULT_VECTOR_STORE_PATH = os.path.join(DEFAULT_VECTOR_STORE_PARENT_DIR, DEFAULT_VECTOR_STORE_FILENAME)
DEFAULT_INDEX_METADATA_PATH = os.path.join(DEFAULT_VECTOR_STORE_PARENT_DIR, DEFAULT_INDEX_METADATA_FILENAME)

# Chunking parameters
DEFAULT_CHUNK_SIZE = 512 # Number of tokens or characters, depending on implementation
DEFAULT_CHUNK_OVERLAP = 64 # Number of tokens or characters for overlap

# Ensure the parent directory for vector store and metadata exists
os.makedirs(DEFAULT_VECTOR_STORE_PARENT_DIR, exist_ok=True)

# You can add checks here to ensure the embedding model path is valid if needed
# if not os.path.exists(EMBEDDING_MODEL_PATH):
#     raise FileNotFoundError(f"Embedding model not found at: {EMBEDDING_MODEL_PATH}. "
#                             "Please set the EMBEDDING_MODEL_PATH environment variable or update the config.")

# Logging level for retriever (optional)
# import logging
# RETRIEVER_LOG_LEVEL = logging.INFO
