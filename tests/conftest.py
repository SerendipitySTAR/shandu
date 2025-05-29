import pytest
import os
import shutil
import tempfile
from pathlib import Path

from shandu.agents.utils.citation_manager import CitationManager
from shandu.local_kb.kb import LocalKB
from shandu.local_kb.retriever import LocalKBRetriever
from shandu.local_kb.document_parser import parse_document # For direct testing if needed
from shandu.config import config # Global config instance

# --- Paths and Sample Data Fixtures ---

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent # Assuming conftest.py is in tests/

@pytest.fixture(scope="session")
def sample_data_dir(project_root: Path) -> Path:
    """Path to the directory containing sample data files."""
    return project_root / "tests" / "data"

@pytest.fixture(scope="session")
def sample_txt_path(sample_data_dir: Path) -> Path:
    """Path to the sample TXT file."""
    return sample_data_dir / "sample.txt"

@pytest.fixture(scope="session")
def sample_docx_path(sample_data_dir: Path) -> Path:
    """Path to the sample DOCX file."""
    return sample_data_dir / "sample.docx"

@pytest.fixture(scope="session")
def sample_pdf_path(sample_data_dir: Path) -> Path:
    """Path to the sample PDF file."""
    return sample_data_dir / "sample.pdf"

@pytest.fixture(scope="session")
def empty_txt_path(sample_data_dir: Path) -> Path:
    """Path to an empty TXT file."""
    path = sample_data_dir / "empty.txt"
    path.touch() # Create empty file
    return path
    
@pytest.fixture(scope="session")
def unsupported_file_path(sample_data_dir: Path) -> Path:
    """Path to an unsupported file type."""
    path = sample_data_dir / "sample.unsupported"
    with open(path, "w") as f:
        f.write("This is an unsupported file.")
    return path


# --- Temporary Directory Fixture ---

@pytest.fixture
def temp_dir() -> str:
    """Create a temporary directory for test artifacts, automatically cleaned up."""
    td = tempfile.mkdtemp()
    yield td
    shutil.rmtree(td)

# --- Application Component Fixtures ---

@pytest.fixture
def citation_manager() -> CitationManager:
    """Return a new CitationManager instance for each test."""
    return CitationManager()

@pytest.fixture
def temp_kb_dir(temp_dir: str) -> str:
    """Creates a temporary directory specifically for LocalKB data within the main temp_dir."""
    kb_data_path = os.path.join(temp_dir, "kb_data")
    os.makedirs(kb_data_path, exist_ok=True)
    return kb_data_path

@pytest.fixture
def local_kb(temp_kb_dir: str, citation_manager: CitationManager) -> LocalKB:
    """
    Return a LocalKB instance initialized with a temporary directory and a citation manager.
    This LocalKB will use the default embedding model path from config.
    """
    # Temporarily override the global config for kb_dir for this LocalKB instance
    original_kb_dir = config.get("local_kb", "kb_dir")
    original_enabled = config.get("local_kb", "enabled")
    
    config.set("local_kb", "kb_dir", temp_kb_dir)
    config.set("local_kb", "enabled", True) # Ensure it's enabled for tests using it

    kb = LocalKB(kb_dir=temp_kb_dir, citation_manager=citation_manager)
    
    yield kb # Provide the LocalKB instance to the test
    
    # Teardown: Restore original config
    config.set("local_kb", "kb_dir", original_kb_dir)
    config.set("local_kb", "enabled", original_enabled)
    # The temp_kb_dir itself will be cleaned up by the temp_dir fixture

@pytest.fixture
def local_kb_retriever(temp_kb_dir: str) -> LocalKBRetriever:
    """
    Return a LocalKBRetriever instance initialized with paths within a temporary KB directory.
    Uses the default embedding model path from shandu.local_kb.config.
    """
    # Ensure the embedding model path is valid or skip tests requiring it.
    # EMBEDDING_MODEL_PATH is imported in shandu.local_kb.config
    # from shandu.local_kb.config import EMBEDDING_MODEL_PATH
    # if not os.path.exists(EMBEDDING_MODEL_PATH):
    #     pytest.skip(f"Embedding model not found at {EMBEDDING_MODEL_PATH}, skipping retriever tests.")

    retriever_vector_store_path = os.path.join(temp_kb_dir, "test_retriever_store.faiss")
    retriever_index_meta_path = os.path.join(temp_kb_dir, "test_retriever_meta.json")
    
    # Clean up any previous retriever files from prior test runs if not fully cleaned by temp_dir
    if os.path.exists(retriever_vector_store_path): os.remove(retriever_vector_store_path)
    if os.path.exists(retriever_index_meta_path): os.remove(retriever_index_meta_path)

    retriever = LocalKBRetriever(
        # model_path=EMBEDDING_MODEL_PATH, # Uses default from config.py
        vector_store_path=retriever_vector_store_path,
        index_metadata_path=retriever_index_meta_path
    )
    return retriever


# --- CLI Testing Fixture ---

@pytest.fixture
def cli_runner():
    """Return a Click CliRunner instance."""
    from click.testing import CliRunner
    return CliRunner()

# --- Helper for checking embedding model availability ---
def check_embedding_model_availability():
    """
    Checks if the embedding model specified in the config is available.
    If not, skips the current test.
    """
    from shandu.local_kb.config import EMBEDDING_MODEL_PATH
    if not os.path.exists(EMBEDDING_MODEL_PATH):
        pytest.skip(f"Embedding model not found at {EMBEDDING_MODEL_PATH}. This test requires it.")
    # Additionally, try to load it to ensure it's a valid model
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(EMBEDDING_MODEL_PATH)
    except Exception as e:
        pytest.skip(f"Failed to load embedding model from {EMBEDDING_MODEL_PATH}: {e}. This test requires a valid model.")

# You can also add a fixture that uses this check:
@pytest.fixture(autouse=False) # Set autouse=True if many tests need this implicitly
def require_embedding_model(request):
    """
    Fixture that skips a test if the embedding model is not available.
    To use: mark a test with @pytest.mark.require_embedding_model
    """
    # Check if the test is marked to require the embedding model
    if request.node.get_closest_marker("require_embedding_model"):
        check_embedding_model_availability()

# Marker registration (optional, but good practice for custom markers)
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "require_embedding_model: mark test to run only if embedding model is available"
    )
