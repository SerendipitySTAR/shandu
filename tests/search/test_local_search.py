import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch

from shandu.search.local_search import LocalSearcher
from shandu.search.search import SearchResult # The DTO being created
from shandu.local_kb.kb import LocalKB # For type hinting the mock
from shandu.agents.utils.citation_manager import SourceInfo # For mocking get_document return

# Fixture for LocalSearcher with a mocked LocalKB
@pytest.fixture
def mocked_local_kb():
    """Creates a MagicMock instance of LocalKB."""
    mock_kb = MagicMock(spec=LocalKB)
    return mock_kb

@pytest.fixture
def local_searcher(mocked_local_kb: MagicMock) -> LocalSearcher:
    """Returns a LocalSearcher instance with a mocked LocalKB."""
    return LocalSearcher(local_kb=mocked_local_kb, max_results=3)

# --- Test Data ---
MOCK_KB_SEARCH_RESULTS = [
    {
        "text": "This is the first chunk from document A about apples.",
        "source_file_path": "/path/to/docA.txt",
        "chunk_index_in_doc": 0,
        "score": 0.85
    },
    {
        "text": "Another chunk from document B discussing bananas.",
        "source_file_path": "/another/path/docB.pdf",
        "chunk_index_in_doc": 1,
        "score": 0.78
    },
    {
        "text": "Final relevant chunk from document C regarding cherries.",
        "source_file_path": "/tmp/docC.docx",
        "chunk_index_in_doc": 0,
        "score": 0.92
    }
]

MOCK_SOURCE_INFO_A = SourceInfo(file_path="/path/to/docA.txt", title="Document A Title", is_local=True)
MOCK_SOURCE_INFO_B = SourceInfo(file_path="/another/path/docB.pdf", title="Document B Title", is_local=True)
MOCK_SOURCE_INFO_C = SourceInfo(file_path="/tmp/docC.docx", title="Document C Title", is_local=True)

def mock_get_document_side_effect(file_path: str):
    if file_path == "/path/to/docA.txt":
        return MOCK_SOURCE_INFO_A
    elif file_path == "/another/path/docB.pdf":
        return MOCK_SOURCE_INFO_B
    elif file_path == "/tmp/docC.docx":
        return MOCK_SOURCE_INFO_C
    return None

# --- Tests for LocalSearcher ---

