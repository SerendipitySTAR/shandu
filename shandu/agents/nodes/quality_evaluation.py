import json
from rich.console import Console
from langchain_core.prompts import ChatPromptTemplate # Added for potential structured prompts
from ..processors.content_processor import AgentState
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback
from ..utils.citation_registry import CitationRegistry # For type hinting and access
from ..utils.citation_manager import CitationManager # To potentially get registry if not directly in state

console = Console()

async def evaluate_quality_node(llm, progress_callback, state: AgentState) -> AgentState:
    console.print("[bold blue]Evaluating report quality...[/]")
    state["status"] = "Evaluating report quality"
    
    final_report_text = state.get("final_report", "")
    report_template = state.get("report_template", "standard")

    if not final_report_text or len(final_report_text.strip()) < 100: # Basic check for minimal content
        console.print("[yellow]No substantial final report found to evaluate.[/yellow]")
        state["quality_score"] = 0.0
        state["quality_report"] = "No substantial report content to evaluate."
        log_chain_of_thought(state, "Skipped quality evaluation: No substantial report content.")
        if progress_callback:
            await _call_progress_callback(progress_callback, state)
        return state

    prompt_text = f"""You are a meticulous and critical reviewer tasked with evaluating a research report.
The report was generated based on a '{report_template}' template. Evaluate its quality across several dimensions.

**Report Content to Evaluate:**
---
{final_report_text[:15000]} 
--- 
**Note:** The report text may be truncated for brevity in this prompt. Evaluate based on the provided portion.

**Evaluation Dimensions:**
1.  **Content Integrity (Score 1-10)**:
    *   Accuracy and factual correctness of the information presented (based on the provided text itself, assume it's internally consistent unless obvious self-contradictions).
    *   Completeness of the information regarding the implied scope.
    *   Depth of analysis and substantiation of claims.
2.  **Logical Consistency (Score 1-10)**:
    *   Coherence and logical flow of arguments.
    *   Absence of internal contradictions.
    *   Smoothness of transitions between sections and ideas.
3.  **Language Style (Score 1-10)**:
    *   Clarity, conciseness, and precision of language.
    *   Correct grammar, spelling, and punctuation.
    *   Appropriateness of tone and style for the specified '{report_template}' template (e.g., formal for 'academic', actionable for 'business').
4.  **Citation Presence (Score 1-10)**:
    *   Presence of inline citations (e.g., [1], [2], [n]) where claims are made or data is presented.
    *   This is a check for the *presence* of citations, not their accuracy or format. A higher score means citations are generally present where expected.

**Output Format:**
Please provide your evaluation as a single, valid JSON object. The JSON object must follow this structure:
{{
    "overall_score": <float, average of the four dimension scores, out of 10>,
    "scores": {{
        "content_integrity": <float, 1-10>,
        "logical_consistency": <float, 1-10>,
        "language_style": <float, 1-10>,
        "citation_presence": <float, 1-10>
    }},
    "feedback": {{
        "content_integrity": "<string, brief summary of strengths/weaknesses for this dimension>",
        "logical_consistency": "<string, brief summary of strengths/weaknesses for this dimension>",
        "language_style": "<string, brief summary of strengths/weaknesses for this dimension>",
        "citation_presence": "<string, brief summary of strengths/weaknesses for this dimension>"
    }},
    "summary_strengths": "<string, overall key strengths of the report>",
    "summary_weaknesses": "<string, overall key weaknesses/areas for improvement>"
}}

Ensure the output is ONLY the JSON object, with no preceding or succeeding text.
"""
    
    try:
        response = await llm.ainvoke(prompt_text)
        llm_output = response.content.strip()
        
        # Attempt to extract JSON from markdown code blocks if necessary
        if llm_output.startswith("```json"):
            llm_output = llm_output[7:]
            if llm_output.endswith("```"):
                llm_output = llm_output[:-3]
        llm_output = llm_output.strip()

        parsed_response = json.loads(llm_output)
        
        # Integrate citation validation details
        citation_registry: Optional[CitationRegistry] = state.get("citation_registry")
        if not citation_registry: # Attempt to get from citation_manager if not directly in state
            citation_manager: Optional[CitationManager] = state.get("citation_manager")
            if citation_manager and hasattr(citation_manager, 'citation_registry'):
                citation_registry = citation_manager.citation_registry
        
        if citation_registry and final_report_text:
            try:
                validation_results = citation_registry.validate_citations(final_report_text)
                parsed_response["citation_validation_details"] = validation_results
                console.print(f"[green]Citation validation performed. All valid in text: {validation_results.get('all_valid_citations_found_in_text')}.[/green]")
            except Exception as val_e:
                console.print(f"[red]Error during citation validation: {val_e}[/red]")
                parsed_response["citation_validation_details"] = f"Citation validation failed: {str(val_e)}"
        else:
            parsed_response["citation_validation_details"] = "Citation validation could not be performed (registry or report text missing)."

        # --- BEGIN: Generate Improvement Suggestions ---
        console.print("[bold blue]Generating improvement suggestions based on quality assessment...[/]")
        try:
            quality_assessment_summary_for_prompt = json.dumps(parsed_response, indent=2)
            
            suggestions_prompt_text = f"""You are an expert editor reviewing a research report and its quality assessment.
Your task is to provide specific, actionable improvement suggestions based on the report content and the initial assessment.

**Original Report (Truncated):**
---
{final_report_text[:10000]}
---

**Initial Quality Assessment & Citation Validation:**
---
{quality_assessment_summary_for_prompt}
---

**Instructions for Suggestions:**
1.  Focus on the weaknesses identified in the `feedback` sections and `summary_weaknesses` of the assessment.
2.  Address any issues highlighted in `citation_validation_details` (e.g., out-of-range, unregistered, or unused citations).
3.  Provide concrete, actionable advice. For example, instead of "Improve clarity," suggest "Rephrase the sentence '...' in section X for better clarity."
4.  If specific scores are low (e.g., below 6), prioritize suggestions for those dimensions.
5.  Output your suggestions as a single, valid JSON object with a single key "improvement_suggestions".
    The value should be a list of dictionaries, where each dictionary has "area" (e.g., "Content Integrity", "Language Style", "Citation Accuracy") and "suggestion" keys.

**Example JSON Output:**
{{
    "improvement_suggestions": [
        {{"area": "Content Integrity", "suggestion": "The claim about X on page Y needs a specific citation or further elaboration."}},
        {{"area": "Citation Accuracy", "suggestion": "Citation [Z] is listed as out_of_range. Please verify its reference number and target."}}
    ]
}}

Ensure the output is ONLY the JSON object.
"""
            suggestions_response = await llm.ainvoke(suggestions_prompt_text)
            suggestions_llm_output = suggestions_response.content.strip()

            if suggestions_llm_output.startswith("```json"):
                suggestions_llm_output = suggestions_llm_output[7:]
                if suggestions_llm_output.endswith("```"):
                    suggestions_llm_output = suggestions_llm_output[:-3]
            suggestions_llm_output = suggestions_llm_output.strip()
            
            suggestions_json = json.loads(suggestions_llm_output)
            parsed_response["improvement_suggestions_structured"] = suggestions_json.get("improvement_suggestions", [])
            console.print(f"[green]Generated {len(parsed_response['improvement_suggestions_structured'])} improvement suggestions.[/green]")

        except json.JSONDecodeError as s_e:
            console.print(f"[red]Error parsing JSON for improvement suggestions: {s_e}[/red]")
            console.print(f"[red]Suggestions LLM Output was: {suggestions_llm_output if 'suggestions_llm_output' in locals() else 'Unavailable'}[/red]")
            parsed_response["improvement_suggestions_structured"] = [{"area": "Error", "suggestion": f"Failed to parse improvement suggestions JSON: {s_e}"}]
        except Exception as s_e:
            console.print(f"[red]Error generating improvement suggestions: {s_e}[/red]")
            parsed_response["improvement_suggestions_structured"] = [{"area": "Error", "suggestion": f"Failed to generate improvement suggestions: {s_e}"}]
        # --- END: Generate Improvement Suggestions ---

        state["quality_score"] = parsed_response.get("overall_score", 0.0)
        state["quality_report"] = parsed_response # Store the augmented structured report
        state["last_node_activity"] = "Completed report quality evaluation and suggestions."
        log_chain_of_thought(state, f"Report quality evaluated. Overall Score: {state['quality_score']:.2f}/10. Suggestions generated.")
        console.print(f"[green]Report quality evaluated. Overall Score: {state['quality_score']:.2f}/10. Suggestions generated.[/green]")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON from quality evaluation LLM: {e}[/red]")
        console.print(f"[red]LLM Output was: {llm_output if 'llm_output' in locals() else 'Unavailable'}[/red]")
        state["quality_score"] = 0.0
        # Ensure quality_report is a dict even in error cases for consistency, if possible
        quality_report_error = {"error": "Failed to parse LLM response for quality evaluation."}
        if 'llm_output' in locals():
             quality_report_error["raw_output"] = llm_output
        # Add citation validation placeholder for error case
        quality_report_error["citation_validation_details"] = "Citation validation not performed due to LLM parsing error."
        state["quality_report"] = quality_report_error
        state["last_node_activity"] = "Failed to parse quality evaluation."
        log_chain_of_thought(state, "Error: Failed to parse quality evaluation JSON response.")
    except Exception as e:
        console.print(f"[red]Error during report quality evaluation LLM call: {e}[/red]")
        state["quality_score"] = 0.0
        state["quality_report"] = {
            "error": f"LLM call failed during quality evaluation: {str(e)}",
            "citation_validation_details": "Citation validation not performed due to LLM call error."
            }
        state["last_node_activity"] = "Quality evaluation LLM call failed."
        log_chain_of_thought(state, f"Error: Quality evaluation LLM call failed: {e}")

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state
