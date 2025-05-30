import asyncio # Added as good practice for async functions, though not directly used by this one's logic beyond type hints
from rich.console import Console

from shandu.prompts import get_system_prompt # Assuming this will be used eventually
from ..processors.content_processor import AgentState
from ..utils.agent_utils import log_chain_of_thought, is_shutdown_requested, _call_progress_callback
# from langchain_core.language_models.base import BaseLanguageModel # For llm type hint if needed

console = Console()

async def global_consistency_check_node(llm, progress_callback, state: AgentState) -> AgentState:
    """
    Performs a global consistency check on the generated report.
    """
    if is_shutdown_requested():
        state["status"] = "Shutdown requested, skipping global consistency check"
        log_chain_of_thought(state, "Shutdown requested, skipping global consistency check")
        if progress_callback: # Ensure callback is called if skipping
            await _call_progress_callback(progress_callback, state)
        return state

    state["status"] = "Performing global consistency check"
    console.print("[bold blue]Performing global consistency check on the report...[/]")
    log_chain_of_thought(state, "Starting global consistency check.")

    report_to_check = state.get('final_report') \
                      or state.get('expanded_report') \
                      or state.get('enhanced_report') \
                      or state.get('initial_report', '')

    if not report_to_check.strip():
        log_chain_of_thought(state, "No report content found to check for consistency.")
        state['consistency_suggestions'] = "No report content available for consistency check."
        if progress_callback:
            await _call_progress_callback(progress_callback, state)
        return state

    language = state.get('language', 'en')
    report_title = state.get('report_title', "N/A")
    original_query = state.get('query', "N/A")

    # Current implementation uses a hardcoded English prompt.
    # To use get_system_prompt, it would be:
    # consistency_prompt_template = get_system_prompt("global_report_consistency_check_prompt", language)
    # if not consistency_prompt_template:
    #     consistency_prompt_template = """Fallback or English prompt...""" # as below
    
    consistency_prompt_template = """You are a meticulous editor reviewing a research report for global consistency and coherence.
Report Title: {report_title}
Main Research Query: {original_query}

Full Report Content to Review:
---
{full_report_content}
---

Please review the entire report and provide feedback on the following aspects:
1.  **Overall Coherence:** Does the report flow logically from one section to the next? Are there smooth transitions between topics and arguments?
2.  **Argument Consistency:** Are arguments, claims, and data points presented consistently throughout the report? Are there any contradictions or discrepancies?
3.  **Thematic Integrity:** Does the report stay focused on the main research query: "{original_query}"? Is the central theme well-developed and maintained across all sections?
4.  **Tone and Style:** Is the tone and writing style consistent across all sections, aligning with the expected report type? (e.g., formal, objective, analytical).
5.  **Completeness:** Does the report adequately address the main research query? Are there any obvious gaps in information or analysis that leave key aspects of the query unanswered?
6.  **Redundancy:** Are there any parts of the report that are overly repetitive or redundant?

Provide your feedback as a concise list of specific, actionable suggestions for improvement. If no major issues are found, please state that the report appears largely consistent and coherent.
Focus on high-level global issues rather than minor grammatical errors, unless they significantly impact clarity or meaning.
Your suggestions should help improve the overall quality and readability of the report.
"""

    max_report_chars_for_prompt = 15000 
    truncated_report_content = report_to_check
    if len(report_to_check) > max_report_chars_for_prompt:
        truncated_report_content = report_to_check[:max_report_chars_for_prompt] + \
                                   "\n\n[Content truncated for brevity in this review prompt]"
        log_chain_of_thought(state, f"Report content truncated to {max_report_chars_for_prompt} chars for consistency check prompt.")

    formatted_prompt = consistency_prompt_template.format(
        report_title=report_title,
        original_query=original_query,
        full_report_content=truncated_report_content
    )

    try:
        console.print("[dim]Calling LLM for consistency check...[/dim]")
        review_llm = llm.with_config({"temperature": 0.1, "max_tokens": 1500})
        response = await review_llm.ainvoke(formatted_prompt)
        suggestions = response.content.strip()
        
        state['consistency_suggestions'] = suggestions
        log_chain_of_thought(state, f"Consistency check completed. Suggestions: {suggestions[:300]}...")
        console.print(f"[green]Consistency check suggestions received:[/]\n[dim]{suggestions[:500]}...[/dim]")

    except Exception as e:
        error_message = f"Error during global consistency check: {str(e)}"
        console.print(f"[red]{error_message}[/red]")
        log_chain_of_thought(state, error_message)
        state['consistency_suggestions'] = f"Failed to perform consistency check. Error: {str(e)}"

    state["status"] = "Global consistency check complete"
    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state
