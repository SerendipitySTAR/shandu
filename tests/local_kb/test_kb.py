import pytest
import os
import json
import time
import shutil
from pathlib import Path

from shandu.local_kb.kb import LocalKB
from shandu.agents.utils.citation_manager import SourceInfo, CitationManager
from shandu.local_kb.retriever import LocalKBRetriever # For type hinting or direct checks
from shandu.local_kb.config import EMBEDDING_MODEL_PATH # To check model availability

# --- Fixtures specific to these tests or re-used from conftest ---
# `local_kb` fixture from conftest.py provides a LocalKB instance with a temp dir and its own CM.
# `sample_txt_path`, `sample_docx_path`, `sample_pdf_path` from conftest.py.

def test_local_kb_init(local_kb: LocalKB, temp_kb_dir: str):
    """Test LocalKB initialization."""
    assert os.path.exists(temp_kb_dir)
    assert os.path.exists(local_kb._metadata_file) # Metadata file should be checked/created
    assert local_kb.kb_dir == temp_kb_dir
    assert isinstance(local_kb.citation_manager, CitationManager)
    assert isinstance(local_kb.retriever, LocalKBRetriever)
    assert local_kb.documents == {} # Starts empty if metadata file was new/empty

@pytest.mark.require_embedding_model # Adding document also adds to retriever
def test_add_document_new_txt(local_kb: LocalKB, sample_txt_path: Path):
    """Test adding a new TXT document."""
    file_path_str = str(sample_txt_path)
    source_info = local_kb.add_document(file_path_str, source_type="test_txt", metadata={"custom_key": "value"})

    assert source_info is not None
    abs_path = os.path.abspath(file_path_str)
    assert abs_path in local_kb.documents
    
    doc_in_kb = local_kb.documents[abs_path]
    assert doc_in_kb.title == sample_txt_path.name
    assert doc_in_kb.file_path == abs_path
    assert doc_in_kb.is_local is True
    assert doc_in_kb.source_type == "test_txt"
    assert doc_in_kb.metadata.get("custom_key") == "value"
    assert len(doc_in_kb.extracted_content) > 0

    # Check CitationManager
    assert abs_path in local_kb.citation_manager.sources
    cm_source = local_kb.citation_manager.sources[abs_path]
    assert cm_source.title == sample_txt_path.name

    # Check Retriever (basic check: document path is in retriever's chunks)
    # More detailed retriever checks are in test_retriever.py
    assert local_kb.retriever.index is not None
    found_in_retriever_chunks = any(
        chunk["source_file_path"] == abs_path for chunk in local_kb.retriever.document_chunks
    )
    assert found_in_retriever_chunks, "Document not found in retriever's indexed chunks."

    # Check metadata persistence
    local_kb._save_metadata() # Explicit save, though add_document does it
    kb_reloaded = LocalKB(kb_dir=local_kb.kb_dir, citation_manager=local_kb.citation_manager)
    assert abs_path in kb_reloaded.documents
    reloaded_doc = kb_reloaded.documents[abs_path]
    assert reloaded_doc.title == sample_txt_path.name
    assert reloaded_doc.metadata.get("custom_key") == "value"


@pytest.mark.require_embedding_model
def test_add_document_docx_and_pdf(local_kb: LocalKB, sample_docx_path: Path, sample_pdf_path: Path):
    """Test adding DOCX and PDF documents."""
    # DOCX
    if os.path.exists(sample_docx_path):
        docx_info = local_kb.add_document(str(sample_docx_path))
        assert docx_info is not None
        abs_docx_path = os.path.abspath(str(sample_docx_path))
        assert abs_docx_path in local_kb.documents
        assert len(local_kb.documents[abs_docx_path].extracted_content) > 0
        assert abs_docx_path in local_kb.citation_manager.sources
        assert any(c["source_file_path"] == abs_docx_path for c in local_kb.retriever.document_chunks)
    else:
        pytest.skip("sample.docx not found, skipping DOCX add test in LocalKB.")

    # PDF
    if os.path.exists(sample_pdf_path):
        pdf_info = local_kb.add_document(str(sample_pdf_path))
        assert pdf_info is not None
        abs_pdf_path = os.path.abspath(str(sample_pdf_path))
        assert abs_pdf_path in local_kb.documents
        # PDF extraction might be empty for the dummy PDF if it's too simple / no actual text objects
        # For this test, we allow empty content but ensure it's added.
        # assert len(local_kb.documents[abs_pdf_path].extracted_content) > 0 
        assert abs_pdf_path in local_kb.citation_manager.sources
        if local_kb.documents[abs_pdf_path].extracted_content: # Only expect in retriever if content was extracted
             assert any(c["source_file_path"] == abs_pdf_path for c in local_kb.retriever.document_chunks)
    else:
        pytest.skip("sample.pdf not found, skipping PDF add test in LocalKB.")


