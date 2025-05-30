import unittest
from unittest.mock import patch, MagicMock, ANY
from click.testing import CliRunner
from shandu.cli import research # Assuming 'research' is the Click command function
from shandu.config import config # To preset some minimal config if needed

# Since ResearchGraph is instantiated inside the cli.research function,
# we need to patch it where it's looked up, which is 'shandu.cli.ResearchGraph'
# Also, clarify_query is called, need to mock that too to avoid LLM calls.
# And the LLM itself.

class TestResearchCLI(unittest.TestCase):

    @patch('shandu.cli.ChatOpenAI') # Mock the LLM instantiation
    @patch('shandu.cli.clarify_query') # Mock the clarify_query async function
    @patch('shandu.cli.ResearchGraph') # Mock the ResearchGraph class
    def test_language_parameter_passed_to_research_graph(self, MockResearchGraph, mock_clarify_query, MockChatOpenAI):
        # Mock the return value of clarify_query
        mock_clarify_query.return_value = "testquery" # It's an async function

        # Mock the ResearchGraph instance and its research_sync method
        mock_graph_instance = MagicMock()
        mock_graph_instance.research_sync.return_value = MagicMock() # Simulate a result object
        MockResearchGraph.return_value = mock_graph_instance
        
        # Mock LLM instance
        MockChatOpenAI.return_value = MagicMock()

        # Ensure some default config values are present to avoid prompts if config is missing
        # This might be necessary if your CLI directly interacts with config for defaults not handled by Click
        with patch.object(config, 'get', side_effect=lambda section, key, default=None: default if default is not None else ""):
            # The side_effect for config.get makes it return the default value provided in the call,
            # or "" if no default is specified. This helps avoid issues if the config file is not present
            # or if certain keys are missing during the test run.
            # For example, config.get("research", "default_depth", 2) would return 2.
            # config.get("api", "base_url") would return "".

            runner = CliRunner()
            result = runner.invoke(research, [
                'testquery', 
                '--language', 'zh',
                # Provide minimal other required options or ensure defaults are fine
                '--depth', '1', 
                '--breadth', '2' 
            ])

        self.assertEqual(result.exit_code, 0, f"CLI command failed with output: {result.output}")

        # Assert that research_sync was called
        mock_graph_instance.research_sync.assert_called_once()
        
        # Get the keyword arguments from the call
        # call_args is a tuple: (args, kwargs) or (name, args, kwargs) if called with name
        # We want the kwargs, which is the second element if (args, kwargs) or third if (name, args, kwargs)
        # For a method call like instance.method(*args, **kwargs), call_args is ((pos_arg1, ...), {kw_arg1: val1, ...})
        
        actual_call_args = mock_graph_instance.research_sync.call_args
        self.assertIsNotNone(actual_call_args)
        
        # Extract kwargs from the call_args object
        called_kwargs = actual_call_args.kwargs
        
        self.assertEqual(called_kwargs.get('language'), 'zh')
        # Also check other parameters to ensure they are passed if necessary
        self.assertEqual(called_kwargs.get('depth'), 1)
        self.assertEqual(called_kwargs.get('breadth'), 2)
        self.assertEqual(called_kwargs.get('query'), 'testquery') # from mocked clarify_query

    @patch('shandu.cli.ChatOpenAI')
    @patch('shandu.cli.clarify_query')
    @patch('shandu.cli.ResearchGraph')
    def test_language_parameter_default_en(self, MockResearchGraph, mock_clarify_query, MockChatOpenAI):
        mock_clarify_query.return_value = "testquery_en"
        mock_graph_instance = MagicMock()
        mock_graph_instance.research_sync.return_value = MagicMock()
        MockResearchGraph.return_value = mock_graph_instance
        MockChatOpenAI.return_value = MagicMock()

        with patch.object(config, 'get', side_effect=lambda section, key, default=None: default if default is not None else ""):
            runner = CliRunner()
            result = runner.invoke(research, [
                'testquery_en',
                '--depth', '1',
                '--breadth', '2'
                # No --language option, so default 'en' should be used
            ])
        
        self.assertEqual(result.exit_code, 0, f"CLI command failed with output: {result.output}")
        mock_graph_instance.research_sync.assert_called_once()
        called_kwargs = mock_graph_instance.research_sync.call_args.kwargs
        self.assertEqual(called_kwargs.get('language'), 'en') # Default

if __name__ == '__main__':
    unittest.main()
