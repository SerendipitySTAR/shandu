import unittest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock, call

from langchain_core.messages import AIMessage
# from langchain_openai import ChatOpenAI # Not strictly needed if spec is BaseLanguageModel
from langchain_core.language_models.base import BaseLanguageModel


from shandu.agents.processors.content_processor import (
    is_relevant_url,
    process_scraped_item,
    UrlRelevanceResult,
    ContentRating
)
from shandu.scraper.scraper import ScrapedContent # Corrected import path


class TestIsRelevantUrl(unittest.TestCase):
    def setUp(self):
        # Using BaseLanguageModel for spec for broader compatibility with LLM mocks
        self.mock_llm_base = MagicMock(spec=BaseLanguageModel) 
        
        # This mock will represent the object returned by llm.with_structured_output()
        self.mock_structured_llm_instance = MagicMock(spec=BaseLanguageModel)
        self.mock_structured_llm_instance.ainvoke = AsyncMock()

        # Make the base LLM's with_structured_output method return the specialized mock instance
        self.mock_llm_base.with_structured_output = MagicMock(return_value=self.mock_structured_llm_instance)
        
        # For the diagnostic call, which uses the base LLM's ainvoke
        self.mock_llm_base.ainvoke = AsyncMock()

        self.url = "http://example.com"
        self.title = "Example Title"
        self.snippet = "This is an example snippet."
        self.query = "example query"

    def _run(self, coro):
        return asyncio.run(coro)

    def test_successful_structured_output(self):
        self.mock_structured_llm_instance.ainvoke.return_value = UrlRelevanceResult(is_relevant=True, reason="Test reason")
        
        result = self._run(is_relevant_url(self.mock_llm_base, self.url, self.title, self.snippet, self.query))
        
        self.assertTrue(result)
        self.mock_llm_base.with_structured_output.assert_called_once_with(UrlRelevanceResult, method="function_calling")
        self.mock_structured_llm_instance.ainvoke.assert_called_once()

    @patch('shandu.agents.processors.content_processor.console.print')
    def test_diagnostic_raw_content_parsing_success(self, mock_console_print):
        # 1. Initial structured call fails
        self.mock_structured_llm_instance.ainvoke.side_effect = ValueError("Initial parsing failed")
        # 2. Diagnostic call (on base LLM) returns valid JSON string
        self.mock_llm_base.ainvoke.return_value = AIMessage(content='{"is_relevant": true, "reason": "Parsed from diagnostic"}')

        result = self._run(is_relevant_url(self.mock_llm_base, self.url, self.title, self.snippet, self.query))
        
        self.assertTrue(result)
        # Check console output
        mock_console_print.assert_any_call("[dim green]Successfully parsed relevance from diagnostic_raw_content for http://example.com. Relevant: True[/dim green]")
        # Ensure structured_llm.ainvoke was called once (the failing one)
        self.mock_structured_llm_instance.ainvoke.assert_called_once()
        # Ensure base_llm.ainvoke was called once (the diagnostic one)
        self.mock_llm_base.ainvoke.assert_called_once()


    @patch('shandu.agents.processors.content_processor.console.print')
    def test_retry_logic_success(self, mock_console_print):
        # 1. Initial structured call fails
        # 2. Diagnostic call returns non-JSON
        # 3. Retry structured call succeeds
        self.mock_structured_llm_instance.ainvoke.side_effect = [
            ValueError("Initial parsing failed"), # For initial call
            UrlRelevanceResult(is_relevant=True, reason="Retry success") # For retry call
        ]
        self.mock_llm_base.ainvoke.return_value = AIMessage(content="This is not JSON") # For diagnostic call

        result = self._run(is_relevant_url(self.mock_llm_base, self.url, self.title, self.snippet, self.query))
        
        self.assertTrue(result)
        self.assertEqual(self.mock_structured_llm_instance.ainvoke.call_count, 2) # Initial + Retry
        self.mock_llm_base.ainvoke.assert_called_once() # Diagnostic
        mock_console_print.assert_any_call(f"[dim blue]Retrying relevance check for {self.url} with explicit JSON prompt...[/dim blue]")


    @patch('shandu.agents.processors.content_processor.console.print')
    def test_final_fallback_success_relevant(self, mock_console_print):
        # 1. Initial structured call fails
        # 2. Diagnostic call returns non-JSON
        # 3. Retry structured call fails
        # 4. Final fallback call (on base LLM) returns "RELEVANT"
        self.mock_structured_llm_instance.ainvoke.side_effect = [
            ValueError("Initial parsing failed"), # Initial
            ValueError("Retry parsing failed")    # Retry
        ]
        self.mock_llm_base.ainvoke.side_effect = [
            AIMessage(content="This is not JSON"),             # Diagnostic
            AIMessage(content="This search result is RELEVANT.") # Fallback
        ]
        
        result = self._run(is_relevant_url(self.mock_llm_base, self.url, self.title, self.snippet, self.query))
        
        self.assertTrue(result)
        self.assertEqual(self.mock_structured_llm_instance.ainvoke.call_count, 2) # Initial + Retry
        self.assertEqual(self.mock_llm_base.ainvoke.call_count, 2) # Diagnostic + Fallback
        mock_console_print.assert_any_call(f"[dim red]Error in structured relevance check (Attempt 2) for {self.url}: ValueError('Retry parsing failed'). Falling back to simpler approach.[/dim red]")


    @patch('shandu.agents.processors.content_processor.console.print')
    def test_final_fallback_success_not_relevant(self, mock_console_print):
        self.mock_structured_llm_instance.ainvoke.side_effect = [
            ValueError("Initial parsing failed"), 
            ValueError("Retry parsing failed")
        ]
        self.mock_llm_base.ainvoke.side_effect = [
            AIMessage(content="This is not JSON"), 
            AIMessage(content="This search result is NOT RELEVANT.")
        ]

        result = self._run(is_relevant_url(self.mock_llm_base, self.url, self.title, self.snippet, self.query))
        
        self.assertFalse(result)
        self.assertEqual(self.mock_structured_llm_instance.ainvoke.call_count, 2)
        self.assertEqual(self.mock_llm_base.ainvoke.call_count, 2)


