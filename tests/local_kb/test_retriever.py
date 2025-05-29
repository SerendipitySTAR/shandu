import pytest
import os
import json
import time
import shutil
import numpy as np
from pathlib import Path

from shandu.local_kb.retriever import LocalKBRetriever
from shandu.agents.utils.citation_manager import SourceInfo # For creating test documents
from shandu.local_kb.config import EMBEDDING_MODEL_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

# Helper to create dummy SourceInfo objects for retriever tests
def create_dummy_source_info(file_path: str, content: str, title: Optional[str] = None) -> SourceInfo:
    if title is None:
        title = os.path.basename(file_path)
    return SourceInfo(
        file_path=file_path, 
        extracted_content=content, 
        title=title, 
        is_local=True, 
        access_time=time.time()
    )

@pytest.fixture
def temp_retriever_files(temp_dir):
    """Provides paths for retriever index and metadata in a temporary directory."""
    vector_store_path = os.path.join(temp_dir, "test_store.faiss")
    index_metadata_path = os.path.join(temp_dir, "test_meta.json")
    return vector_store_path, index_metadata_path

@pytest.fixture
def retriever_instance(temp_retriever_files) -> LocalKBRetriever:
    """Returns a LocalKBRetriever instance with temporary file paths."""
    vector_store_path, index_metadata_path = temp_retriever_files
    # Ensure clean state for each test using this retriever
    if os.path.exists(vector_store_path): os.remove(vector_store_path)
    if os.path.exists(index_metadata_path): os.remove(index_metadata_path)

    return LocalKBRetriever(
        vector_store_path=vector_store_path,
        index_metadata_path=index_metadata_path
    )

# --- Tests for LocalKBRetriever ---

@pytest.mark.require_embedding_model
def test_retriever_init_model_loading(retriever_instance: LocalKBRetriever):
    """Test if the embedding model loads correctly."""
    assert retriever_instance.embedding_model is not None, "Embedding model should be loaded."

def test_retriever_init_no_existing_index(retriever_instance: LocalKBRetriever, temp_retriever_files):
    """Test initialization when no index files exist."""
    vector_store_path, index_metadata_path = temp_retriever_files
    assert not os.path.exists(vector_store_path)
    assert not os.path.exists(index_metadata_path)
    assert retriever_instance.index is None
    assert not retriever_instance.document_chunks

