"""
Citation registry to track and manage citations throughout the report generation process.
"""
from typing import Dict, Any, List, Optional, Set, Union

class CitationRegistry:
    """
    Registry that tracks all citations used in a report, ensuring that in-text citations
    match the sources in the references section.
    """
    def __init__(self):
        self.citations = {}  # Maps citation_id to source metadata
        self.id_to_url = {}  # Maps citation_id to source URL for quick lookups
        self.url_to_id = {}  # Maps source URL to citation_id for deduplication
        self.next_id = 1     # Next available citation ID
        self.citation_contexts = {}  # Stores context for each citation use
    
    def register_citation(self, source_url: str, context: str = "") -> int:
        """
        Register a citation and return its ID.
        
        Args:
            source_url: The URL of the source being cited
            context: Optional context about how the citation is being used
            
        Returns:
            int: The citation ID to use in the report
        """

        if source_url in self.url_to_id:
            citation_id = self.url_to_id[source_url]

            if context and context not in self.citation_contexts.get(citation_id, []):
                if citation_id not in self.citation_contexts:
                    self.citation_contexts[citation_id] = []
                self.citation_contexts[citation_id].append(context)
            return citation_id
        
        # Register new citation
        citation_id = self.next_id
        self.citations[citation_id] = {
            "url": source_url,
            "id": citation_id
        }
        self.id_to_url[citation_id] = source_url
        self.url_to_id[source_url] = citation_id
        
        # Store context if provided
        if context:
            self.citation_contexts[citation_id] = [context]
            
        self.next_id += 1
        return citation_id
    
    def get_citation_url(self, citation_id: int) -> Optional[str]:
        """Get the URL associated with a citation ID."""
        return self.id_to_url.get(citation_id)
    
    def get_citation_info(self, citation_id: int) -> Optional[Dict[str, Any]]:
        """Get the full citation info for a citation ID."""
        return self.citations.get(citation_id)
    
    def get_all_citations(self) -> Dict[int, Dict[str, Any]]:
        """Return all registered citations."""
        return self.citations
    
    def get_all_citation_urls(self) -> List[str]:
        """Return all unique cited URLs in order of first citation."""
        return [self.id_to_url[cid] for cid in sorted(self.id_to_url.keys())]
    
    def get_citation_contexts(self, citation_id: int) -> List[str]:
        """Get the contexts in which a citation was used."""
        return self.citation_contexts.get(citation_id, [])
    
    def bulk_register_sources(self, source_urls: List[str]) -> None:
        """Pre-register a list of sources without assigning contexts."""
        for url in source_urls:
            if url not in self.url_to_id:
                self.register_citation(url)
    
    def update_citation_metadata(self, citation_id: int, metadata: Dict[str, Any]) -> None:
        """Update metadata for a citation (e.g., add title, date, etc.)."""
        if citation_id in self.citations:
            self.citations[citation_id].update(metadata)
    
    def validate_citations(self, text: str) -> Dict[str, Any]:
        """
        Validate all citations in a text against the registry.
        
        Args:
            text: The text content to validate citations in
            
        Returns:
            Dict containing detailed validation results.
        """
        import re

        citation_pattern = re.compile(r'\[(\d+)\]')
        # All numeric IDs found in text via r'\[(\d+)\]'
        used_citation_ids = set(int(cid) for cid in citation_pattern.findall(text) if cid.isdigit())

        # All IDs in self.citations.keys()
        # Assuming self.citations keys are integers or string representations of integers
        registered_citation_ids = set(int(key) for key in self.citations.keys())

        # Max ID in self.citations.keys()
        max_expected_citation_id = max(registered_citation_ids) if registered_citation_ids else 0
        
        # In text & in registry & within range (implicitly, as they are in registered_citation_ids)
        correctly_used_ids = used_citation_ids.intersection(registered_citation_ids)
        
        # In text, numeric, but > max_expected_citation_id
        out_of_range_ids_in_text = {cid for cid in used_citation_ids if cid > max_expected_citation_id}
        
        # In text, numeric, within range (<= max_expected_citation_id), but not in registered_citation_ids
        unregistered_ids_in_text = {
            cid for cid in used_citation_ids 
            if cid <= max_expected_citation_id and cid not in registered_citation_ids
        }
        
        # In registry but not found in text
        unused_registered_ids = registered_citation_ids - used_citation_ids
        
        # True if no out_of_range or unregistered citations
        all_valid_citations_found_in_text = not out_of_range_ids_in_text and not unregistered_ids_in_text

        return {
            "all_valid_citations_found_in_text": all_valid_citations_found_in_text,
            "used_citation_ids": used_citation_ids,
            "registered_citation_ids": registered_citation_ids,
            "max_expected_citation_id": max_expected_citation_id,
            "correctly_used_ids": correctly_used_ids,
            "out_of_range_ids_in_text": out_of_range_ids_in_text,
            "unregistered_ids_in_text": unregistered_ids_in_text,
            "unused_registered_ids": unused_registered_ids
        }
