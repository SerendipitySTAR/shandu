import unittest

class TestCriticalImports(unittest.TestCase):
    def test_all_critical_modules_can_be_imported(self):
        try:
            import shandu
            from shandu import cli
            from shandu.config import config, get_user_agent, get_current_date
            from shandu.agents.langgraph_agent import ResearchGraph
            from shandu.agents.nodes import (
                initialize_node, 
                reflect_node, 
                generate_queries_node,
                search_node, 
                smart_source_selection, 
                format_citations_node,
                generate_initial_report_node, 
                enhance_report_node,
                expand_key_sections_node, 
                report_node, 
                evaluate_quality_node, # Assuming this exists based on previous __init__.py
                global_consistency_check_node
            )
            from shandu.agents.graph.builder import build_graph
            from shandu.search.search import UnifiedSearcher, SearchResult
            from shandu.scraper.scraper import WebScraper, ScrapedContent
            from shandu.agents.processors.content_processor import AgentState
            from shandu.agents.utils.citation_manager import CitationManager, SourceInfo, Learning
            from shandu.agents.utils.citation_registry import CitationRegistry
            from shandu.prompts import SYSTEM_PROMPTS, USER_PROMPTS, REPORT_STYLE_GUIDELINES, get_system_prompt

            # Add other key imports as identified
            self.assertTrue(True, "All critical modules imported successfully.")
        except ImportError as e:
            self.fail(f"Failed to import a critical module: {e}")

if __name__ == '__main__':
    unittest.main()
