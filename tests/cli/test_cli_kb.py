import pytest
import os
import shutil
from click.testing import CliRunner
from pathlib import Path

from shandu.cli import cli # Main CLI application
from shandu.config import config # Global config
from shandu.local_kb.kb import LocalKB # To inspect KB state directly in some tests

# Fixtures from conftest.py will be used:
# - cli_runner: For invoking CLI commands
# - temp_dir: For creating isolated environments
# - sample_txt_path, sample_docx_path, sample_pdf_path: For sample files
# - local_kb: (Potentially) for setting up a KB to be manipulated by CLI,
#             or we can let CLI commands create their own based on overridden config.

# Helper to get the persistent KB directory for a test
def get_persistent_kb_dir(temp_test_env_dir: str) -> str:
    """Returns a consistent path for the 'persistent' KB within a test's temp environment."""
    return os.path.join(temp_test_env_dir, "test_persistent_kb_data")

@pytest.fixture
def persistent_kb_test_env(temp_dir: str):
    """
    Sets up a temporary environment where the CLI will operate,
    including a directory for the persistent KB.
    It overrides the global config for 'local_kb.kb_dir' to this temp persistent dir.
    """
    original_kb_dir = config.get("local_kb", "kb_dir")
    original_enabled_status = config.get("local_kb", "enabled")

    persistent_kb_path = get_persistent_kb_dir(temp_dir)
    os.makedirs(persistent_kb_path, exist_ok=True)
    
    config.set("local_kb", "kb_dir", persistent_kb_path)
    config.set("local_kb", "enabled", True) # Ensure KB is enabled for these CLI tests
    
    yield persistent_kb_path # The path to the persistent KB for this test run
    
    # Teardown: Restore original config and clean up the temp persistent KB dir
    config.set("local_kb", "kb_dir", original_kb_dir)
    config.set("local_kb", "enabled", original_enabled_status)
    if os.path.exists(persistent_kb_path):
        shutil.rmtree(persistent_kb_path)


# --- Tests for `shandu kb` commands ---

