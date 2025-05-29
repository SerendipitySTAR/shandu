import os
import logging
import asyncio
from typing import List, Optional, Dict, Any

from shandu.search.search import SearchResult # Existing web SearchResult
from shandu.local_kb.kb import LocalKB
# from shandu.local_kb.retriever import LocalKBRetriever # Not directly used, accessed via LocalKB
# from shandu.agents.utils.citation_manager import SourceInfo # Not directly used, LocalKB provides info

# Configure logger for the module
logger = logging.getLogger(__name__)
if not logger.handlers: # Ensure logger is configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class LocalSearcher:
    """
    Performs searches against a Local Knowledge Base (LocalKB) and returns results
    in the standard SearchResult format.
    """

    def __init__(self, local_kb: LocalKB, max_results: int = 5):
        """
        Initializes the LocalSearcher.

        Args:
            local_kb: An instance of LocalKB to search against.
            max_results: The default maximum number of search results to return.
        """
        self.local_kb = local_kb
        self.max_results = max_results
        self.logger = logger # Use the module-level logger

    async def search(self, query: str, force_refresh: bool = False) -> List[SearchResult]:
        """
        Asynchronously performs a search in the LocalKB.
        Note: The underlying LocalKB search is currently synchronous. This async method
        is provided for interface consistency.

        Args:
            query: The search query string.
            force_refresh: Currently ignored, maintained for interface consistency.

        Returns:
            A list of SearchResult objects.
        """
        self.logger.info(f"Async search called for query: '{query}'. force_refresh: {force_refresh} (ignored)")
        # LocalKB's search_local_kb is synchronous.
        # To make this truly async if search_local_kb becomes async, use await here.
        # For now, we call the synchronous method.
        try:
            results_from_kb = self.local_kb.search_local_kb(query, k=self.max_results)
            
            search_results: List[SearchResult] = []
            for res in results_from_kb:
                source_file_path = res.get("source_file_path")
                chunk_text = res.get("text")

                if not source_file_path or chunk_text is None : # text can be empty string
                    self.logger.warning(f"Skipping result due to missing path or text: {res}")
                    continue

                doc_info = self.local_kb.get_document(source_file_path)
                title = doc_info.title if doc_info and doc_info.title else os.path.basename(source_file_path)
                
                # Using file:// scheme for local file paths for better standard representation
                url = f"file://{os.path.abspath(source_file_path)}"

                search_results.append(
                    SearchResult(
                        url=url,
                        title=title,
                        snippet=chunk_text, # The retrieved chunk is the snippet
                        source="Local Knowledge Base",
                        # Optional: add score or other metadata if SearchResult supports it
                        # metadata={"score": res.get("score"), "chunk_index": res.get("chunk_index_in_doc")}
                    )
                )
            self.logger.info(f"Found {len(search_results)} results for query '{query}' from LocalKB.")
            return search_results
        except Exception as e:
            self.logger.error(f"Error during local search for query '{query}': {e}", exc_info=True)
            return []

    def search_sync(self, query: str, force_refresh: bool = False) -> List[SearchResult]:
        """
        Synchronously performs a search in the LocalKB.

        Args:
            query: The search query string.
            force_refresh: Currently ignored, maintained for interface consistency.

        Returns:
            A list of SearchResult objects.
        """
        self.logger.info(f"Sync search called for query: '{query}'. force_refresh: {force_refresh} (ignored)")
        try:
            results_from_kb = self.local_kb.search_local_kb(query, k=self.max_results)
            
            search_results: List[SearchResult] = []
            for res in results_from_kb:
                source_file_path = res.get("source_file_path")
                chunk_text = res.get("text")

                if not source_file_path or chunk_text is None:
                    self.logger.warning(f"Skipping result due to missing path or text: {res}")
                    continue
                
                doc_info = self.local_kb.get_document(source_file_path)
                title = doc_info.title if doc_info and doc_info.title else os.path.basename(source_file_path)
                
                url = f"file://{os.path.abspath(source_file_path)}"

                search_results.append(
                    SearchResult(
                        url=url,
                        title=title,
                        snippet=chunk_text,
                        source="Local Knowledge Base"
                        # Optional: add score or other metadata
                        # metadata={"score": res.get("score"), "chunk_index": res.get("chunk_index_in_doc")}
                    )
                )
            self.logger.info(f"Found {len(search_results)} results for query '{query}' from LocalKB (sync).")
            return search_results
        except Exception as e:
            self.logger.error(f"Error during synchronous local search for query '{query}': {e}", exc_info=True)
            return []

