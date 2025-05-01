"""Source selection node with robust error handling and retry logic."""
import os
import re
import time
import asyncio
import random
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from ..processors.content_processor import AgentState
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback
from ...prompts import SYSTEM_PROMPTS, USER_PROMPTS

console = Console()

# Maximum retry attempts for source selection
MAX_RETRIES = 3

# Structured output model for source selection
class SourceSelection(BaseModel):
    """Structured output for source selection."""
    selected_sources: list[str] = Field(
        description="List of URLs for the most valuable sources to include in the report",
        min_items=1
    )
    selection_rationale: str = Field(
        description="Explanation of why these sources were selected"
    )

# Exponential backoff function for retries
async def backoff_retry(attempt: int) -> None:
    """Simple exponential backoff."""
    if attempt > 0:
        # Exponential backoff with jitter to avoid thundering herd
        delay = min(30, (2 ** attempt) + (random.random() * 0.5))
        console.print(f"[yellow]Backing off for {delay:.1f} seconds before retry...[/]")
        await asyncio.sleep(delay)

def extract_urls_from_text(text: str, all_source_urls: List[str]) -> List[str]:
    """
    Extract URLs from the model response text.
    
    Args:
        text: The text to extract URLs from
        all_source_urls: List of all possible source URLs
        
    Returns:
        List of extracted URLs
    """
    selected_urls = []
    lines = text.split('\n')
    
    # Iterate through each line looking for URLs
    for line in lines:
        for url in all_source_urls:
            if url in line:
                if url not in selected_urls:
                    selected_urls.append(url)
                    break
                    
    return selected_urls

async def select_sources_with_llm(llm, all_source_urls: List[str], sources_text: str, query: str) -> List[str]:
    """
    Try to select sources using LLM with retry logic.
    
    Args:
        llm: The language model
        all_source_urls: List of all source URLs
        sources_text: Formatted text of all sources
        query: The research query
        
    Returns:
        List of selected URLs
    """
    selected_urls = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Selecting sources..."),
        console=console
    ) as progress:
        task = progress.add_task("Selecting", total=1)
        
        # Try using a standard source selection approach first
        for attempt in range(MAX_RETRIES):
            try:
                await backoff_retry(attempt)
                
                # Use a direct, simplified prompt
                direct_prompt = f"""Select the 15-20 most valuable sources for this research report.

RESEARCH TOPIC: {query}

SOURCES TO EVALUATE:
{sources_text[:15000]}  # Limit text length to avoid token issues

INSTRUCTIONS:
- Select 15-20 of the most valuable sources from the list
- Return ONLY the exact URLs of your selected sources
- List the URLs in order of importance, one URL per line
- Do not include any explanations, just the URLs
"""
                # Try with a smaller timeout and token limit
                retry_llm = llm.with_config({"timeout": 30, "max_tokens": 1024})
                response = await retry_llm.ainvoke(direct_prompt)
                selected_urls = extract_urls_from_text(response.content, all_source_urls)
                
                # If we got some results, we're done
                if selected_urls:
                    progress.update(task, completed=1)
                    break
                    
            except Exception as e:
                console.print(f"[yellow]Source selection attempt {attempt+1} failed: {str(e)}[/]")
                
                # Only log the first error in detail
                if attempt == 0:
                    from ...utils.logger import log_error
                    log_error("Error in source selection", e,
                         context=f"Query: {query}, Function: select_sources_with_llm")
                
                # If this was the last attempt, continue to fallback mechanisms
                if attempt == MAX_RETRIES - 1:
                    console.print("[yellow]All source selection attempts failed, using fallback approach[/]")
                    
        progress.update(task, completed=1)
    
    return selected_urls

async def smart_source_selection(llm, progress_callback, state: AgentState) -> AgentState:
    """Select relevant sources for the report using robust error handling."""
    state["status"] = "Selecting most valuable sources"
    console.print("[bold blue]Selecting most relevant and high-quality sources...[/]")

    # Collect all unique source URLs
    all_source_urls = []
    for analysis in state["content_analysis"]:
        if "sources" in analysis and isinstance(analysis["sources"], list):
            for url in analysis["sources"]:
                if url not in all_source_urls:
                    all_source_urls.append(url)
    
    console.print(f"[green]Found {len(all_source_urls)} total sources to evaluate[/]")
    
    # If we have too many sources, use smart selection to filter them
    if len(all_source_urls) > 25:
        # Prepare formatted source text
        sources_text = ""
        for i, url in enumerate(all_source_urls, 1):
            source_meta = next((s for s in state["sources"] if s.get("url") == url), {})
            
            sources_text += f"Source {i}:\nURL: {url}\n"
            if source_meta.get("title"):
                sources_text += f"Title: {source_meta.get('title')}\n"
            if source_meta.get("snippet"):
                sources_text += f"Summary: {source_meta.get('snippet')}\n"
            if source_meta.get("date"):
                sources_text += f"Date: {source_meta.get('date')}\n"
            sources_text += "\n"
        
        # Try LLM-based selection with retry logic
        selected_urls = await select_sources_with_llm(
            llm, 
            all_source_urls, 
            sources_text, 
            state['query']
        )
        
        # Fallback: If all attempts fail, use a simplified ranking based on source metadata
        if not selected_urls:
            console.print("[yellow]Using fallback source selection based on metadata ranking[/]")
            
            # Prioritize sources with titles and snippets
            ranked_sources = []
            for url in all_source_urls:
                source_meta = next((s for s in state["sources"] if s.get("url") == url), {})
                
                # Simple ranking based on metadata completeness
                score = 0
                if source_meta.get("title"):
                    score += 2
                if source_meta.get("snippet"):
                    score += 1
                if source_meta.get("date"):
                    score += 1
                
                ranked_sources.append((url, score))
            
            # Sort by score in descending order
            ranked_sources.sort(key=lambda x: x[1], reverse=True)
            
            # Take top 15-20 sources
            max_sources = min(20, len(ranked_sources))
            selected_urls = [url for url, _ in ranked_sources[:max_sources]]
        
        # Always ensure we have sources
        if not selected_urls and all_source_urls:
            # Last resort: take the first 15-20 sources
            selected_urls = all_source_urls[:min(20, len(all_source_urls))]
        
        # Store the selected sources
        state["selected_sources"] = selected_urls
        log_chain_of_thought(
            state, 
            f"Selected {len(selected_urls)} most relevant sources from {len(all_source_urls)} total sources"
        )
    else:
        # If we don't have too many sources, use all of them
        state["selected_sources"] = all_source_urls
        log_chain_of_thought(state, f"Using all {len(all_source_urls)} sources for final report")

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state