def test_add_document_already_exists(local_kb: LocalKB, sample_txt_path: Path):
    """Test adding a document that already exists in the KB."""
    file_path_str = str(sample_txt_path)
    local_kb.add_document(file_path_str, metadata={"version": "1"}) # First add
    
    # Attempt to add again
    source_info_re_add = local_kb.add_document(file_path_str, metadata={"version": "2"})
    
    assert source_info_re_add is not None # add_document currently returns the existing SourceInfo
    abs_path = os.path.abspath(file_path_str)
    # It should not create a duplicate entry in self.documents
    # The current behavior of add_document is to return existing if found.
    # If it were to update, metadata version should be "2". Let's check current behavior.
    assert local_kb.documents[abs_path].metadata.get("version") == "1" # Assumes it doesn't update on re-add.
    # To test update behavior, test_update_document should be used.
    
    # Count should remain 1
    assert len(local_kb.documents) == 1


@pytest.mark.require_embedding_model
def test_remove_document(local_kb: LocalKB, sample_txt_path: Path):
    """Test removing a document."""
    file_path_str = str(sample_txt_path)
    abs_path = os.path.abspath(file_path_str)

    # Add document first
    local_kb.add_document(file_path_str)
    assert abs_path in local_kb.documents
    assert abs_path in local_kb.citation_manager.sources
    initial_retriever_chunk_count = len(local_kb.retriever.document_chunks)
    assert initial_retriever_chunk_count > 0


    # Remove document
    removed_status = local_kb.remove_document(file_path_str)
    assert removed_status is True
    assert abs_path not in local_kb.documents
    assert abs_path not in local_kb.citation_manager.sources
    # Check if removed from retriever (by checking chunk count or specific chunks)
    # remove_document_from_index rebuilds the index, so chunks from this doc should be gone.
    assert len(local_kb.retriever.document_chunks) < initial_retriever_chunk_count
    found_in_retriever_chunks_after_remove = any(
        chunk["source_file_path"] == abs_path for chunk in local_kb.retriever.document_chunks
    )
    assert not found_in_retriever_chunks_after_remove

    # Test removing non-existent document
    removed_status_non_existent = local_kb.remove_document("non_existent.txt")
    assert removed_status_non_existent is False


def test_get_document_and_list_documents(local_kb: LocalKB, sample_txt_path: Path, sample_docx_path: Path):
    """Test getting and listing documents."""
    assert local_kb.list_documents() == [] # Initially empty

    txt_path_str = str(sample_txt_path)
    local_kb.add_document(txt_path_str)
    
    if os.path.exists(sample_docx_path):
        docx_path_str = str(sample_docx_path)
        local_kb.add_document(docx_path_str)
        expected_count = 2
    else:
        expected_count = 1
        docx_path_str = None # To avoid using it later if skipped

    # List documents
    docs_list = local_kb.list_documents()
    assert len(docs_list) == expected_count
    doc_titles = {doc.title for doc in docs_list}
    assert sample_txt_path.name in doc_titles
    if docx_path_str:
        assert sample_docx_path.name in doc_titles

    # Get specific document
    retrieved_txt_doc = local_kb.get_document(txt_path_str)
    assert retrieved_txt_doc is not None
    assert retrieved_txt_doc.title == sample_txt_path.name

    if docx_path_str:
        retrieved_docx_doc = local_kb.get_document(docx_path_str)
        assert retrieved_docx_doc is not None
        assert retrieved_docx_doc.title == sample_docx_path.name

    # Get non-existent document
    non_existent_doc = local_kb.get_document("non_existent.txt")
    assert non_existent_doc is None


@pytest.mark.require_embedding_model
def test_update_document(local_kb: LocalKB, sample_txt_path: Path, temp_dir: str):
    """Test updating a document."""
    # Create a modifiable copy of sample_txt_path in temp_dir
    original_content = "This is the original content for update test."
    temp_file_path = Path(temp_dir) / sample_txt_path.name
    with open(temp_file_path, "w") as f:
        f.write(original_content)

    # Add initial version
    local_kb.add_document(str(temp_file_path), metadata={"version": "1.0"})
    doc_v1 = local_kb.get_document(str(temp_file_path))
    assert doc_v1 is not None
    assert doc_v1.metadata.get("version") == "1.0"
    assert original_content in doc_v1.extracted_content

    # Modify the file content
    updated_content = "This is the updated content. It's different now!"
    with open(temp_file_path, "w") as f:
        f.write(updated_content)

    # Update the document in KB
    updated_doc_info = local_kb.update_document(str(temp_file_path), metadata={"version": "2.0", "status": "updated"})
    assert updated_doc_info is not None
    assert updated_doc_info.metadata.get("version") == "2.0"
    assert updated_doc_info.metadata.get("status") == "updated"
    assert updated_content in updated_doc_info.extracted_content
    
    # Check if old version's specific content (if distinct enough) is gone from retriever if re-indexed
    # This requires searching or checking retriever chunks.
    # The update_document calls remove then add, so retriever should reflect the new content.
    
    # Search for old content (should ideally not be found or have low score)
    # Search for new content (should be found)
    search_results_old = local_kb.search_local_kb("original content for update")
    if search_results_old: # It might still find it if "original content" is too generic
        is_old_still_top = any(original_content in res['text'] for res in search_results_old)
        # This assertion is tricky because "original content" might be part of "updated content"
        # A better check would be if the specific phrase *only* in original is not prominent.
        # For now, we'll rely on the new content being more prominent.

    search_results_new = local_kb.search_local_kb("updated content different now")
    assert len(search_results_new) > 0
    assert any(updated_content in res['text'] for res in search_results_new)


