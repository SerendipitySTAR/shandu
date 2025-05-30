import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
import os
import subprocess
import re
import shutil
import uuid

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
# Assuming ChatOpenAI is part of langchain_openai, if not, adjust path
# from langchain_openai import ChatOpenAI
from langchain_core.language_models.base import BaseLanguageModel

from shandu.agents.processors.report_generator import generate_initial_report
from shandu.agents.nodes.report_generation import report_node, generate_initial_report_node
from shandu.agents.processors.content_processor import AgentState
from shandu.agents.utils.citation_manager import CitationManager, SourceInfo
from shandu.prompts import REPORT_STYLE_GUIDELINES
from shandu.agents.utils.citation_registry import CitationRegistry


class TestReportStyling(unittest.TestCase):
    def _run_async(self, coro):
        return asyncio.run(coro)

    def test_generate_standard_report_style(self):
        mock_llm = MagicMock() # spec=ChatOpenAI removed for simplicity if not strictly needed by mock setup
        mock_llm.ainvoke = AsyncMock()

        expected_content = "# Report Title\n\n## Introduction\nThis is a standard report."
        mock_llm.ainvoke.return_value = AIMessage(content=expected_content)
        
        style_instructions = REPORT_STYLE_GUIDELINES['standard']

        report_content = self._run_async(generate_initial_report(
            llm=mock_llm,
            query="Test Query",
            findings="Some findings.",
            extracted_themes="## Theme1\nDesc1",
            report_title="Test Report Title",
            selected_sources=[],
            formatted_citations="",
            current_date="2023-01-01",
            detail_level="standard",
            include_objective=False,
            citation_registry=None,
            report_style_instructions=style_instructions,
            language='en'
        ))

        self.assertIn("This is a standard report.", report_content) # Check for style-specific content
        self.assertIn("Introduction", report_content) # Standard reports should have an intro

        # Assert that the prompt passed to the LLM includes reinforced style instructions
        last_call_args = mock_llm.ainvoke.call_args
        self.assertIsNotNone(last_call_args, "LLM's ainvoke was not called")
        
        # The prompt can be a list of messages or a string depending on how ainvoke is called by the function
        prompt_arg = last_call_args[0][0]
        user_message_content = ""

        if isinstance(prompt_arg, list): # List of BaseMessage objects
            for msg in prompt_arg:
                if hasattr(msg, 'type') and msg.type == "human": # Langchain messages have .type
                    user_message_content = msg.content
                    break
                elif isinstance(msg, HumanMessage): # Direct check for HumanMessage
                     user_message_content = msg.content
                     break
        elif isinstance(prompt_arg, str): # If the prompt is just a string
            user_message_content = prompt_arg

        self.assertTrue(user_message_content, "User message content not found in LLM call")
        self.assertIn("CRITICAL that you strictly follow", user_message_content)
        self.assertIn(style_instructions, user_message_content)

    def test_generate_business_report_style(self):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()

        expected_content = "# Report Title\n\n## Executive Summary\nThis is a business report."
        mock_llm.ainvoke.return_value = AIMessage(content=expected_content)
        
        style_instructions = REPORT_STYLE_GUIDELINES['business']

        report_content = self._run_async(generate_initial_report(
            llm=mock_llm,
            query="Business Query",
            findings="Business findings.",
            extracted_themes="## Market Analysis\nDetails",
            report_title="Business Test Report",
            selected_sources=[],
            formatted_citations="",
            current_date="2023-01-01",
            detail_level="standard",
            include_objective=False,
            citation_registry=None,
            report_style_instructions=style_instructions,
            language='en'
        ))

        self.assertIn("Executive Summary", report_content)

        last_call_args = mock_llm.ainvoke.call_args
        self.assertIsNotNone(last_call_args)
        prompt_arg = last_call_args[0][0]
        user_message_content = ""
        if isinstance(prompt_arg, list):
            for msg in prompt_arg:
                if hasattr(msg, 'type') and msg.type == "human":
                    user_message_content = msg.content
                    break
                elif isinstance(msg, HumanMessage):
                     user_message_content = msg.content
                     break
        elif isinstance(prompt_arg, str):
            user_message_content = prompt_arg
        
        self.assertTrue(user_message_content)
        self.assertIn("CRITICAL that you strictly follow", user_message_content)
        self.assertIn(style_instructions, user_message_content)

    def test_generate_academic_report_style(self):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()

        expected_content = "# Report Title\n\n## Abstract\nThis is an academic report.\n\n## Introduction\nIntro here."
        mock_llm.ainvoke.return_value = AIMessage(content=expected_content)
        
        style_instructions = REPORT_STYLE_GUIDELINES['academic']

        report_content = self._run_async(generate_initial_report(
            llm=mock_llm,
            query="Academic Query",
            findings="Academic findings.",
            extracted_themes="## Methodology\nDetails",
            report_title="Academic Test Report",
            selected_sources=[],
            formatted_citations="",
            current_date="2023-01-01",
            detail_level="standard",
            include_objective=False,
            citation_registry=None,
            report_style_instructions=style_instructions,
            language='en'
        ))

        self.assertIn("Abstract", report_content)
        self.assertIn("Introduction", report_content) # Academic also has intro

        last_call_args = mock_llm.ainvoke.call_args
        self.assertIsNotNone(last_call_args)
        prompt_arg = last_call_args[0][0]
        user_message_content = ""
        if isinstance(prompt_arg, list):
            for msg in prompt_arg:
                if hasattr(msg, 'type') and msg.type == "human":
                    user_message_content = msg.content
                    break
                elif isinstance(msg, HumanMessage):
                     user_message_content = msg.content
                     break
        elif isinstance(prompt_arg, str):
            user_message_content = prompt_arg

        self.assertTrue(user_message_content)
        self.assertIn("CRITICAL that you strictly follow", user_message_content)
        self.assertIn(style_instructions, user_message_content)

    def test_generate_literature_review_style(self):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()

        expected_content = "# Report Title\n\n## Introduction\nScope and objectives.\n\n## Thematic Sections\nTheme 1 discussed."
        mock_llm.ainvoke.return_value = AIMessage(content=expected_content)
        
        style_instructions = REPORT_STYLE_GUIDELINES['literature_review']

        report_content = self._run_async(generate_initial_report(
            llm=mock_llm,
            query="Literature Review Query",
            findings="Literature findings.",
            extracted_themes="## Key Themes\nDetails",
            report_title="Literature Review Test Report",
            selected_sources=[],
            formatted_citations="",
            current_date="2023-01-01",
            detail_level="standard",
            include_objective=False,
            citation_registry=None,
            report_style_instructions=style_instructions,
            language='en'
        ))

        self.assertIn("Introduction", report_content) 
        self.assertIn("Scope and objectives", report_content) # Specific to lit review intro
        self.assertIn("Thematic Sections", report_content)

        last_call_args = mock_llm.ainvoke.call_args
        self.assertIsNotNone(last_call_args)
        prompt_arg = last_call_args[0][0]
        user_message_content = ""
        if isinstance(prompt_arg, list):
            for msg in prompt_arg:
                if hasattr(msg, 'type') and msg.type == "human":
                    user_message_content = msg.content
                    break
                elif isinstance(msg, HumanMessage):
                     user_message_content = msg.content
                     break
        elif isinstance(prompt_arg, str):
            user_message_content = prompt_arg

        self.assertTrue(user_message_content)
        self.assertIn("CRITICAL that you strictly follow", user_message_content)
        self.assertIn(style_instructions, user_message_content)