if __name__ == '__main__':
    # Example Usage (requires a LocalKB instance and its dependencies)
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    # Setup a dummy LocalKB for testing LocalSearcher
    # This setup is simplified and assumes LocalKB and its components (retriever, parser) work.
    # For a real test, EMBEDDING_MODEL_PATH in shandu/local_kb/config.py must be valid.
    
    TEST_KB_DIR_FOR_SEARCHER = "temp_local_searcher_kb_data"
    
    # Clean up previous test directory
    import shutil
    if os.path.exists(TEST_KB_DIR_FOR_SEARCHER):
        shutil.rmtree(TEST_KB_DIR_FOR_SEARCHER)
    os.makedirs(TEST_KB_DIR_FOR_SEARCHER)

    # Create dummy files for the LocalKB
    TEST_DOCS_SUBDIR_FOR_SEARCHER = os.path.join(TEST_KB_DIR_FOR_SEARCHER, "docs")
    os.makedirs(TEST_DOCS_SUBDIR_FOR_SEARCHER, exist_ok=True)

    doc1_path = os.path.join(TEST_DOCS_SUBDIR_FOR_SEARCHER, "climate_change.txt")
    doc2_path = os.path.join(TEST_DOCS_SUBDIR_FOR_SEARCHER, "python_programming.txt")

    with open(doc1_path, "w", encoding="utf-8") as f:
        f.write("Climate change is a significant global issue. It is caused by the emission of greenhouse gases. "
                "Renewable energy sources like solar and wind power can help mitigate its effects.")

    with open(doc2_path, "w", encoding="utf-8") as f:
        f.write("Python is a versatile programming language. It is known for its readability and large standard library. "
                "Python is widely used in web development, data science, and artificial intelligence.")

    try:
        # Initialize LocalKB - this might take time if embedding model needs download/loading
        # Ensure your EMBEDDING_MODEL_PATH is correctly set in shandu.local_kb.config
        # or that the default model for SentenceTransformer can be downloaded.
        local_kb_instance = LocalKB(kb_dir=TEST_KB_DIR_FOR_SEARCHER)
        
        # Add documents to LocalKB
        added_doc1 = local_kb_instance.add_document(doc1_path, metadata={"topic": "environment"})
        added_doc2 = local_kb_instance.add_document(doc2_path, metadata={"topic": "programming"})

        if not added_doc1 or not added_doc2:
            raise Exception("Failed to add documents to LocalKB for testing LocalSearcher.")

        if local_kb_instance.retriever.embedding_model is None:
             print("LocalKB's retriever could not load an embedding model. Search tests will likely fail or be inaccurate.")
             # Depending on setup, this might be a fatal error for the test.

        # Initialize LocalSearcher
        local_searcher = LocalSearcher(local_kb=local_kb_instance, max_results=3)

        print("\n--- Testing LocalSearcher (Sync) ---")
        sync_query = "renewable energy"
        sync_results = local_searcher.search_sync(sync_query)
        print(f"Sync search results for '{sync_query}':")
        for res_idx, res in enumerate(sync_results):
            print(f"  {res_idx+1}. Title: {res.title}, URL: {res.url}, Source: {res.source}")
            print(f"     Snippet: '{res.snippet[:100]}...'")
        assert len(sync_results) > 0, f"Expected results for '{sync_query}'"
        if sync_results:
            assert "climate_change.txt" in sync_results[0].title, "Top result should be climate change doc"


        print("\n--- Testing LocalSearcher (Async) ---")
        async_query = "data science with Python"
        # In a real async environment, you'd await this.
        # For this test script, we run it using asyncio.run().
        async_results = asyncio.run(local_searcher.search(async_query))
        print(f"Async search results for '{async_query}':")
        for res_idx, res in enumerate(async_results):
            print(f"  {res_idx+1}. Title: {res.title}, URL: {res.url}, Source: {res.source}")
            print(f"     Snippet: '{res.snippet[:100]}...'")
        assert len(async_results) > 0, f"Expected results for '{async_query}'"
        if async_results:
            assert "python_programming.txt" in async_results[0].title, "Top result should be Python doc"
            
        print("\n--- Testing with query that might not have strong matches ---")
        no_match_query = "ancient Roman history"
        no_match_results = local_searcher.search_sync(no_match_query)
        print(f"Sync search results for '{no_match_query}': {len(no_match_results)} results found.")
        # Depending on the embedding model, some results might still appear due to semantic similarity
        # For this test, we'll just log them.
        for res_idx, res in enumerate(no_match_results):
            print(f"  {res_idx+1}. Title: {res.title}, Snippet: '{res.snippet[:60]}...'")
        # No strict assert here as behavior with dissimilar queries varies.

    except Exception as e:
        print(f"An error occurred during LocalSearcher test setup or execution: {e}")
        print("Ensure that the embedding model path is correctly configured in shandu/local_kb/config.py "
              "and that all dependencies are installed.")
    finally:
        # Clean up the temporary test directory
        try:
            shutil.rmtree(TEST_KB_DIR_FOR_SEARCHER)
            print(f"\nCleaned up test directory: {TEST_KB_DIR_FOR_SEARCHER}")
        except Exception as e_clean:
            print(f"Error cleaning up test directory {TEST_KB_DIR_FOR_SEARCHER}: {e_clean}")

    print("\nLocalSearcher tests completed.")
