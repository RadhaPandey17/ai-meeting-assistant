import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.path.join("downloads", "chroma_db")

_embeddings = None

def get_embeddings():
    """Lazy load HuggingFace embeddings model."""
    global _embeddings
    if _embeddings is None:
        print(f"Loading HuggingFace Embedding model: {EMBEDDING_MODEL_NAME}...")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        print("Embedding model loaded.")
    return _embeddings

def create_vector_store(documents: list[Document], collection_name: str = "meeting_transcript") -> Chroma:
    """
    Creates an in-memory or persisted Chroma vector store from text documents.
    """
    embeddings = get_embeddings()
    print(f"Creating Chroma vector store with {len(documents)} document chunks...")
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name
    )
    print("Vector store created successfully.")
    return vector_store