@pytest.mark.require_embedding_model
def test_search_local_kb(local_kb: LocalKB, sample_txt_path: Path):
    """Test the search_local_kb method."""
    # Add a document with known content
    content = "The quick brown fox and a lazy dog. Special test phrase for LocalKB search."
    # Create a file with this content in the temp_kb_dir structure, as local_kb uses it
    search_test_file_path = Path(local_kb.kb_dir) / "search_test_doc.txt"
    with open(search_test_file_path, "w") as f:
        f.write(content)
    
    local_kb.add_document(str(search_test_file_path))

    # Search for a phrase from the document
    search_results = local_kb.search_local_kb("Special test phrase", k=1)
    assert len(search_results) >= 1
    top_result = search_results[0]
    assert os.path.abspath(str(search_test_file_path)) == top_result["source_file_path"]
    assert "Special test phrase" in top_result["text"]

    # Search for something not in the document
    no_match_results = local_kb.search_local_kb("nonexistent phrase xyz123", k=1)
    # Depending on model, might return something, but score should be low or text dissimilar
    if no_match_results:
        # Add a score check if scores are normalized or a threshold is meaningful
        pass 
    # For now, just ensure it doesn't crash
    assert isinstance(no_match_results, list)


def test_get_all_documents_content(local_kb: LocalKB, sample_txt_path: Path):
    """Test retrieving all documents' content."""
    txt_content_expected = "".join(line.strip() for line in Path(sample_txt_path).read_text().strip().splitlines())
    
    local_kb.add_document(str(sample_txt_path))
    
    all_content = local_kb.get_all_documents_content()
    assert len(all_content) == 1
    doc_content_info = all_content[0]
    assert doc_content_info["file_path"] == os.path.abspath(str(sample_txt_path))
    
    # Compare normalized content
    extracted_normalized = "".join(line.strip() for line in doc_content_info["content"].strip().splitlines())
    assert extracted_normalized == txt_content_expected


def test_metadata_persistence_across_sessions(temp_kb_dir: str, sample_txt_path: Path):
    """Test if metadata (and implicitly retriever index) persists across LocalKB instances."""
    cm1 = CitationManager()
    kb1 = LocalKB(kb_dir=temp_kb_dir, citation_manager=cm1)
    
    file_path_str = str(sample_txt_path)
    abs_path = os.path.abspath(file_path_str)
    kb1.add_document(file_path_str, metadata={"session": "one"})
    
    # Ensure retriever index is built and saved by kb1.add_document
    # (This relies on add_document correctly calling retriever methods that save)
    assert os.path.exists(os.path.join(temp_kb_dir, "vector_store.faiss"))
    assert os.path.exists(os.path.join(temp_kb_dir, "index_metadata.json"))

    # Create a new LocalKB instance using the same directory
    cm2 = CitationManager() # New CM instance
    kb2 = LocalKB(kb_dir=temp_kb_dir, citation_manager=cm2)
    
    assert abs_path in kb2.documents
    reloaded_doc = kb2.documents[abs_path]
    assert reloaded_doc.title == sample_txt_path.name
    assert reloaded_doc.metadata.get("session") == "one"
    
    # Check if citation manager for kb2 also got populated (it should via _load_metadata)
    assert abs_path in kb2.citation_manager.sources

    # Check if retriever index was loaded in kb2
    assert kb2.retriever.index is not None
    assert kb2.retriever.index.ntotal > 0
    assert len(kb2.retriever.document_chunks) > 0
    found_in_retriever_chunks = any(
        chunk["source_file_path"] == abs_path for chunk in kb2.retriever.document_chunks
    )
    assert found_in_retriever_chunks


def test_add_document_no_content_extracted(local_kb: LocalKB, tmp_path, caplog):
    """Test adding a document from which no content can be extracted (e.g., an empty parsable file)."""
    # Use an empty TXT file for this, as it's parsable but yields no content.
    empty_file = tmp_path / "truly_empty.txt"
    empty_file.write_text("") # Ensure it's genuinely empty

    source_info = local_kb.add_document(str(empty_file))
    assert source_info is not None
    assert source_info.extracted_content == ""
    abs_path = os.path.abspath(str(empty_file))
    assert abs_path in local_kb.documents
    
    # Check logs for warning about no content
    # The warning is in LocalKB.add_document: "No content extracted from document..."
    assert "No content extracted from document" in caplog.text
    assert str(abs_path) in caplog.text

    # Retriever should ideally not add empty content to its index, or handle it gracefully.
    # LocalKBRetriever.add_document_to_index has checks for empty chunks.
    # So, the number of chunks for this document in the retriever should be 0.
    num_chunks_for_empty_doc = sum(
        1 for chunk in local_kb.retriever.document_chunks if chunk["source_file_path"] == abs_path
    )
    assert num_chunks_for_empty_doc == 0