class TestChartGeneration(unittest.TestCase):
    def _run_async(self, coro):
        return asyncio.run(coro)

    def setUp(self):
        self.test_chart_dir = "test_charts_output"
        if not os.path.exists(self.test_chart_dir):
            os.makedirs(self.test_chart_dir)
        
        # Mock LLM for general use in node functions if needed
        self.mock_llm = MagicMock(spec=BaseLanguageModel) # Use BaseLanguageModel for broader compatibility
        self.mock_llm.ainvoke = AsyncMock()


    def tearDown(self):
        if os.path.exists(self.test_chart_dir):
            shutil.rmtree(self.test_chart_dir)

    @patch('shandu.agents.nodes.report_generation.llm') # Mock the llm instance used in the node module
    def test_matplotlib_code_generation_prompting(self, mock_node_llm):
        # This test focuses on the LLM call within generate_initial_report_node for chart code
        mock_chart_code_llm = MagicMock(spec=BaseLanguageModel)
        mock_chart_code_llm.ainvoke = AsyncMock(return_value=AIMessage(content="```python\nimport matplotlib.pyplot as plt\nplt.plot([1,2],[3,4])\nplt.savefig('test.png')\nplt.close()\n```"))
        
        # Set the main llm used by generate_initial_report_node to return our specific chart_code_llm for chart gen calls
        # This requires knowing how generate_initial_report_node gets its LLM or if it uses a global one.
        # The provided code shows `visual_data_llm = llm.with_config(...)` and `chart_code_llm = llm.with_config(...)`
        # So, we mock the `llm` that is passed into `generate_initial_report_node`.
        # The `mock_node_llm` from the decorator is this `llm`.
        # We need its `with_config` to return our `mock_chart_code_llm`.
        mock_node_llm.with_config.return_value = mock_chart_code_llm

        citation_manager = CitationManager()
        source_info = SourceInfo(url="http://example.com/data_source")
        source_info.extracted_content = "Some text with data: values are 1, 2, 3."
        # Simulate that visualizable_data was already extracted by a prior LLM call (mocked here)
        source_info.visualizable_data = [{
            "data_points": [[1, 10], [2, 20], [3, 30]],
            "data_type": "time-series",
            "potential_chart_types": ["line_chart", "bar_chart"],
            "title_suggestion": "Test Chart Title",
            "x_axis_label_suggestion": "Time",
            "y_axis_label_suggestion": "Value",
            "description": "A test dataset."
        }]
        citation_manager.add_source(source_info)

        state = AgentState(
            query="Test query for charts",
            findings="Some findings.",
            sources=[{"url": "http://example.com/data_source", "title": "Data Source"}],
            selected_sources=["http://example.com/data_source"],
            content_analysis=[{"query": "Test query for charts", "analysis": "Analysis text", "sources": ["http://example.com/data_source"]}],
            citation_manager=citation_manager,
            current_date="2023-01-01",
            detail_level="standard",
            report_template="standard",
            language="en",
            start_time=0 
        )
        
        # We are testing a part of generate_initial_report_node.
        # The node is complex, so we focus on the chart generation part.
        # The `generate_initial_report_node` itself calls `prepare_report_data` and then tries to extract visual data.
        # The visual data extraction part also uses an LLM. Let's mock that too.
        
        # Mock the LLM call for visual_data extraction
        mock_visual_data_extraction_llm = MagicMock(spec=BaseLanguageModel)
        mock_visual_data_extraction_llm.ainvoke = AsyncMock(return_value=AIMessage(content=json.dumps(source_info.visualizable_data)))
        
        # The first with_config call in generate_initial_report_node is for visual_data_llm, 
        # the second is for chart_code_llm.
        mock_node_llm.with_config.side_effect = [mock_visual_data_extraction_llm, mock_chart_code_llm]

        # Run the node function (or the relevant part if refactored)
        # generate_initial_report_node is an async generator, so we need to handle that.
        # For simplicity, let's assume we can call it and it modifies state.
        # The function is not a generator, it's `async def ... -> AgentState`
        
        final_state = self._run_async(
            generate_initial_report_node(llm=mock_node_llm, include_objective=False, progress_callback=None, state=state)
        )

        # Assert that the chart_code_llm (mock_chart_code_llm) was called
        mock_chart_code_llm.ainvoke.assert_called_once()
        
        # Inspect call_args for the chart code generation prompt
        prompt_for_chart_code = mock_chart_code_llm.ainvoke.call_args[0][0]
        self.assertIn("Generate a Python script using Matplotlib", prompt_for_chart_code)
        self.assertIn("line_chart", prompt_for_chart_code) # From potential_chart_types[0]
        self.assertIn(str(source_info.visualizable_data[0]['data_points']), prompt_for_chart_code)
        self.assertIn(source_info.visualizable_data[0]['title_suggestion'], prompt_for_chart_code)
        self.assertIn("plt.savefig(", prompt_for_chart_code) # Check if filename instruction is there
        self.assertIn("plt.close()", prompt_for_chart_code)

        # Verify that the generated code is stored in visualizable_data
        updated_source_info = final_state["citation_manager"].sources["http://example.com/data_source"]
        self.assertIsNotNone(updated_source_info.visualizable_data[0].get('matplotlib_code'))
        self.assertIn("plt.plot([1,2],[3,4])", updated_source_info.visualizable_data[0]['matplotlib_code'])
        self.assertTrue(updated_source_info.visualizable_data[0]['chart_filename'].startswith("chart_"))
        self.assertTrue(updated_source_info.visualizable_data[0]['chart_filename'].endswith(".png"))


    @patch('shandu.agents.nodes.report_generation.subprocess.run')
    @patch('shandu.agents.nodes.report_generation.os.path.exists')
    @patch('shandu.agents.nodes.report_generation.os.makedirs') # To prevent actual makedirs during test
    def test_chart_script_execution_success(self, mock_makedirs, mock_os_exists, mock_subprocess_run):
        # Configure mocks
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Mock os.path.exists to return True after subprocess.run (simulating file creation)
        # and then for the temp script removal check
        mock_os_exists.side_effect = [True, True]


        # Prepare AgentState
        chart_filename = "test_chart_success.png"
        matplotlib_code = (
            "import matplotlib.pyplot as plt\n"
            "fig, ax = plt.subplots()\n"
            "ax.plot([1, 2, 3], [1, 4, 9])\n"
            f"plt.savefig('{chart_filename}')\n" # Original filename
            "plt.close(fig)\n"
        )
        
        citation_manager = CitationManager()
        source_info = SourceInfo(url="http://example.com/chart_source")
        source_info.visualizable_data = [{
            'matplotlib_code': matplotlib_code,
            'chart_filename': chart_filename,
            'title_suggestion': 'Successful Chart'
        }]
        citation_manager.add_source(source_info)

        state = AgentState(
            query="Test query",
            findings="# Report Title\n\n## Section1\nContent1", # Initial report content
            sources=[], selected_sources=[], content_analysis=[],
            citation_manager=citation_manager,
            current_date="2023-01-01",
            detail_level="standard",
            report_template="standard",
            language="en",
            start_time=0
        )
        state["initial_report"] = state["findings"] # report_node uses this if others are missing

        # Patch the chart_output_dir within the scope of report_node for this test
        # This is tricky. Instead, we'll rely on the dynamic savefig path modification.
        # The `report_node` creates `chart_output_dir = "charts"`. We need our test_chart_dir.
        # We can patch `os.path.join` to redirect paths to our test dir, or patch `chart_output_dir`
        # where it's defined in report_node. A simpler approach for testing might be to
        # ensure the dynamic `plt.savefig` modification correctly uses an absolute path.
        # The code already does: `image_path = os.path.join(chart_output_dir, original_chart_filename)`
        # and `chart_code = re.sub(r"plt\.savefig\s*\(\s*['\"].*?['\"]\s*\)", f"plt.savefig(r'{safe_image_path_for_script}')", chart_code)`
        # So, we need `chart_output_dir` inside `report_node` to be `self.test_chart_dir`.
        
        with patch('shandu.agents.nodes.report_generation.chart_output_dir', self.test_chart_dir):
            final_state = self._run_async(report_node(self.mock_llm, None, state))

        # Assert subprocess.run was called
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        self.assertEqual(args[0][0], "python") # Python executable
        self.assertTrue(args[0][1].endswith("temp_chart_script.py")) # Temp script path

        # Assert that the report contains the Markdown link
        expected_md_path = f"{self.test_chart_dir}/{chart_filename}".replace("\\", "/")
        self.assertIn(f"![Successful Chart]({expected_md_path})", final_state["findings"])
        
        # Check that the temp script was removed (os.path.exists for script_path should be True then False)
        # The side_effect for mock_os_exists handles this: first True for image, second True for script before removal.
        # If we want to be more specific, we'd need more calls or more specific patching for os.remove.


    def test_chart_script_creates_file_actually(self):
        chart_filename = "actual_test_chart.png"
        # This code will be dynamically modified by report_node to save to the correct path
        matplotlib_code = (
            "import matplotlib.pyplot as plt\n"
            "import numpy as np\n"
            "x = np.linspace(0, 10, 100)\n"
            "y = np.sin(x)\n"
            "fig, ax = plt.subplots()\n"
            "ax.plot(x, y)\n"
            # The following line will be replaced by report_node's logic
            "plt.savefig('PLACEHOLDER_FILENAME.png')\n"
            "plt.close(fig)\n"
        )

        citation_manager = CitationManager()
        source_info = SourceInfo(url="http://example.com/actual_chart")
        source_info.visualizable_data = [{
            'matplotlib_code': matplotlib_code,
            'chart_filename': chart_filename,
            'title_suggestion': 'Actual Chart'
        }]
        citation_manager.add_source(source_info)

        state = AgentState(
            query="Test query for actual chart",
            findings="# Report Title\n\n## Section1\nContent1",
            sources=[], selected_sources=[], content_analysis=[],
            citation_manager=citation_manager,
            current_date="2023-01-01",
            detail_level="standard", report_template="standard", language="en", start_time=0
        )
        state["initial_report"] = state["findings"]

        expected_image_path = os.path.join(self.test_chart_dir, chart_filename)
        
        # Ensure the file does not exist before the test
        if os.path.exists(expected_image_path):
            os.remove(expected_image_path)

        with patch('shandu.agents.nodes.report_generation.chart_output_dir', self.test_chart_dir):
            final_state = self._run_async(report_node(self.mock_llm, None, state))

        # Assert that the chart image file *actually* exists
        self.assertTrue(os.path.exists(expected_image_path), f"Chart file {expected_image_path} was not created.")
        self.assertTrue(os.path.getsize(expected_image_path) > 0, f"Chart file {expected_image_path} is empty.")

        # Assert that the report contains the Markdown link
        md_path_in_report = f"{self.test_chart_dir}/{chart_filename}".replace("\\","/")
        self.assertIn(f"![Actual Chart]({md_path_in_report})", final_state["findings"])
        
        # Check temp script cleanup (implicitly done by report_node)
        # We can't easily check if os.remove was called on the temp script without more mocks,
        # but we can check if the temp script is NOT in test_chart_dir.
        self.assertFalse(os.path.exists(os.path.join(self.test_chart_dir, "temp_chart_script.py")))


    @patch('shandu.agents.nodes.report_generation.subprocess.run')
    @patch('shandu.agents.nodes.report_generation.console.print') # To check error logging
    def test_chart_script_execution_failure_faulty_code(self, mock_console_print, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="", stderr="SyntaxError: invalid syntax")

        chart_filename = "faulty_chart.png"
        faulty_matplotlib_code = "import matplotlib.pyplot as plt\nplt.plot([1,2],[3,4)\nplt.savefig('faulty.png')\nplt.close()" # Syntax error

        citation_manager = CitationManager()
        source_info = SourceInfo(url="http://example.com/faulty_chart")
        source_info.visualizable_data = [{
            'matplotlib_code': faulty_matplotlib_code,
            'chart_filename': chart_filename,
            'title_suggestion': 'Faulty Chart'
        }]
        citation_manager.add_source(source_info)

        state = AgentState(
            query="Test query for faulty chart",
            findings="# Report Title\n\n## Section1\nContent1",
            sources=[], selected_sources=[], content_analysis=[],
            citation_manager=citation_manager,
            current_date="2023-01-01",
            detail_level="standard", report_template="standard", language="en", start_time=0
        )
        state["initial_report"] = state["findings"]
        
        expected_image_path = os.path.join(self.test_chart_dir, chart_filename)

        with patch('shandu.agents.nodes.report_generation.chart_output_dir', self.test_chart_dir):
            final_state = self._run_async(report_node(self.mock_llm, None, state))

        mock_subprocess_run.assert_called_once()
        
        # Check that an error message was logged
        # Example: find a call to console.print that contains "Error executing chart script"
        error_logged = any("Error executing chart script" in str(call_args) for call_args in mock_console_print.call_args_list)
        self.assertTrue(error_logged, "Error message for faulty script was not logged.")

        # Assert that the report does NOT contain a Markdown link to the chart
        self.assertNotIn(f"![Faulty Chart]", final_state["findings"])
        self.assertNotIn(f"({self.test_chart_dir}/{chart_filename})", final_state["findings"])

        # Assert that the image file does NOT exist
        self.assertFalse(os.path.exists(expected_image_path))


    @patch('shandu.agents.nodes.report_generation.subprocess.run')
    @patch('shandu.agents.nodes.report_generation.console.print')
    def test_chart_script_execution_timeout(self, mock_console_print, mock_subprocess_run):
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="python test_script.py", timeout=30)

        chart_filename = "timeout_chart.png"
        matplotlib_code = "import time\nimport matplotlib.pyplot as plt\nplt.plot([1,2])\nplt.savefig('timeout.png')\nplt.close()\ntime.sleep(60)" # Will timeout

        citation_manager = CitationManager()
        source_info = SourceInfo(url="http://example.com/timeout_chart")
        source_info.visualizable_data = [{
            'matplotlib_code': matplotlib_code,
            'chart_filename': chart_filename,
            'title_suggestion': 'Timeout Chart'
        }]
        citation_manager.add_source(source_info)

        state = AgentState(
            query="Test query for timeout chart",
            findings="# Report Title\n\n## Section1\nContent1",
            sources=[], selected_sources=[], content_analysis=[],
            citation_manager=citation_manager,
            current_date="2023-01-01",
            detail_level="standard", report_template="standard", language="en", start_time=0
        )
        state["initial_report"] = state["findings"]

        with patch('shandu.agents.nodes.report_generation.chart_output_dir', self.test_chart_dir):
            final_state = self._run_async(report_node(self.mock_llm, None, state))

        mock_subprocess_run.assert_called_once()
        
        timeout_logged = any("Timeout executing chart script" in str(call_args) for call_args in mock_console_print.call_args_list)
        self.assertTrue(timeout_logged, "Timeout message was not logged.")

        self.assertNotIn(f"![Timeout Chart]", final_state["findings"])
        self.assertNotIn(f"({self.test_chart_dir}/{chart_filename})", final_state["findings"])
        self.assertFalse(os.path.exists(os.path.join(self.test_chart_dir, chart_filename)))


