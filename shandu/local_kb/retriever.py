import os
import json
import logging
import numpy as np
from typing import List, Optional, Dict, Tuple, Any

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logging.getLogger(__name__).warning(
        "sentence_transformers library not found. LocalKBRetriever will not be functional. "
        "Please install it with 'pip install sentence-transformers'"
    )
    SentenceTransformer = None # type: ignore

try:
    import faiss
except ImportError:
    logging.getLogger(__name__).warning(
        "faiss-cpu library not found. LocalKBRetriever will not be functional. "
        "Please install it with 'pip install faiss-cpu'"
    )
    faiss = None # type: ignore

# Assuming SourceInfo might be imported if this was part of a larger kb.py,
# but for a separate retriever.py, it might not be directly used or defined here.
# If needed: from .kb import SourceInfo (or appropriate import path)
# For now, build_index_from_documents will expect objects with 'extracted_content' and 'file_path'.
from shandu.agents.utils.citation_manager import SourceInfo # Adjusted import

from .config import (
    EMBEDDING_MODEL_PATH,
    DEFAULT_VECTOR_STORE_PATH,
    DEFAULT_INDEX_METADATA_PATH,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP
)

# Configure logger for the module
logger_retriever = logging.getLogger(__name__)
if not logger_retriever.handlers: # Ensure logger is configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class LocalKBRetriever:
    """
    Manages vector indexing and retrieval for local documents using SentenceTransformer and FAISS.
    """

    def __init__(self, 
                 model_path: str = EMBEDDING_MODEL_PATH, 
                 vector_store_path: str = DEFAULT_VECTOR_STORE_PATH, 
                 index_metadata_path: str = DEFAULT_INDEX_METADATA_PATH,
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        """
        Initializes the LocalKBRetriever.

        Args:
            model_path: Path to the SentenceTransformer model.
            vector_store_path: Path to save/load the FAISS index.
            index_metadata_path: Path to save/load metadata about indexed chunks.
            chunk_size: Size of text chunks.
            chunk_overlap: Overlap between text chunks.
        """
        self.logger = logger_retriever
        self.vector_store_path = vector_store_path
        self.index_metadata_path = index_metadata_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if SentenceTransformer is None or faiss is None:
            self.logger.error("sentence-transformers or faiss-cpu is not installed. LocalKBRetriever cannot function.")
            self.embedding_model = None
            self.index = None
            self.document_chunks = []
            return

        try:
            self.logger.info(f"Loading embedding model from: {model_path}")
            if not os.path.exists(model_path):
                self.logger.warning(f"Embedding model path does not exist: {model_path}. Retrieval will fail.")
                # Potentially download a default model here if desired, e.g. 'all-MiniLM-L6-v2'
                # For now, we rely on the path being correct as per original design.
                # Example: self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                raise FileNotFoundError(f"Embedding model not found at {model_path}. Please ensure it's available.")
            self.embedding_model = SentenceTransformer(model_path)
            self.logger.info("Embedding model loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load SentenceTransformer model from {model_path}: {e}", exc_info=True)
            self.embedding_model = None # Ensure it's None if loading fails

        self.index: Optional[faiss.Index] = None
        self.document_chunks: List[Dict[str, Any]] = []  # Stores chunk text and metadata

        self._load_index()

    def _chunk_text(self, text: str) -> List[str]:
        """
        Splits a text into smaller, potentially overlapping chunks.
        Simple implementation: splits by words.
        A more advanced version would use tokenizers from sentence-transformers or langchain.
        """
        if not text:
            return []
            
        # Using a basic character-based split for simplicity, not token-based for now
        # This is a placeholder and should ideally be replaced with a more robust tokenizer solution
        # (e.g., from langchain.text_splitter.SentenceTransformersTokenTextSplitter)
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start += self.chunk_size - self.chunk_overlap # Move start pointer for next chunk
            if start >= len(text): # Ensure we don't go past the end if overlap is large
                 break
        return chunks


    def _load_index(self):
        """Loads the FAISS index and document chunk metadata from disk."""
        if self.embedding_model is None: # Cannot function without model
            return

        if os.path.exists(self.vector_store_path) and os.path.exists(self.index_metadata_path):
            try:
                self.index = faiss.read_index(self.vector_store_path)
                with open(self.index_metadata_path, 'r', encoding='utf-8') as f:
                    self.document_chunks = json.load(f)
                self.logger.info(f"Successfully loaded FAISS index from {self.vector_store_path} "
                                 f"and metadata for {len(self.document_chunks)} chunks.")
            except Exception as e:
                self.logger.error(f"Error loading index or metadata: {e}. Starting with an empty index.", exc_info=True)
                self.index = None
                self.document_chunks = []
        else:
            self.logger.info("No existing index found. A new one will be created when documents are added.")
            self.index = None
            self.document_chunks = []

    def _save_index(self):
        """Saves the FAISS index and document chunk metadata to disk."""
        if self.embedding_model is None: # Cannot function without model
            return

        if self.index is not None and self.document_chunks:
            try:
                os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
                os.makedirs(os.path.dirname(self.index_metadata_path), exist_ok=True)
                
                faiss.write_index(self.index, self.vector_store_path)
                with open(self.index_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(self.document_chunks, f, indent=4, ensure_ascii=False)
                self.logger.info(f"Successfully saved FAISS index to {self.vector_store_path} "
                                 f"and metadata for {len(self.document_chunks)} chunks.")
            except Exception as e:
                self.logger.error(f"Error saving index or metadata: {e}", exc_info=True)
        else:
            self.logger.info("Index is None or no document chunks to save. Skipping save.")


    def build_index_from_documents(self, documents: List[SourceInfo], reindex: bool = False):
        """
        Builds or rebuilds the FAISS index from a list of SourceInfo objects.

        Args:
            documents: A list of SourceInfo objects (must have 'extracted_content' and 'file_path').
            reindex: If True, forces a rebuild even if an index exists.
        """
        if self.embedding_model is None:
            self.logger.error("Embedding model not loaded. Cannot build index.")
            return

        if not reindex and self.index is not None and self.document_chunks:
            self.logger.info("Index already exists and reindex is False. Skipping build.")
            return

        self.logger.info(f"Building index from {len(documents)} documents. Reindex: {reindex}")
        self.document_chunks = [] # Reset
        
        processed_chunks_for_embedding = []

        for doc_idx, doc in enumerate(documents):
            if doc.extracted_content and doc.file_path:
                # Use absolute path for consistency, though doc.file_path should already be absolute from LocalKB
                abs_file_path = os.path.abspath(doc.file_path)
                chunks = self._chunk_text(doc.extracted_content)
                for chunk_idx, chunk_text in enumerate(chunks):
                    self.document_chunks.append({
                        "text": chunk_text,
                        "source_file_path": abs_file_path,
                        "original_document_index": doc_idx, # Index in the input 'documents' list
                        "chunk_index_in_doc": chunk_idx # Index of this chunk within its original document
                    })
                    processed_chunks_for_embedding.append(chunk_text)
            else:
                self.logger.warning(f"Document missing extracted_content or file_path: Title '{doc.title}'. Skipping.")

        if not self.document_chunks:
            self.logger.warning("No processable chunks found in documents. Index will be empty.")
            self.index = None
            self._save_index() # Save empty state
            return

        try:
            self.logger.info(f"Encoding {len(processed_chunks_for_embedding)} chunks for indexing...")
            embeddings = self.embedding_model.encode(processed_chunks_for_embedding, show_progress_bar=True)
            
            if embeddings.ndim == 1: # If only one chunk, ensure it's 2D
                embeddings = np.asarray([embeddings])

            if embeddings.shape[0] == 0: # No embeddings generated
                 self.logger.warning("No embeddings were generated. Index will be empty.")
                 self.index = None
                 self._save_index()
                 return

            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)  # Using L2 distance
            self.index.add(embeddings.astype(np.float32)) # FAISS expects float32
            
            self.logger.info(f"Successfully built FAISS index with {self.index.ntotal} vectors.")
            self._save_index()
        except Exception as e:
            self.logger.error(f"Error building FAISS index: {e}", exc_info=True)
            self.index = None
            # self.document_chunks might still be populated, decide if it should be cleared on error
            # For now, keeping it as it reflects the chunks that were attempted.

    def add_document_to_index(self, document: SourceInfo):
        """
        Adds a single document's content to the existing FAISS index.
        (More granular update than full re-index)
        """
        if self.embedding_model is None or self.index is None:
            self.logger.warning(f"Embedding model or FAISS index not initialized. Building index from scratch with document: {document.file_path}")
            # If index doesn't exist, we need all known documents, not just this one.
            # This implies that LocalKB should manage the list of all documents and pass it here.
            # For now, this function assumes the index exists or will be built from this single doc (less ideal).
            # A better approach for an empty index would be to call build_index_from_documents with all docs.
            # Let's assume for now if index is None, we build it with this single doc.
            if self.index is None:
                self.build_index_from_documents([document], reindex=True)
                return

        if not document.extracted_content or not document.file_path:
            self.logger.warning(f"Document {document.title or document.file_path} has no content or path. Cannot add to index.")
            return

        abs_file_path = os.path.abspath(document.file_path)
        new_chunks_text = self._chunk_text(document.extracted_content)
        
        if not new_chunks_text:
            self.logger.info(f"No text chunks generated for document: {abs_file_path}. Nothing to add to index.")
            return

        try:
            new_embeddings = self.embedding_model.encode(new_chunks_text, show_progress_bar=False)
            if new_embeddings.ndim == 1:
                new_embeddings = np.asarray([new_embeddings])
            
            if new_embeddings.shape[0] == 0:
                self.logger.warning(f"No embeddings generated for document: {abs_file_path}. Nothing to add to index.")
                return

            # Add to FAISS index
            self.index.add(new_embeddings.astype(np.float32))

            # Add to metadata
            # Need to know the original document index if using the same structure as build_index_from_documents
            # For simplicity, we'll just store what's available.
            # This part needs careful consideration if original_document_index is critical elsewhere.
            # Let's assume for incremental add, original_document_index is less critical or handled by caller.
            # Max current original_document_index + 1 or just a placeholder?
            # For now, let's use a placeholder or a reference to the file_path.
            
            base_chunk_idx_in_doc = 0 # Assuming these are new chunks for this doc
            for chunk_idx, chunk_text in enumerate(new_chunks_text):
                self.document_chunks.append({
                    "text": chunk_text,
                    "source_file_path": abs_file_path,
                    # "original_document_index": -1, # Placeholder for incrementally added doc
                    "chunk_index_in_doc": base_chunk_idx_in_doc + chunk_idx
                })
            
            self.logger.info(f"Successfully added {len(new_chunks_text)} chunks from document {abs_file_path} to index. New total: {self.index.ntotal}")
            self._save_index()
        except Exception as e:
            self.logger.error(f"Error adding document {abs_file_path} to index: {e}", exc_info=True)


    def remove_document_from_index(self, file_path: str, all_documents_after_removal: List[SourceInfo]):
        """
        Removes a document and its associated chunks from the index.
        Implemented by rebuilding the index from the provided list of remaining documents.

        Args:
            file_path: The path of the document to remove (used for logging).
            all_documents_after_removal: A list of ALL SourceInfo objects that should remain in the KB.
        """
        if self.embedding_model is None:
            self.logger.error("Embedding model not loaded. Cannot modify index.")
            return

        self.logger.info(f"Removing document '{file_path}' by rebuilding the index with remaining documents.")
        # Rebuild the index using the list of documents that excludes the one to be removed.
        # This list should be managed and provided by LocalKB.
        self.build_index_from_documents(all_documents_after_removal, reindex=True)
        # _save_index() is called by build_index_from_documents


    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the FAISS index for the top k most similar document chunks.

        Args:
            query: The search query string.
            k: The number of results to return.

        Returns:
            A list of dictionaries, each representing a relevant chunk and its metadata.
        """
        if self.embedding_model is None:
            self.logger.error("Embedding model not loaded. Cannot perform search.")
            return []
        if self.index is None or self.index.ntotal == 0 or not self.document_chunks:
            self.logger.info("Index is not built or is empty. Cannot perform search.")
            return []

        try:
            query_embedding = self.embedding_model.encode([query], show_progress_bar=False)
            if query_embedding.ndim == 1: # Ensure 2D
                 query_embedding = np.asarray([query_embedding])

            # FAISS search
            distances, indices = self.index.search(query_embedding.astype(np.float32), k)
            
            results = []
            if indices.size == 0 or distances.size == 0: # Should not happen if k > 0 and index not empty
                return []

            for i in range(indices.shape[1]): # Iterate through k results for the single query
                idx = indices[0][i]
                dist = distances[0][i]

                if idx < 0 or idx >= len(self.document_chunks): # Invalid index from FAISS
                    self.logger.warning(f"FAISS returned invalid index {idx}. Skipping.")
                    continue
                
                chunk_info = self.document_chunks[idx]
                
                # Score: FAISS L2 distance is non-negative. Lower is better.
                # Convert to a pseudo-similarity score (0-1, higher is better) if desired,
                # e.g., score = 1 / (1 + dist). For now, returning raw distance.
                results.append({
                    "text": chunk_info["text"],
                    "source_file_path": chunk_info["source_file_path"],
                    "chunk_index_in_doc": chunk_info.get("chunk_index_in_doc", -1), # older versions might not have this
                    "original_document_index": chunk_info.get("original_document_index", -1), # older versions might not have this
                    "score": float(dist) # Raw L2 distance
                })
            
            # Sort by score (distance ascending) if FAISS didn't guarantee it (it usually does)
            # results.sort(key=lambda x: x['score']) 
            
            return results

        except Exception as e:
            self.logger.error(f"Error during search for query '{query}': {e}", exc_info=True)
            return []

if __name__ == '__main__':
    # Example Usage (for testing LocalKBRetriever independently)
    logging.basicConfig(level=logging.DEBUG)
    logger_retriever.setLevel(logging.DEBUG)

    # Ensure the embedding model path is correct for your setup
    # For testing, you might use a default sentence-transformer model name
    # if EMBEDDING_MODEL_PATH is not correctly set for local execution.
    # e.g., test_model_path = 'all-MiniLM-L6-v2' if EMBEDDING_MODEL_PATH is placeholder
    test_model_path = EMBEDDING_MODEL_PATH 
    
    # Create a temporary directory for retriever test data
    TEST_RETRIEVER_DIR = "temp_retriever_data_test"
    if not os.path.exists(TEST_RETRIEVER_DIR):
        os.makedirs(TEST_RETRIEVER_DIR)
    
    test_vector_store_path = os.path.join(TEST_RETRIEVER_DIR, "test_store.faiss")
    test_index_meta_path = os.path.join(TEST_RETRIEVER_DIR, "test_meta.json")

    # Clean up previous test files if they exist
    if os.path.exists(test_vector_store_path): os.remove(test_vector_store_path)
    if os.path.exists(test_index_meta_path): os.remove(test_index_meta_path)

    retriever = LocalKBRetriever(
        model_path=test_model_path,
        vector_store_path=test_vector_store_path,
        index_metadata_path=test_index_meta_path
    )

    if retriever.embedding_model is None:
        print("Failed to initialize retriever due to model loading issues. Aborting test.")
    else:
        # Create dummy SourceInfo objects (mimicking what LocalKB would provide)
        dummy_doc1_path = os.path.join(TEST_RETRIEVER_DIR, "doc1.txt")
        with open(dummy_doc1_path, "w") as f: f.write("The quick brown fox jumps over the lazy dog. This is the first document.")
        
        dummy_doc2_path = os.path.join(TEST_RETRIEVER_DIR, "doc2.txt")
        with open(dummy_doc2_path, "w") as f: f.write("Artificial intelligence is rapidly changing various industries. The future of AI is bright.")

        dummy_source_infos = [
            SourceInfo(file_path=dummy_doc1_path, extracted_content="The quick brown fox jumps over the lazy dog. This is the first document.", title="Doc1"),
            SourceInfo(file_path=dummy_doc2_path, extracted_content="Artificial intelligence is rapidly changing various industries. The future of AI is bright.", title="Doc2"),
            SourceInfo(file_path=os.path.join(TEST_RETRIEVER_DIR, "doc3.txt"), extracted_content="Another document about space exploration and distant galaxies.", title="Doc3") # No file created, just for metadata
        ]
        
        print("\n--- Testing Build Index ---")
        retriever.build_index_from_documents(dummy_source_infos, reindex=True)
        assert retriever.index is not None
        assert len(retriever.document_chunks) > 0
        print(f"Index built with {retriever.index.ntotal} vectors.")

        print("\n--- Testing Search ---")
        query1 = "information about AI"
        results1 = retriever.search(query1, k=2)
        print(f"Search results for '{query1}':")
        for res in results1:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:50]}...'")
        assert len(results1) > 0
        # A simple check, actual content matching depends on model and chunking
        if results1:
             assert "doc2.txt" in results1[0]["source_file_path"] 

        query2 = "lazy animals"
        results2 = retriever.search(query2, k=2)
        print(f"\nSearch results for '{query2}':")
        for res in results2:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:50]}...'")
        assert len(results2) > 0
        if results2:
            assert "doc1.txt" in results2[0]["source_file_path"]


        print("\n--- Testing Add Document to Index ---")
        doc4_path = os.path.join(TEST_RETRIEVER_DIR, "doc4.txt")
        with open(doc4_path, "w") as f: f.write("A new document about renewable energy sources like solar and wind power.")
        new_doc_info = SourceInfo(file_path=doc4_path, extracted_content="A new document about renewable energy sources like solar and wind power.", title="Doc4")
        
        initial_index_size = retriever.index.ntotal if retriever.index else 0
        retriever.add_document_to_index(new_doc_info)
        assert retriever.index is not None
        assert retriever.index.ntotal > initial_index_size
        print(f"Index size after adding doc: {retriever.index.ntotal}")

        query3 = "solar energy"
        results3 = retriever.search(query3, k=2)
        print(f"\nSearch results for '{query3}' after adding doc4:")
        for res in results3:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:50]}...'")
        if results3:
             assert "doc4.txt" in results3[0]["source_file_path"]


        print("\n--- Testing Remove Document from Index (by rebuilding) ---")
        # Create a list of documents that should remain (doc1, doc3, doc4)
        # We are "removing" doc2
        remaining_docs_info = [
            dummy_source_infos[0], # doc1
            dummy_source_infos[2], # doc3 (content was "Another document about space exploration...")
            new_doc_info         # doc4
        ]
        retriever.remove_document_from_index(dummy_doc2_path, remaining_docs_info)
        assert retriever.index is not None
        
        query_after_remove = "future of AI" # This should ideally not find doc2 strongly
        results_after_remove = retriever.search(query_after_remove, k=3)
        print(f"\nSearch results for '{query_after_remove}' after removing doc2:")
        found_doc2 = False
        for res in results_after_remove:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:50]}...'")
            if "doc2.txt" in res['source_file_path']:
                found_doc2 = True # It might still appear if k is large enough and content is similar to others
        # A simple check: the top result should not be doc2 if removal worked as expected for targeted queries
        # This depends heavily on the distinctiveness of content.
        # A better test would be to ensure the number of chunks from doc2 is zero in document_chunks
        # or that the total number of vectors decreased appropriately.
        
        doc2_chunks_in_meta = any(chunk['source_file_path'] == dummy_doc2_path for chunk in retriever.document_chunks)
        assert not doc2_chunks_in_meta, "doc2 chunks should have been removed from metadata after rebuild."
        print("doc2 chunks successfully removed from metadata.")


        print("\n--- Testing Persistence (Save/Load) ---")
        # Save current state (already done by operations)
        # retriever._save_index() # Explicit save if needed
        
        # Create a new retriever instance, loading from the same paths
        retriever2 = LocalKBRetriever(
            model_path=test_model_path,
            vector_store_path=test_vector_store_path,
            index_metadata_path=test_index_meta_path
        )
        assert retriever2.index is not None
        assert len(retriever2.document_chunks) == len(retriever.document_chunks)
        print(f"Loaded index with {retriever2.index.ntotal} vectors and {len(retriever2.document_chunks)} chunk metadata entries.")

        # Test search with the loaded index
        results_loaded = retriever2.search(query1, k=2) # "information about AI"
        # After removing doc2, this query might return different things or fewer results
        print(f"Search results for '{query1}' using loaded index:")
        for res in results_loaded:
            print(f"  - Path: {res['source_file_path']}, Score: {res['score']:.4f}, Text: '{res['text'][:50]}...'")
        # Check if the results are somewhat consistent with the state before saving (minus doc2)
        
    # Clean up
    import shutil
    try:
        shutil.rmtree(TEST_RETRIEVER_DIR)
        print(f"\nCleaned up test directory: {TEST_RETRIEVER_DIR}")
    except Exception as e:
        print(f"Error cleaning up test directory {TEST_RETRIEVER_DIR}: {e}")

    print("\nLocalKBRetriever tests completed.")