# For kb add, remove, list, reindex, we need to ensure the embedding model is available
# as these operations interact with the retriever.
@pytest.mark.require_embedding_model # Apply to individual tests or the class
class TestCliKbManagement:

    def test_kb_add_document(self, cli_runner: CliRunner, persistent_kb_test_env: str, sample_txt_path: Path):
        """Test `shandu kb add` command."""
        kb_dir_for_this_test = persistent_kb_test_env
        
        result = cli_runner.invoke(cli, ["kb", "add", str(sample_txt_path)])
        print(f"CLI output (kb add): {result.output}") # For debugging
        assert result.exit_code == 0
        assert f"Document '{sample_txt_path.name}' added successfully" in result.output

        # Verify by loading the KB directly (using the same overridden config path)
        kb_instance = LocalKB(kb_dir=kb_dir_for_this_test)
        abs_added_path = os.path.abspath(str(sample_txt_path))
        assert abs_added_path in kb_instance.documents
        assert kb_instance.documents[abs_added_path].title == sample_txt_path.name

    def test_kb_add_document_with_metadata(self, cli_runner: CliRunner, persistent_kb_test_env: str, sample_docx_path: Path):
        """Test `shandu kb add` with metadata."""
        kb_dir_for_this_test = persistent_kb_test_env
        metadata_json = '{"author": "Test Author", "version": "1.1"}'
        
        result = cli_runner.invoke(cli, [
            "kb", "add", str(sample_docx_path),
            "--source-type", "report",
            "--metadata-json", metadata_json
        ])
        print(f"CLI output (kb add --metadata): {result.output}")
        assert result.exit_code == 0
        assert f"Document '{sample_docx_path.name}' added successfully" in result.output

        kb_instance = LocalKB(kb_dir=kb_dir_for_this_test)
        abs_added_path = os.path.abspath(str(sample_docx_path))
        assert abs_added_path in kb_instance.documents
        doc = kb_instance.documents[abs_added_path]
        assert doc.source_type == "report"
        assert doc.metadata.get("author") == "Test Author"
        assert doc.metadata.get("version") == "1.1"

    def test_kb_list_documents_empty(self, cli_runner: CliRunner, persistent_kb_test_env: str):
        """Test `shandu kb list` when KB is empty."""
        result = cli_runner.invoke(cli, ["kb", "list"])
        print(f"CLI output (kb list empty): {result.output}")
        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_kb_list_documents_with_content(self, cli_runner: CliRunner, persistent_kb_test_env: str, sample_txt_path: Path):
        """Test `shandu kb list` with documents."""
        # Add a document first
        cli_runner.invoke(cli, ["kb", "add", str(sample_txt_path)])
        
        result = cli_runner.invoke(cli, ["kb", "list"])
        print(f"CLI output (kb list with content): {result.output}")
        assert result.exit_code == 0
        assert "Local KB Documents" in result.output # Table title
        assert sample_txt_path.name in result.output
        assert str(os.path.abspath(str(sample_txt_path))) in result.output # Path

    def test_kb_remove_document(self, cli_runner: CliRunner, persistent_kb_test_env: str, sample_txt_path: Path):
        """Test `shandu kb remove` command."""
        kb_dir_for_this_test = persistent_kb_test_env
        abs_added_path = os.path.abspath(str(sample_txt_path))

        # Add a document
        cli_runner.invoke(cli, ["kb", "add", str(sample_txt_path)])
        kb_instance_before_remove = LocalKB(kb_dir=kb_dir_for_this_test)
        assert abs_added_path in kb_instance_before_remove.documents

        # Remove the document
        result = cli_runner.invoke(cli, ["kb", "remove", str(sample_txt_path)])
        print(f"CLI output (kb remove): {result.output}")
        assert result.exit_code == 0
        assert f"Document '{abs_added_path}' removed successfully" in result.output

        kb_instance_after_remove = LocalKB(kb_dir=kb_dir_for_this_test)
        assert abs_added_path not in kb_instance_after_remove.documents
        
        # Test removing non-existent document
        result_non_existent = cli_runner.invoke(cli, ["kb", "remove", "/path/to/non_existent_doc.txt"])
        print(f"CLI output (kb remove non-existent): {result_non_existent.output}")
        assert result_non_existent.exit_code == 0 # Command itself doesn't fail, prints warning
        assert "Document not found" in result_non_existent.output


    def test_kb_reindex_documents(self, cli_runner: CliRunner, persistent_kb_test_env: str, sample_txt_path: Path):
        """Test `shandu kb reindex` command."""
        # Add a document to have something to reindex
        cli_runner.invoke(cli, ["kb", "add", str(sample_txt_path)])

        result = cli_runner.invoke(cli, ["kb", "reindex"])
        print(f"CLI output (kb reindex): {result.output}")
        assert result.exit_code == 0
        assert "Successfully re-indexed all documents" in result.output
        
    def test_kb_reindex_empty_kb(self, cli_runner: CliRunner, persistent_kb_test_env: str):
        """Test `shandu kb reindex` on an empty KB."""
        result = cli_runner.invoke(cli, ["kb", "reindex"])
        print(f"CLI output (kb reindex empty): {result.output}")
        assert result.exit_code == 0
        assert "No documents in the knowledge base to re-index" in result.output


# --- Tests for `shandu research --local-files` ---
# These tests might be slower if they invoke real research processes.
# Focus on the setup and cleanup of the session KB.
# Mocking the actual research graph execution might be needed for faster unit tests.