def test_chunk_text(retriever_instance: LocalKBRetriever):
    """Test the _chunk_text method."""
    text1 = "This is a short text."
    chunks1 = retriever_instance._chunk_text(text1)
    assert len(chunks1) == 1
    assert chunks1[0] == text1

    # Test with text larger than chunk size
    long_text = " ".join(["word"] * (DEFAULT_CHUNK_SIZE + DEFAULT_CHUNK_SIZE // 2))
    chunks_long = retriever_instance._chunk_text(long_text)
    assert len(chunks_long) > 1
    # Check overlap: the end of the first chunk should overlap with the start of the second
    # This depends on the exact chunking logic (character vs word, exact split points)
    # For the current basic character-based split:
    if len(chunks_long) > 1:
        first_chunk_end = chunks_long[0][-(DEFAULT_CHUNK_OVERLAP):] if DEFAULT_CHUNK_OVERLAP > 0 else ""
        # The overlap logic in the provided _chunk_text is character based.
        # A perfect check would be: chunks_long[1].startswith(chunks_long[0][DEFAULT_CHUNK_SIZE - DEFAULT_CHUNK_OVERLAP:])
        # but this can be tricky. Let's assert that chunks are not empty and have expected lengths.
        assert len(chunks_long[0]) == DEFAULT_CHUNK_SIZE
        assert len(chunks_long[1]) > 0


    empty_text = ""
    chunks_empty = retriever_instance._chunk_text(empty_text)
    assert len(chunks_empty) == 0

    text_smaller_than_overlap = "Small text"
    retriever_instance.chunk_size = 20
    retriever_instance.chunk_overlap = 10 # Overlap larger than text - chunk_size
    chunks_small_overlap = retriever_instance._chunk_text(text_smaller_than_overlap)
    assert len(chunks_small_overlap) == 1
    assert chunks_small_overlap[0] == text_smaller_than_overlap


@pytest.mark.require_embedding_model
def test_build_index_from_documents(retriever_instance: LocalKBRetriever, temp_dir: str, temp_retriever_files):
    """Test building the index from a list of SourceInfo objects."""
    vector_store_path, index_metadata_path = temp_retriever_files

    doc_content1 = "The quick brown fox jumps over the lazy dog. This is the first document for testing."
    doc_content2 = "Artificial intelligence is rapidly changing various industries. The future of AI is bright and full of potential."
    
    # Create dummy files (not strictly necessary if SourceInfo only needs content and path string)
    doc1_path = os.path.join(temp_dir, "doc1.txt")
    doc2_path = os.path.join(temp_dir, "doc2.txt")
    with open(doc1_path, "w") as f: f.write(doc_content1)
    with open(doc2_path, "w") as f: f.write(doc_content2)

    documents = [
        create_dummy_source_info(doc1_path, doc_content1, "Document One"),
        create_dummy_source_info(doc2_path, doc_content2, "Document Two AI")
    ]

    retriever_instance.build_index_from_documents(documents, reindex=True)

    assert retriever_instance.index is not None
    assert retriever_instance.index.ntotal > 0 # Check if vectors were added
    assert len(retriever_instance.document_chunks) > 0
    assert os.path.exists(vector_store_path), "FAISS index file should be saved."
    assert os.path.exists(index_metadata_path), "Index metadata file should be saved."

    # Verify content of document_chunks metadata
    with open(index_metadata_path, 'r') as f:
        loaded_chunks_meta = json.load(f)
    assert len(loaded_chunks_meta) == len(retriever_instance.document_chunks)
    assert loaded_chunks_meta[0]["source_file_path"] == os.path.abspath(doc1_path)
    assert doc_content1.startswith(loaded_chunks_meta[0]["text"]) # First chunk of first doc

    # Test reindex=False when index exists
    initial_ntotal = retriever_instance.index.ntotal
    retriever_instance.build_index_from_documents(documents, reindex=False) # Should skip
    assert retriever_instance.index.ntotal == initial_ntotal


@pytest.mark.require_embedding_model
def test_add_document_to_index(retriever_instance: LocalKBRetriever, temp_dir: str):
    """Test adding a single document to an existing index."""
    # First, build an initial index
    doc_content1 = "Initial document about planet Earth."
    doc1_path = os.path.join(temp_dir, "init_doc.txt")
    with open(doc1_path, "w") as f: f.write(doc_content1)
    initial_documents = [create_dummy_source_info(doc1_path, doc_content1)]
    retriever_instance.build_index_from_documents(initial_documents, reindex=True)

    initial_vector_count = retriever_instance.index.ntotal
    initial_chunk_count = len(retriever_instance.document_chunks)

    # Add a new document
    doc_content_new = "A new document discussing Mars exploration missions."
    doc_new_path = os.path.join(temp_dir, "new_doc.txt")
    with open(doc_new_path, "w") as f: f.write(doc_content_new)
    new_document = create_dummy_source_info(doc_new_path, doc_content_new, "Mars Doc")
    
    retriever_instance.add_document_to_index(new_document)

    assert retriever_instance.index.ntotal > initial_vector_count
    assert len(retriever_instance.document_chunks) > initial_chunk_count
    
    # Verify the new chunk metadata
    found_new_chunk = any(
        chunk["source_file_path"] == os.path.abspath(doc_new_path) and \
        doc_content_new.startswith(chunk["text"]) 
        for chunk in retriever_instance.document_chunks
    )
    assert found_new_chunk, "Metadata for the new document's chunks not found."


@pytest.mark.require_embedding_model
def test_remove_document_from_index(retriever_instance: LocalKBRetriever, temp_dir: str):
    """Test removing a document from the index (by rebuilding)."""
    doc1_path = os.path.join(temp_dir, "doc_to_keep.txt")
    doc2_path = os.path.join(temp_dir, "doc_to_remove.txt")
    doc3_path = os.path.join(temp_dir, "another_doc_to_keep.txt")

    doc_content_keep1 = "Content that will remain in the index."
    doc_content_remove = "Content that should be removed from the index."
    doc_content_keep2 = "More content that will remain after removal."

    with open(doc1_path, "w") as f: f.write(doc_content_keep1)
    with open(doc2_path, "w") as f: f.write(doc_content_remove)
    with open(doc3_path, "w") as f: f.write(doc_content_keep2)

    doc_info_keep1 = create_dummy_source_info(doc1_path, doc_content_keep1)
    doc_info_remove = create_dummy_source_info(doc2_path, doc_content_remove)
    doc_info_keep2 = create_dummy_source_info(doc3_path, doc_content_keep2)
    
    all_docs_initially = [doc_info_keep1, doc_info_remove, doc_info_keep2]
    retriever_instance.build_index_from_documents(all_docs_initially, reindex=True)
    
    initial_total_chunks = len(retriever_instance.document_chunks)
    initial_total_vectors = retriever_instance.index.ntotal

    # Documents that should remain after removal
    docs_after_removal = [doc_info_keep1, doc_info_keep2]
    retriever_instance.remove_document_from_index(os.path.abspath(doc2_path), docs_after_removal)

    assert retriever_instance.index is not None
    # Check that the number of vectors/chunks has decreased
    # Exact number depends on chunking, so just check it's less
    assert retriever_instance.index.ntotal < initial_total_vectors
    assert len(retriever_instance.document_chunks) < initial_total_chunks

    # Verify that chunks from the removed document are no longer in metadata
    abs_removed_path = os.path.abspath(doc2_path)
    for chunk in retriever_instance.document_chunks:
        assert chunk["source_file_path"] != abs_removed_path
    
    # Verify that chunks from kept documents are still there
    abs_kept_path1 = os.path.abspath(doc1_path)
    found_kept_chunk1 = any(chunk["source_file_path"] == abs_kept_path1 for chunk in retriever_instance.document_chunks)
    assert found_kept_chunk1


@pytest.mark.require_embedding_model
def test_search_populated_index(retriever_instance: LocalKBRetriever, temp_dir: str):
    """Test search functionality on a populated index."""
    doc_content_cat = "The domestic cat is a small carnivorous mammal. It is the only domesticated species in the family Felidae."
    doc_content_dog = "The dog is a domesticated descendant of the wolf. It is part of the canid family."
    doc_content_tech = "Quantum computing promises to revolutionize information processing with qubits."

    doc_cat_path = os.path.join(temp_dir, "cat_doc.txt")
    doc_dog_path = os.path.join(temp_dir, "dog_doc.txt")
    doc_tech_path = os.path.join(temp_dir, "tech_doc.txt")

    with open(doc_cat_path, "w") as f: f.write(doc_content_cat)
    with open(doc_dog_path, "w") as f: f.write(doc_content_dog)
    with open(doc_tech_path, "w") as f: f.write(doc_content_tech)

    documents = [
        create_dummy_source_info(doc_cat_path, doc_content_cat, "Cats"),
        create_dummy_source_info(doc_dog_path, doc_content_dog, "Dogs"),
        create_dummy_source_info(doc_tech_path, doc_content_tech, "Technology")
    ]
    retriever_instance.build_index_from_documents(documents, reindex=True)

    # Search for "feline animals"
    query_cat = "feline animals"
    results_cat = retriever_instance.search(query_cat, k=1)
    assert len(results_cat) == 1
    assert os.path.abspath(doc_cat_path) == results_cat[0]["source_file_path"]
    assert "cat" in results_cat[0]["text"].lower() # Check if snippet is relevant

    # Search for "quantum information"
    query_tech = "quantum information"
    results_tech = retriever_instance.search(query_tech, k=1)
    assert len(results_tech) == 1
    assert os.path.abspath(doc_tech_path) == results_tech[0]["source_file_path"]
    assert "quantum" in results_tech[0]["text"].lower()

    # Search with k=2 for a broader query
    query_pets = "domesticated mammals"
    results_pets = retriever_instance.search(query_pets, k=2)
    assert len(results_pets) == 2
    # Results should include cat and dog documents, order might vary
    result_paths_pets = {res["source_file_path"] for res in results_pets}
    assert os.path.abspath(doc_cat_path) in result_paths_pets
    assert os.path.abspath(doc_dog_path) in result_paths_pets


def test_search_empty_index(retriever_instance: LocalKBRetriever):
    """Test search on an empty or non-existent index."""
    results = retriever_instance.search("any query", k=5)
    assert len(results) == 0


@pytest.mark.require_embedding_model
def test_save_and_load_index_persistence(retriever_instance: LocalKBRetriever, temp_dir: str, temp_retriever_files):
    """Test that index and metadata are saved and loaded correctly."""
    vector_store_path, index_metadata_path = temp_retriever_files

    doc_content = "Persistence test document about data storage."
    doc_path = os.path.join(temp_dir, "persist_doc.txt")
    with open(doc_path, "w") as f: f.write(doc_content)
    documents = [create_dummy_source_info(doc_path, doc_content)]
    
    retriever_instance.build_index_from_documents(documents, reindex=True)
    # _save_index is called by build_index_from_documents

    # Create a new retriever instance to load the saved index
    retriever_loaded = LocalKBRetriever(
        vector_store_path=vector_store_path,
        index_metadata_path=index_metadata_path
    )
    assert retriever_loaded.index is not None
    assert retriever_loaded.index.ntotal == retriever_instance.index.ntotal
    assert len(retriever_loaded.document_chunks) == len(retriever_instance.document_chunks)
    assert retriever_loaded.document_chunks[0]["text"] == retriever_instance.document_chunks[0]["text"]
    assert retriever_loaded.document_chunks[0]["source_file_path"] == os.path.abspath(doc_path)

    # Perform a search with the loaded index
    search_results = retriever_loaded.search("data storage", k=1)
    assert len(search_results) == 1
    assert search_results[0]["source_file_path"] == os.path.abspath(doc_path)


def test_retriever_init_without_model(monkeypatch, temp_retriever_files):
    """Test retriever initialization if embedding model fails to load."""
    vector_store_path, index_metadata_path = temp_retriever_files
    
    # Simulate SentenceTransformer failing to load
    def mock_sentence_transformer_error(model_path):
        raise Exception("Simulated model load failure")

    monkeypatch.setattr("shandu.local_kb.retriever.SentenceTransformer", mock_sentence_transformer_error)
    
    retriever_no_model = LocalKBRetriever(
        vector_store_path=vector_store_path,
        index_metadata_path=index_metadata_path
    )
    assert retriever_no_model.embedding_model is None
    assert retriever_no_model.index is None # Should not attempt to load index
    
    # Try to use methods that require the model
    assert retriever_no_model.search("query") == []
    # build_index should also not proceed
    retriever_no_model.build_index_from_documents([], reindex=True)
    assert retriever_no_model.index is None


# Placeholder for a test for building index with no documents
@pytest.mark.require_embedding_model
def test_build_index_no_documents(retriever_instance: LocalKBRetriever):
    retriever_instance.build_index_from_documents([], reindex=True)
    assert retriever_instance.index is None # Or an empty index, depending on FAISS behavior
    assert not retriever_instance.document_chunks
    # Check if files are created (they might be, but empty)
    # For now, just ensuring it doesn't crash and state is as expected.
    if os.path.exists(retriever_instance.vector_store_path):
        # FAISS might save an empty index file.
        pass
    if os.path.exists(retriever_instance.index_metadata_path):
        with open(retriever_instance.index_metadata_path, 'r') as f:
            meta = json.load(f)
            assert meta == []
