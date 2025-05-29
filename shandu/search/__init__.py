"""
Search module for Shandu deep research system.
"""

from .search import UnifiedSearcher, SearchResult
from .local_search import LocalSearcher

__all__ = ["UnifiedSearcher", "SearchResult", "LocalSearcher"]