@pytest.mark.require_embedding_model # Research with local files will try to init retriever
def test_research_with_local_files_session_kb_creation_and_cleanup(
    cli_runner: CliRunner, 
    persistent_kb_test_env: str, # Acts as the parent for session KB
    sample_txt_path: Path, 
    sample_docx_path: Path,
    monkeypatch
):
    """
    Test `shandu research --local-files` for session KB creation and cleanup.
    Mocks the actual research execution to focus on KB aspects.
    """
    
    # Path to the directory where session KBs would be created (parent dir)
    # persistent_kb_test_env is already set as the config's kb_dir
    base_kb_dir_for_sessions = persistent_kb_test_env

    # Mock the ResearchGraph's research_sync method to prevent full research execution
    # We just want to check if the session KB is set up and then cleaned up.
    mock_research_result = MagicMock()
    mock_research_result.to_markdown.return_value = "Mocked research report."
    
    # research_sync is a method of an instance, so we need to patch it where it's constructed or called.
    # It's called on `graph.research_sync`. `graph` is an instance of ResearchGraph.
    # So we patch 'shandu.cli.ResearchGraph.research_sync'
    
    # Keep track of what kb_dir is used by LocalKB when (if) it's initialized by search_node
    # This is tricky because search_node uses the global config.
    # The CLI command temporarily overrides this global config.
    
    # We can check for the creation of the session_kb_{timestamp} directory
    # and its subsequent removal.

    def mock_research_sync_fn(*args, **kwargs):
        # Inside the mocked research, we can try to inspect the config
        # to see if kb_dir was indeed overridden.
        current_kb_dir_in_research = config.get("local_kb", "kb_dir")
        assert "session_kb_" in current_kb_dir_in_research # Check if it's a session dir
        assert current_kb_dir_in_research != get_persistent_kb_dir(base_kb_dir_for_sessions) # Ensure it's not the persistent one
        
        # Simulate research by checking if the session KB (pointed to by current_kb_dir_in_research)
        # contains the added local files.
        session_kb_instance = LocalKB(kb_dir=current_kb_dir_in_research)
        assert os.path.abspath(str(sample_txt_path)) in session_kb_instance.documents
        assert os.path.abspath(str(sample_docx_path)) in session_kb_instance.documents
        
        return mock_research_result

    monkeypatch.setattr("shandu.cli.ResearchGraph.research_sync", mock_research_sync_fn)

    local_files_str = f"{str(sample_txt_path)},{str(sample_docx_path)}"
    
    result = cli_runner.invoke(cli, [
        "research", "test query for local files",
        "--local-files", local_files_str,
        "--depth", "1" # Minimal depth for faster test
    ])
    
    print(f"CLI output (research --local-files): {result.output}")
    assert result.exit_code == 0
    assert "Mocked research report." in result.output # From our mocked research_sync
    assert "Session Local KB created and configured" in result.output
    assert "Cleaned up temporary session Local KB" in result.output
    
    # Verify that the session KB directory (which should be a subdir of base_kb_dir_for_sessions)
    # no longer exists.
    # We need to find the name of the session dir. It includes a timestamp.
    # We can list subdirs in base_kb_dir_for_sessions; there should be none starting with "session_kb_".
    found_session_dir_after_cleanup = False
    for item in os.listdir(base_kb_dir_for_sessions):
        if item.startswith("session_kb_"):
            found_session_dir_after_cleanup = True
            break
    assert not found_session_dir_after_cleanup, "Temporary session KB directory was not cleaned up."
    
    # Also verify that the global config for kb_dir is restored
    assert config.get("local_kb", "kb_dir") == get_persistent_kb_dir(base_kb_dir_for_sessions)


def test_research_with_invalid_local_file(cli_runner: CliRunner, persistent_kb_test_env: str, monkeypatch):
    """Test `research --local-files` with a non-existent file."""
    
    mock_research_result = MagicMock()
    mock_research_result.to_markdown.return_value = "Mocked research report (invalid file test)."
    monkeypatch.setattr("shandu.cli.ResearchGraph.research_sync", lambda *args, **kwargs: mock_research_result)

    non_existent_file = "/path/to/absolutely/non_existent_file.txt"
    result = cli_runner.invoke(cli, [
        "research", "test query invalid local",
        "--local-files", non_existent_file,
        "--depth", "1"
    ])

    print(f"CLI output (research --invalid-local-files): {result.output}")
    assert result.exit_code == 0
    assert f"Warning: Local file '{non_existent_file}' not found" in result.output
    # Ensure it still proceeds and the "Cleaned up" message for session KB might not appear if no valid files were processed
    # or if the session KB dir wasn't created.
    # The key is that it doesn't crash and warns the user.
    # If a session dir was created (e.g., for other valid files), it should be cleaned.
    # If no valid files, session_kb_path might not be set, so no cleanup message for it.
    assert "Mocked research report (invalid file test)." in result.output
    if "Session Local KB created" not in result.output:
        assert "Cleaned up temporary session Local KB" not in result.output
        
    # Check that no session_kb directory was left behind if one was attempted
    found_session_dir_after_cleanup = False
    for item in os.listdir(persistent_kb_test_env): # persistent_kb_test_env is the parent dir
        if item.startswith("session_kb_"):
            found_session_dir_after_cleanup = True
            break
    assert not found_session_dir_after_cleanup, "Temporary session KB directory was not cleaned up after invalid file."