def test_local_searcher_init(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test LocalSearcher initialization."""
    assert local_searcher.local_kb == mocked_local_kb
    assert local_searcher.max_results == 3

@pytest.mark.asyncio
async def test_local_searcher_search_async_with_results(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test async search when LocalKB returns results."""
    mocked_local_kb.search_local_kb.return_value = MOCK_KB_SEARCH_RESULTS
    mocked_local_kb.get_document.side_effect = mock_get_document_side_effect

    query = "test query"
    results = await local_searcher.search(query)

    mocked_local_kb.search_local_kb.assert_called_once_with(query, k=local_searcher.max_results)
    assert len(results) == len(MOCK_KB_SEARCH_RESULTS)

    for i, sr_dto in enumerate(results):
        kb_res = MOCK_KB_SEARCH_RESULTS[i]
        mock_doc_info = mock_get_document_side_effect(kb_res["source_file_path"])
        
        assert isinstance(sr_dto, SearchResult)
        assert sr_dto.url == f"file://{os.path.abspath(kb_res['source_file_path'])}"
        assert sr_dto.title == (mock_doc_info.title if mock_doc_info else os.path.basename(kb_res['source_file_path']))
        assert sr_dto.snippet == kb_res["text"]
        assert sr_dto.source == "Local Knowledge Base"

def test_local_searcher_search_sync_with_results(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test sync search when LocalKB returns results."""
    mocked_local_kb.search_local_kb.return_value = MOCK_KB_SEARCH_RESULTS
    mocked_local_kb.get_document.side_effect = mock_get_document_side_effect
    
    query = "another test query"
    results = local_searcher.search_sync(query)

    mocked_local_kb.search_local_kb.assert_called_once_with(query, k=local_searcher.max_results)
    assert len(results) == len(MOCK_KB_SEARCH_RESULTS)

    for i, sr_dto in enumerate(results):
        kb_res = MOCK_KB_SEARCH_RESULTS[i]
        mock_doc_info = mock_get_document_side_effect(kb_res["source_file_path"])

        assert isinstance(sr_dto, SearchResult)
        assert sr_dto.url == f"file://{os.path.abspath(kb_res['source_file_path'])}"
        assert sr_dto.title == (mock_doc_info.title if mock_doc_info else os.path.basename(kb_res['source_file_path']))
        assert sr_dto.snippet == kb_res["text"]
        assert sr_dto.source == "Local Knowledge Base"

@pytest.mark.asyncio
async def test_local_searcher_search_async_no_results(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test async search when LocalKB returns no results."""
    mocked_local_kb.search_local_kb.return_value = []

    query = "empty query"
    results = await local_searcher.search(query)

    mocked_local_kb.search_local_kb.assert_called_once_with(query, k=local_searcher.max_results)
    assert len(results) == 0

def test_local_searcher_search_sync_no_results(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test sync search when LocalKB returns no results."""
    mocked_local_kb.search_local_kb.return_value = []

    query = "empty sync query"
    results = local_searcher.search_sync(query)

    mocked_local_kb.search_local_kb.assert_called_once_with(query, k=local_searcher.max_results)
    assert len(results) == 0

@pytest.mark.asyncio
async def test_local_searcher_search_kb_exception_async(local_searcher: LocalSearcher, mocked_local_kb: MagicMock, caplog):
    """Test async search when LocalKB.search_local_kb raises an exception."""
    mocked_local_kb.search_local_kb.side_effect = Exception("KB search failed!")

    query = "query causing error"
    results = await local_searcher.search(query)

    assert len(results) == 0
    assert "Error during local search" in caplog.text
    assert "KB search failed!" in caplog.text

def test_local_searcher_search_kb_exception_sync(local_searcher: LocalSearcher, mocked_local_kb: MagicMock, caplog):
    """Test sync search when LocalKB.search_local_kb raises an exception."""
    mocked_local_kb.search_local_kb.side_effect = Exception("Sync KB search failed!")

    query = "sync query causing error"
    results = local_searcher.search_sync(query)

    assert len(results) == 0
    assert "Error during synchronous local search" in caplog.text
    assert "Sync KB search failed!" in caplog.text


@pytest.mark.asyncio
async def test_local_searcher_title_fallback(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    """Test title fallback to basename if get_document returns None or no title."""
    single_result = [{
        "text": "Chunk from doc with no title info.",
        "source_file_path": "/path/to/nameless_doc.txt",
        "score": 0.8
    }]
    mocked_local_kb.search_local_kb.return_value = single_result
    
    # Scenario 1: get_document returns None
    mocked_local_kb.get_document.return_value = None
    results1 = await local_searcher.search("query1")
    assert len(results1) == 1
    assert results1[0].title == "nameless_doc.txt"

    # Scenario 2: get_document returns SourceInfo with empty title
    mock_source_no_title = SourceInfo(file_path="/path/to/nameless_doc.txt", title="", is_local=True)
    mocked_local_kb.get_document.return_value = mock_source_no_title
    results2 = await local_searcher.search("query2")
    assert len(results2) == 1
    assert results2[0].title == "nameless_doc.txt"


def test_local_searcher_missing_path_or_text_in_kb_result(local_searcher: LocalSearcher, mocked_local_kb: MagicMock, caplog):
    """Test handling of KB results missing 'source_file_path' or 'text'."""
    bad_results = [
        {"source_file_path": "/path/doc1.txt"}, # Missing text
        {"text": "Some text"},                 # Missing source_file_path
        {"text": None, "source_file_path": "/path/doc2.txt"} # Text is None
    ]
    mocked_local_kb.search_local_kb.return_value = bad_results
    # Mock get_document to prevent errors if it's called for partial valid data
    mocked_local_kb.get_document.return_value = SourceInfo(file_path="dummy", title="Dummy", is_local=True)


    results = local_searcher.search_sync("test")
    assert len(results) == 0 # All results should be skipped
    assert "Skipping result due to missing path or text" in caplog.text
    # Check if it logged for each bad result (or at least that logging occurred)
    assert caplog.text.count("Skipping result due to missing path or text") >= len(bad_results)

# Example of how force_refresh is currently ignored (just for completeness, not very impactful)
def test_force_refresh_ignored(local_searcher: LocalSearcher, mocked_local_kb: MagicMock):
    mocked_local_kb.search_local_kb.return_value = []
    local_searcher.search_sync("test", force_refresh=True)
    # Assert that search_local_kb was called without force_refresh, as it's not part of its signature
    mocked_local_kb.search_local_kb.assert_called_once_with("test", k=local_searcher.max_results)
    # (No direct way to check force_refresh was "ignored" other than it not causing an error
    # and the underlying call not receiving it)