class TestProcessScrapedItem(unittest.TestCase):
    def setUp(self):
        self.mock_llm_base = MagicMock(spec=BaseLanguageModel)
        self.mock_structured_llm_instance = MagicMock(spec=BaseLanguageModel)
        self.mock_structured_llm_instance.ainvoke = AsyncMock()
        self.mock_llm_base.with_structured_output = MagicMock(return_value=self.mock_structured_llm_instance)
        self.mock_llm_base.ainvoke = AsyncMock()

        self.item = ScrapedContent(
            url="http://example.com/item",
            title="Test Item Title",
            text="Some initial text content for the item.",
            html="<html><body><p>Initial text</p></body></html>",
            content_type="text/html",
            metadata={"source": "test"}
        )
        self.subquery = "test subquery for item"
        self.main_content = "This is the main content that will be processed."

    def _run(self, coro):
        return asyncio.run(coro)

    def test_successful_structured_output(self):
        expected_rating = ContentRating(rating="HIGH", justification="Good source", extracted_content="Relevant text.")
        self.mock_structured_llm_instance.ainvoke.return_value = expected_rating
        
        result_dict = self._run(process_scraped_item(self.mock_llm_base, self.item, self.subquery, self.main_content))
        
        self.assertEqual(result_dict["rating"], expected_rating.rating)
        self.assertEqual(result_dict["justification"], expected_rating.justification)
        self.assertEqual(result_dict["content"], expected_rating.extracted_content)
        self.mock_llm_base.with_structured_output.assert_called_once_with(ContentRating, method="function_calling")
        self.mock_structured_llm_instance.ainvoke.assert_called_once()

    @patch('shandu.agents.processors.content_processor.console.print')
    def test_diagnostic_raw_content_parsing_success(self, mock_console_print):
        self.mock_structured_llm_instance.ainvoke.side_effect = ValueError("Initial parsing failed")
        self.mock_llm_base.ainvoke.return_value = AIMessage(content='{"rating": "MEDIUM", "justification": "From diagnostic", "extracted_content": "Diagnostic content"}')

        result_dict = self._run(process_scraped_item(self.mock_llm_base, self.item, self.subquery, self.main_content))
        
        self.assertEqual(result_dict["rating"], "MEDIUM")
        self.assertEqual(result_dict["justification"], "From diagnostic")
        self.assertEqual(result_dict["content"], "Diagnostic content")
        mock_console_print.assert_any_call(f"[dim green]Successfully parsed ContentRating from diagnostic_raw_content for {self.item.url}.[/dim green]")
        self.mock_structured_llm_instance.ainvoke.assert_called_once()
        self.mock_llm_base.ainvoke.assert_called_once()


    @patch('shandu.agents.processors.content_processor.console.print')
    def test_retry_logic_success(self, mock_console_print):
        expected_retry_rating = ContentRating(rating="LOW", justification="Retry success", extracted_content="Retry content")
        self.mock_structured_llm_instance.ainvoke.side_effect = [
            ValueError("Initial parsing failed"), 
            expected_retry_rating
        ]
        self.mock_llm_base.ainvoke.return_value = AIMessage(content="This is not JSON") # Diagnostic call

        result_dict = self._run(process_scraped_item(self.mock_llm_base, self.item, self.subquery, self.main_content))

        self.assertEqual(result_dict["rating"], expected_retry_rating.rating)
        self.assertEqual(result_dict["justification"], expected_retry_rating.justification)
        self.assertEqual(result_dict["content"], expected_retry_rating.extracted_content)
        self.assertEqual(self.mock_structured_llm_instance.ainvoke.call_count, 2)
        self.mock_llm_base.ainvoke.assert_called_once() # Diagnostic
        mock_console_print.assert_any_call(f"[dim blue]Retrying content processing for {self.item.url} with explicit JSON prompt...[/dim blue]")


    @patch('shandu.agents.processors.content_processor.console.print')
    def test_final_fallback_parsing(self, mock_console_print):
        self.mock_structured_llm_instance.ainvoke.side_effect = [
            ValueError("Initial parsing failed"), 
            ValueError("Retry parsing failed")
        ]
        self.mock_llm_base.ainvoke.side_effect = [
            AIMessage(content="This is not JSON"), # Diagnostic
            AIMessage(content="RELIABILITY: HIGH\nJUSTIFICATION: Fallback reason\nEXTRACTED_CONTENT: Fallback content about topic X.") # Fallback
        ]

        result_dict = self._run(process_scraped_item(self.mock_llm_base, self.item, self.subquery, self.main_content))

        self.assertEqual(result_dict["rating"], "HIGH")
        self.assertEqual(result_dict["justification"], "Fallback reason")
        self.assertEqual(result_dict["content"], "Fallback content about topic X.")
        self.assertEqual(self.mock_structured_llm_instance.ainvoke.call_count, 2)
        self.assertEqual(self.mock_llm_base.ainvoke.call_count, 2)
        mock_console_print.assert_any_call(f"[dim red]Error in structured content processing (Attempt 2) for {self.item.url}: ValueError('Retry parsing failed'). Falling back to simpler approach.[/dim red]")


if __name__ == '__main__':
    unittest.main()
