import os
import json
import time
import logging
import shutil
from typing import Dict, List, Optional, Any

from shandu.agents.utils.citation_manager import SourceInfo, CitationManager
from shandu.local_kb.document_parser import parse_document
from shandu.local_kb.retriever import LocalKBRetriever
from shandu.local_kb.config import DEFAULT_VECTOR_STORE_FILENAME, DEFAULT_INDEX_METADATA_FILENAME


# Configure logger for the module
logger = logging.getLogger(__name__)
# Basic config, assuming a global config might be set elsewhere in the application
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class LocalKB:
    """
    Manages a local knowledge base of documents, their metadata, and extracted content.
    Integrates with CitationManager for source tracking.
    """

    def __init__(self, kb_dir: str = "local_kb_data", citation_manager: Optional[CitationManager] = None):
        """
        Initializes the LocalKB.

        Args:
            kb_dir: Directory to store metadata and potentially cached content.
            citation_manager: An optional CitationManager instance.
        """
        self.kb_dir = kb_dir
        os.makedirs(self.kb_dir, exist_ok=True)
        logger.info("LocalKB initialized with directory: %s", self.kb_dir)

        self.citation_manager = citation_manager or CitationManager()
        self.documents: Dict[str, SourceInfo] = {}  # Keyed by absolute file path

        # Initialize Retriever
        # Store retriever data within the specific kb_dir
        vector_store_path = os.path.join(self.kb_dir, DEFAULT_VECTOR_STORE_FILENAME)
        index_metadata_path = os.path.join(self.kb_dir, DEFAULT_INDEX_METADATA_FILENAME)
        self.retriever = LocalKBRetriever(
            vector_store_path=vector_store_path,
            index_metadata_path=index_metadata_path
        )

        self._load_metadata() # Loads self.documents

        # Build or load index after documents are loaded
        if self.documents:
            logger.info("KB documents loaded, ensuring retriever index is up-to-date.")
            # reindex=False allows loading existing index; if index is missing or outdated, it will rebuild.
            self.retriever.build_index_from_documents(list(self.documents.values()), reindex=False)
        else:
            logger.info("No initial documents loaded. Retriever index will be built as documents are added.")


    @property
    def _metadata_file(self) -> str:
        """Helper property to get the path to the metadata JSON file."""
        return os.path.join(self.kb_dir, "kb_metadata.json")

    def _source_info_to_dict(self, source_info: SourceInfo) -> Dict[str, Any]:
        """Converts a SourceInfo object to a dictionary for JSON serialization."""
        return {
            "url": source_info.url,
            "title": source_info.title,
            "snippet": source_info.snippet,
            "source_type": source_info.source_type,
            "content_type": source_info.content_type,
            "access_time": source_info.access_time,
            "domain": source_info.domain,
            "reliability_score": source_info.reliability_score,
            "metadata": source_info.metadata,
            "is_local": source_info.is_local,
            "file_path": source_info.file_path,
            "extracted_content": source_info.extracted_content, # Included for now
            "visualizable_data": source_info.visualizable_data,
        }

    def _dict_to_source_info(self, data: Dict[str, Any]) -> SourceInfo:
        """Converts a dictionary (from JSON) back to a SourceInfo object."""
        return SourceInfo(
            url=data.get("url"),
            title=data.get("title", ""),
            snippet=data.get("snippet", ""),
            source_type=data.get("source_type", "local_file"),
            content_type=data.get("content_type", ""),
            access_time=data.get("access_time", time.time()),
            domain=data.get("domain", "localfile"),
            reliability_score=data.get("reliability_score", 0.0),
            metadata=data.get("metadata", {}),
            is_local=data.get("is_local", True), # Default to True for KB context
            file_path=data.get("file_path"),
            extracted_content=data.get("extracted_content", ""),
            visualizable_data=data.get("visualizable_data", []),
        )

    def _load_metadata(self):
        """Loads document metadata from the metadata file."""
        if not os.path.exists(self._metadata_file):
            logger.info("Metadata file not found. Starting with an empty knowledge base.")
            return

        try:
            with open(self._metadata_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            self.documents.clear() # Clear current documents before loading

            for path_key, source_data in loaded_data.items():
                source_info = self._dict_to_source_info(source_data)
                # Ensure file_path in SourceInfo is consistent with the key if it was derived/changed
                if source_info.file_path != path_key:
                    logger.warning(f"Mismatch in file_path ('{source_info.file_path}') and key ('{path_key}') for loaded metadata. Using key as authoritative.")
                    source_info.file_path = path_key # Assuming path_key is the authoritative one
                
                self.documents[path_key] = source_info
                # Register with citation manager. add_source handles duplicates.
                self.citation_manager.add_source(source_info)
            logger.info("Successfully loaded metadata for %d documents from %s", len(self.documents), self._metadata_file)
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from metadata file: %s. Starting with an empty knowledge base.", self._metadata_file, exc_info=True)
            self.documents.clear() # Ensure it's empty on error
        except Exception as e:
            logger.error("An unexpected error occurred while loading metadata from %s: %s. Starting with an empty knowledge base.", self._metadata_file, e, exc_info=True)
            self.documents.clear() # Ensure it's empty on error


    def _save_metadata(self):
        """Saves the current state of self.documents to the metadata JSON file."""
        data_to_save = {}
        for path, source_info in self.documents.items():
            data_to_save[path] = self._source_info_to_dict(source_info)

        try:
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logger.info("Successfully saved metadata for %d documents to %s", len(self.documents), self._metadata_file)
        except Exception as e:
            logger.error("An error occurred while saving metadata to %s: %s", self._metadata_file, e, exc_info=True)

    def add_document(self, file_path: str, source_type: str = "local_file", 
                     content_type: Optional[str] = None, 
                     metadata: Optional[Dict[str, Any]] = None) -> Optional[SourceInfo]:
        """
        Adds a local document to the knowledge base.

        Args:
            file_path: Path to the local document.
            source_type: Type of the source (e.g., "local_file", "report").
            content_type: MIME type or category of content (e.g., "article", "notes").
            metadata: Additional metadata for the source.

        Returns:
            The created SourceInfo object, or None if an error occurred.
        """
        abs_file_path = os.path.abspath(file_path)

        if not os.path.exists(abs_file_path):
            logger.error("File not found: %s. Cannot add document.", abs_file_path)
            return None

        if abs_file_path in self.documents:
            logger.info("Document %s already exists in the knowledge base. Returning existing metadata.", abs_file_path)
            # Consider an update mechanism here in the future
            return self.documents[abs_file_path]

        logger.info("Attempting to parse document: %s", abs_file_path)
        extracted_text = parse_document(abs_file_path)

        if extracted_text is None: # parse_document returns None on failure
            logger.error("Failed to parse document or no text extracted: %s", abs_file_path)
            return None
        
        if not extracted_text.strip(): # Check if extracted text is empty or just whitespace
            logger.warning("No content extracted from document: %s. It might be empty or unparsable.", abs_file_path)
            # Depending on policy, we might still add it with empty content or return None
            # For now, let's add it, but this could be changed.

        file_name = os.path.basename(abs_file_path)
        if content_type is None:
            _, ext = os.path.splitext(file_name)
            content_type = ext.lower() if ext else "unknown" # Use extension as content type if not provided

        source_info = SourceInfo(
            file_path=abs_file_path,
            is_local=True,
            url=None, # Local files don't have URLs
            title=file_name,
            source_type=source_type,
            content_type=content_type,
            extracted_content=extracted_text,
            access_time=time.time(),
            metadata=metadata or {},
            domain="localfile" # Default domain for local files
        )

        self.documents[abs_file_path] = source_info
        self.citation_manager.add_source(source_info) # Register with CitationManager
        self._save_metadata()
        
        # Update retriever index
        logger.info("Adding document %s to retriever index.", abs_file_path)
        self.retriever.add_document_to_index(source_info)

        logger.info("Successfully added document: %s to the knowledge base and retriever index.", abs_file_path)
        return source_info

    def remove_document(self, file_path: str) -> bool:
        """
        Removes a document's metadata from the knowledge base.

        Args:
            file_path: Absolute path to the document.

        Returns:
            True if successful, False otherwise.
        """
        abs_file_path = os.path.abspath(file_path)
        if abs_file_path not in self.documents:
            logger.warning("Document not found in knowledge base: %s. Cannot remove.", abs_file_path)
            return False

        del self.documents[abs_file_path]
        
        # Also remove from CitationManager's sources if it exists there
        # The key in citation_manager.sources for local files is the file_path
        if abs_file_path in self.citation_manager.sources:
            del self.citation_manager.sources[abs_file_path]
            logger.info("Removed document %s from CitationManager sources.", abs_file_path)
        
        # Also remove from citation_manager.source_to_learnings
        if abs_file_path in self.citation_manager.source_to_learnings:
            # Need to remove learnings associated ONLY with this source if they exist
            learnings_to_check = list(self.citation_manager.source_to_learnings[abs_file_path]) # Iterate over a copy
            for learning_hash in learnings_to_check:
                learning_obj = self.citation_manager.learnings.get(learning_hash)
                if learning_obj:
                    if abs_file_path in learning_obj.sources:
                        learning_obj.sources.remove(abs_file_path)
                    # If this was the only source for the learning, remove the learning itself
                    if not learning_obj.sources:
                        del self.citation_manager.learnings[learning_hash]
                        logger.info(f"Removed learning {learning_hash} as it no longer has sources.")
            del self.citation_manager.source_to_learnings[abs_file_path]
            logger.info("Removed document %s from CitationManager source_to_learnings map.", abs_file_path)

        self._save_metadata() # Save metadata before potentially long retriever operation

        # Update retriever index by rebuilding with the remaining documents
        logger.info("Removing document %s from retriever index.", abs_file_path)
        # The list of documents passed to remove_document_from_index should be the state *after* removal
        self.retriever.remove_document_from_index(abs_file_path, list(self.documents.values()))

        logger.info("Successfully removed document metadata: %s from the knowledge base and updated retriever index.", abs_file_path)
        return True

    def get_document(self, file_path: str) -> Optional[SourceInfo]:
        """
        Retrieves a document's metadata from the knowledge base.

        Args:
            file_path: Absolute path to the document.

        Returns:
            The SourceInfo object if found, else None.
        """
        abs_file_path = os.path.abspath(file_path)
        source_info = self.documents.get(abs_file_path)
        if source_info:
            logger.debug("Document found: %s", abs_file_path)
        else:
            logger.debug("Document not found: %s", abs_file_path)
        return source_info

    def list_documents(self) -> List[SourceInfo]:
        """Returns a list of all SourceInfo objects in the knowledge base."""
        return list(self.documents.values())

    def update_document(self, file_path: str, source_type: str = "local_file", 
                        content_type: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[SourceInfo]:
        """
        Updates a document in the knowledge base.
        Currently, this removes the old entry and adds a new one.

        Args:
            file_path: Path to the local document.
            source_type: Type of the source.
            content_type: MIME type or category of content.
            metadata: Additional metadata.

        Returns:
            The updated SourceInfo object, or None if an error occurred.
        """
        abs_file_path = os.path.abspath(file_path)
        logger.info("Attempting to update document: %s", abs_file_path)
        
        if abs_file_path not in self.documents:
            logger.warning("Document %s not found for update. Adding as new document.", abs_file_path)
            # Fall through to add_document logic
        else:
            # Remove existing document first to ensure clean update
            # This also handles removing from citation manager correctly
            if not self.remove_document(abs_file_path):
                logger.error("Failed to remove existing document %s during update. Aborting update.", abs_file_path)
                return None # Or return the old one if partial success is not desired
        
        # Add the document again with potentially new information or re-parsed content
        # This will re-parse the file content.
        updated_source_info = self.add_document(
            file_path=abs_file_path, # Use original file_path, add_document will make it absolute
            source_type=source_type,
            content_type=content_type,
            metadata=metadata
        )

        if updated_source_info:
            logger.info("Successfully updated document: %s", abs_file_path)
        else:
            logger.error("Failed to update document: %s during re-addition.", abs_file_path)
            # Potentially try to restore the old metadata if re-addition fails?
            # For now, it remains removed if re-addition fails.
            
        return updated_source_info


    def get_all_documents_content(self) -> List[Dict[str, Any]]:
        """
        Retrieves the file path and extracted content for all documents.

        Returns:
            A list of dictionaries, each with "file_path" and "content".
        """
        return [
            {"file_path": source.file_path, "content": source.extracted_content}
            for source in self.documents.values() if source.file_path and source.extracted_content # Ensure content exists
        ]

    def search_local_kb(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a semantic search over the documents in the local knowledge base.

        Args:
            query: The search query string.
            k: The number of top results to return.

        Returns:
            A list of dictionaries, each representing a relevant chunk found.
            Structure of each dict depends on LocalKBRetriever.search output.
        """
        if not self.retriever:
            logger.warning("Retriever not initialized. Cannot perform search.")
            return []
        
        logger.info(f"Searching local KB for query: '{query}' with k={k}")
        return self.retriever.search(query, k)


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Ensure this test is run from a context where shandu.local_kb.config.EMBEDDING_MODEL_PATH is valid
    # or the LocalKBRetriever can otherwise load a model.
    logging.basicConfig(level=logging.DEBUG) # Enable more verbose logging for testing
    logger.setLevel(logging.DEBUG) # Ensure LocalKB's logger is also debug
    # Assuming retriever logger is configured in retriever.py, or configure it here if needed
    # logging.getLogger("shandu.local_kb.retriever").setLevel(logging.DEBUG)

    # Create a dummy CitationManager or use default
    # citation_manager = CitationManager()

    # Initialize LocalKB
    # Using a temporary directory for testing to avoid cluttering
    TEST_KB_DIR = "temp_local_kb_data_test" # Main directory for this test run
    
    # Clean up from previous tests thoroughly
    if os.path.exists(TEST_KB_DIR):
        logger.info(f"Removing previous test directory: {TEST_KB_DIR}")
        shutil.rmtree(TEST_KB_DIR)
    os.makedirs(TEST_KB_DIR, exist_ok=True)


    kb = LocalKB(kb_dir=TEST_KB_DIR) # uses its own citation_manager and retriever

    # Create dummy files in a subdirectory for testing (within TEST_KB_DIR)
    TEST_DOCS_SUBDIR = os.path.join(TEST_KB_DIR, "test_docs_source") # Source files for KB
    os.makedirs(TEST_DOCS_SUBDIR, exist_ok=True)

    dummy_txt_path = os.path.join(TEST_DOCS_SUBDIR, "sample.txt")
    dummy_txt_path_2 = os.path.join(TEST_DOCS_SUBDIR, "another_sample.txt")
    dummy_docx_path = os.path.join(TEST_DOCS_SUBDIR, "sample.docx") # Requires python-docx
    dummy_pdf_path = os.path.join(TEST_DOCS_SUBDIR, "sample.pdf")   # Requires pypdf2
    non_existent_path = os.path.join(TEST_DOCS_SUBDIR, "i_do_not_exist.txt")


    with open(dummy_txt_path, "w", encoding="utf-8") as f:
        f.write("This is the first test document (TXT).\nIt contains some sample text about cats and dogs and their "
                "rivalry. The quick brown fox also makes an appearance.")
    
    with open(dummy_txt_path_2, "w", encoding="utf-8") as f:
        f.write("The second test document discusses artificial intelligence, machine learning, and neural networks. "
                "It also mentions the future of technology.")

    # For DOCX and PDF, you'd need actual files for parse_document to work.
    # We'll add them conditionally if the libraries are available and files are created.

    print(f"\n--- Testing Add Document ({dummy_txt_path}) ---")
    added_txt_info = kb.add_document(dummy_txt_path, source_type="test_txt", metadata={"category": "animals"})
    if added_txt_info:
        print(f"Added TXT: {added_txt_info.title}, Content Length: {len(added_txt_info.extracted_content or '')}")
        assert added_txt_info.file_path == os.path.abspath(dummy_txt_path)
        assert os.path.abspath(dummy_txt_path) in kb.documents
        assert os.path.abspath(dummy_txt_path) in kb.citation_manager.sources
        assert kb.retriever.index is not None and kb.retriever.index.ntotal > 0

    print(f"\n--- Testing Add Document ({dummy_txt_path_2}) ---")
    added_txt_info_2 = kb.add_document(dummy_txt_path_2, source_type="test_txt", metadata={"category": "technology"})
    if added_txt_info_2:
        print(f"Added TXT: {added_txt_info_2.title}, Content Length: {len(added_txt_info_2.extracted_content or '')}")
        assert os.path.abspath(dummy_txt_path_2) in kb.documents
        assert kb.retriever.index.ntotal > (len(added_txt_info.extracted_content or '') // kb.retriever.chunk_size if added_txt_info else 0)


    print(f"\n--- Testing Add Document (Non-existent: {non_existent_path}) ---")
    added_non_existent = kb.add_document(non_existent_path)
    assert added_non_existent is None

    # Conditional DOCX test
    try:
        import docx as docx_lib
        if docx_lib:
            doc_content = "This is a test DOCX file about renewable energy and climate change."
            doc = docx_lib.Document()
            doc.add_paragraph(doc_content)
            doc.save(dummy_docx_path)
            print(f"\n--- Testing Add Document ({dummy_docx_path}) ---")
            added_docx_info = kb.add_document(dummy_docx_path, source_type="test_docx", metadata={"topic": "environment"})
            if added_docx_info:
                print(f"Added DOCX: {added_docx_info.title}, Content Length: {len(added_docx_info.extracted_content or '')}")
                assert os.path.abspath(dummy_docx_path) in kb.documents
    except ImportError:
        print(f"\nSkipping DOCX test as python-docx is not installed.")
    except Exception as e:
        print(f"\nError during DOCX test setup or add: {e}")


    print("\n--- Testing List Documents ---")
    all_docs = kb.list_documents()
    print(f"Found {len(all_docs)} documents in KB:")
    for doc_info in all_docs:
        print(f"- {doc_info.title} (Path: {doc_info.file_path})")
    assert len(all_docs) == len(kb.documents)

    print("\n--- Testing Get Document ---")
    retrieved_txt_info = kb.get_document(dummy_txt_path)
    assert retrieved_txt_info is not None
    assert retrieved_txt_info.title == os.path.basename(dummy_txt_path)
    print(f"Retrieved: {retrieved_txt_info.title}")

    print("\n--- Testing Search Local KB ---")
    if kb.retriever.embedding_model: # Only run search if model is loaded
        search_query_animals = "information about pets"
        search_results_animals = kb.search_local_kb(search_query_animals, k=2)
        print(f"Search results for '{search_query_animals}':")
        for res in search_results_animals:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:60]}...'")
        assert len(search_results_animals) > 0
        if search_results_animals: # Check if top result is relevant
            assert "sample.txt" in search_results_animals[0]["source_file_path"]

        search_query_tech = "future of AI"
        search_results_tech = kb.search_local_kb(search_query_tech, k=2)
        print(f"\nSearch results for '{search_query_tech}':")
        for res in search_results_tech:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:60]}...'")
        assert len(search_results_tech) > 0
        if search_results_tech:
             assert "another_sample.txt" in search_results_tech[0]["source_file_path"]
    else:
        print("Skipping search tests as embedding model is not available.")


    print("\n--- Testing Persistence (Save/Load of KB and Retriever Index) ---")
    kb_path_to_check = os.path.abspath(dummy_txt_path)
    # Re-initialize LocalKB from the same directory. This will load metadata and retriever index.
    kb2 = LocalKB(kb_dir=TEST_KB_DIR) # citation_manager will be new, or pass kb.citation_manager
    assert kb_path_to_check in kb2.documents
    retrieved_after_load = kb2.get_document(kb_path_to_check)
    assert retrieved_after_load is not None
    assert retrieved_after_load.title == os.path.basename(kb_path_to_check)
    if added_txt_info: # Check content if original add was successful
        assert retrieved_after_load.extracted_content == added_txt_info.extracted_content
    print(f"Successfully loaded KB metadata. Document '{retrieved_after_load.title}' is present.")
    assert kb2.retriever.index is not None and kb2.retriever.index.ntotal > 0
    print(f"Retriever index loaded with {kb2.retriever.index.ntotal} vectors.")

    # Test search with kb2 to ensure retriever loaded correctly
    if kb2.retriever.embedding_model:
        search_results_animals_kb2 = kb2.search_local_kb(search_query_animals, k=1)
        assert len(search_results_animals_kb2) > 0
        if search_results_animals_kb2:
            assert "sample.txt" in search_results_animals_kb2[0]["source_file_path"]
        print("Search after reload is functional.")


    print("\n--- Testing Update Document ---")
    updated_text_content = "The first document now talks about updated content on foxes and hounds."
    with open(dummy_txt_path, "w", encoding="utf-8") as f:
        f.write(updated_text_content)
    
    updated_info = kb.update_document(dummy_txt_path, metadata={"version": "2.0", "category": "animals"})
    assert updated_info is not None
    assert updated_info.extracted_content == updated_text_content
    print(f"Updated document: {updated_info.title}. New content verified.")
    
    # Verify search reflects update (content about foxes should be found)
    if kb.retriever.embedding_model:
        search_query_foxes = "foxes and hounds"
        search_results_foxes = kb.search_local_kb(search_query_foxes, k=1)
        print(f"Search results for '{search_query_foxes}' after update:")
        for res in search_results_foxes:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:60]}...'")
        assert len(search_results_foxes) > 0
        if search_results_foxes:
            assert "sample.txt" in search_results_foxes[0]["source_file_path"]
            assert "foxes and hounds" in search_results_foxes[0]["text"]


    print("\n--- Testing Remove Document ---")
    path_to_remove = os.path.abspath(dummy_txt_path_2) # "another_sample.txt"
    num_docs_before_remove = len(kb.list_documents())
    num_vectors_before_remove = kb.retriever.index.ntotal if kb.retriever.index else 0
    
    removal_status = kb.remove_document(dummy_txt_path_2)
    assert removal_status is True
    assert path_to_remove not in kb.documents
    assert len(kb.list_documents()) == num_docs_before_remove - 1
    print(f"Successfully removed document: {dummy_txt_path_2} from KB metadata.")

    # Check if retriever index was updated (rebuilt, so fewer vectors)
    if kb.retriever.index: # Should exist if docs were added
        # Exact number of vectors removed depends on chunking of the removed doc.
        # Check that it's less than before, or that specific content is no longer found easily.
        assert kb.retriever.index.ntotal < num_vectors_before_remove
        print(f"Retriever index updated. New vector count: {kb.retriever.index.ntotal}")

        # Verify that searching for content unique to the removed document yields less relevant results
        search_query_tech_after_remove = "future of AI" # From another_sample.txt
        search_results_tech_after_remove = kb.search_local_kb(search_query_tech_after_remove, k=1)
        print(f"Search results for '{search_query_tech_after_remove}' after removal:")
        if search_results_tech_after_remove:
            for res in search_results_tech_after_remove:
                print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:60]}...'")
            # The top result should ideally not be another_sample.txt anymore
            assert "another_sample.txt" not in search_results_tech_after_remove[0]["source_file_path"]
        else:
            print("Search returned no results, as expected or content not found strongly.")


    # Clean up the temporary test directory
    # This needs to be outside the main try-finally of the script if LocalKB itself creates subdirs like TEST_DOCS_SUBDIR
    # For testing, it's often better to clean up at the start of the test run.
    # However, a final cleanup is also good.
    logger.info(f"Attempting to clean up test directory: {TEST_KB_DIR}")
    try:
        shutil.rmtree(TEST_KB_DIR)
        logger.info(f"Cleaned up test directory: {TEST_KB_DIR}")
    except Exception as e:
        logger.error(f"Error cleaning up test directory {TEST_KB_DIR}: {e}", exc_info=True)

    print("\nLocalKB tests with retriever integration completed.")