from shandu.agents.nodes.report_generation import _get_length_instruction

class TestReportHelpers(unittest.TestCase):
    @patch('shandu.agents.nodes.report_generation.print') # Mock print to suppress warning logs
    def test_get_length_instruction_custom_wordcount(self, mock_print):
        # Test with 10000 words
        instruction_10000 = _get_length_instruction("custom_10000")
        self.assertIn("CRITICAL: This section MUST be approximately 10000 words.", instruction_10000)
        self.assertIn("concerted effort", instruction_10000)
        self.assertIn("reach this specific 10000 word target", instruction_10000)

        # Test with 500 words
        instruction_500 = _get_length_instruction("custom_500")
        self.assertIn("CRITICAL: This section MUST be approximately 500 words.", instruction_500)
        self.assertIn("concerted effort", instruction_500)
        self.assertIn("reach this specific 500 word target", instruction_500)
        
        # Ensure no warning print was called for valid custom formats
        # This depends on how mock_print is used. If it's just to suppress, this check might not be needed.
        # However, if print is only called for warnings, then it should not have been called.
        # For this test, we'll assume valid inputs don't trigger print().
        # mock_print.assert_not_called() # This might be too strict if print is used for non-warnings.

    @patch('shandu.agents.nodes.report_generation.print') # Mock print to check for warning logs
    def test_get_length_instruction_standard_values(self, mock_print):
        brief_instruction = _get_length_instruction("brief")
        self.assertTrue(brief_instruction) # Check it's not empty
        self.assertIn("concise", brief_instruction)

        detailed_instruction = _get_length_instruction("detailed")
        self.assertTrue(detailed_instruction)
        self.assertIn("expansive", detailed_instruction)

        standard_instruction = _get_length_instruction("standard")
        self.assertTrue(standard_instruction)
        self.assertIn("balanced level of detail", standard_instruction)

        # Test invalid custom formats
        invalid_custom_abc = _get_length_instruction("custom_abc")
        self.assertIn("balanced level of detail", invalid_custom_abc) # Should return default
        mock_print.assert_any_call("Warning: Could not parse word count from detail_level 'custom_abc'. Defaulting to standard detail instructions.")
        
        mock_print.reset_mock() # Reset mock for the next call
        invalid_custom_empty = _get_length_instruction("custom_")
        self.assertIn("balanced level of detail", invalid_custom_empty) # Should return default
        mock_print.assert_any_call("Warning: Could not parse word count from detail_level 'custom_'. Defaulting to standard detail instructions.")

        mock_print.reset_mock()
        unknown_level = _get_length_instruction("unknown_level")
        self.assertIn("balanced level of detail", unknown_level) # Should return default for unknown
        mock_print.assert_any_call("Warning: Unknown detail_level 'unknown_level'. Defaulting to standard detail instructions.")


if __name__ == '__main__':
    unittest.main()
