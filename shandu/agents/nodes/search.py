"""
Search node for research graph.
"""
import asyncio
import time
import random
import logging
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from ..processors.content_processor import AgentState, is_relevant_url, process_scraped_item, analyze_content
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback, is_shutdown_requested
from ...search.search import SearchResult
from ...utils.kb_utils import load_local_kb # For Local KB search

console = Console()

# Structured output model for search results
class SearchResultAnalysis(BaseModel):
    """Structured output for search result analysis."""
    relevant_urls: list[str] = Field(
        description="List of URLs that are relevant to the query",
        min_items=0
    )
    analysis: str = Field(
        description="Analysis of the search results"
    )

logger = logging.getLogger(__name__)

async def search_node(llm, searcher, scraper, progress_callback, state: AgentState) -> AgentState:
    """
    Search for information based on the current subqueries.
    
    Args:
        llm: Language model to use
        searcher: Search engine to use
        scraper: Web scraper to use
        progress_callback: Callback function for progress updates
        state: Current agent state
        
    Returns:
        Updated agent state
    """
    if is_shutdown_requested():
        state["status"] = "Shutdown requested, skipping search"
        log_chain_of_thought(state, "Shutdown requested, skipping search")
        return state
    
    state["status"] = f"Searching for information (Depth {state['current_depth']})"
    
    breadth = state["breadth"]
    if len(state["subqueries"]) > 0:
        recent_queries = state["subqueries"][-breadth:]
    else:
        recent_queries = [state["query"]]

    async def process_query(query, query_idx):
        if is_shutdown_requested():
            log_chain_of_thought(state, f"Shutdown requested, stopping search after {query_idx} queries")
            return
            
        logger.info(f"Processing query {query_idx+1}/{len(recent_queries)}: {query}")
        console.print(f"Executing search for: {query}")
        state["status"] = f"Searching for: {query}"
        
        # Search for the query using multiple engines for better results
        try:
            # Use multiple engines in parallel for more diverse results
            engines = ["google", "duckduckgo"]  # Using primary engines 
            if query_idx % 2 == 0:  # Add Wikipedia for every other query
                engines.append("wikipedia")
            
            search_results = await searcher.search(query, engines=engines)
            if not search_results:
                logger.warning(f"No search results found for: {query}")
                log_chain_of_thought(state, f"No search results found for '{query}'")
                return
                
        except Exception as e:
            console.print(f"[red]Error during search: {e}[/]")
            log_chain_of_thought(state, f"Error during search for '{query}': {str(e)}")
            return
        
        # Filter relevant URLs in batches to avoid overwhelming the LLM
        relevant_urls = []
        url_batches = [search_results[i:i+10] for i in range(0, len(search_results), 10)]
        
        for batch in url_batches:
            if is_shutdown_requested():
                break

            relevance_tasks = []
            for result in batch:
                relevance_task = is_relevant_url(llm, result.url, result.title, result.snippet, query)
                relevance_tasks.append((result, relevance_task))
            
            # Wait for all relevance checks in this batch
            for result, relevance_task in relevance_tasks:
                try:
                    is_relevant = await relevance_task
                    if is_relevant:
                        relevant_urls.append(result)

                        state["sources"].append({
                            "url": result.url,
                            "title": result.title,
                            "snippet": result.snippet,
                            "source": result.source,
                            "query": query
                        })
                except Exception as e:
                    logger.error(f"Error checking relevance for {result.url}: {e}")
        
        if not relevant_urls:
            log_chain_of_thought(state, f"No relevant URLs found for '{query}'")
            return
        
        # Limit the number of URLs to scrape for efficiency
        # Choose a mix of the most relevant URLs across different sources
        # Sort by source first to ensure diversity, then take top N
        relevant_urls.sort(key=lambda r: r.source)
        relevant_urls = relevant_urls[:8]  # Increased from 5 to 8 for better coverage
        
        # Scrape the relevant URLs all at once using our improved scraper
        urls_to_scrape = [result.url for result in relevant_urls]
        
        # The new scraper implementation handles concurrency internally
        # It will use semaphores to limit concurrent scraping and handle timeouts
        try:
            scraped_contents = await scraper.scrape_urls(
                urls_to_scrape, 
                dynamic=False,  # Avoid dynamic for speed unless specially needed 
                force_refresh=False  # Use caching if available
            )
        except Exception as e:
            logger.error(f"Error scraping URLs for query '{query}': {e}")
            log_chain_of_thought(state, f"Error scraping URLs for query '{query}': {str(e)}")
            return

        processed_items = []
        successful_scrapes = [item for item in scraped_contents if item.is_successful()]

        for item in successful_scrapes:
            if is_shutdown_requested():
                break
                
            logger.info(f"Processing scraped content from: {item.url}")
            content_preview = item.text[:100] + "..." if len(item.text) > 100 else item.text
            logger.debug(f"Content preview: {content_preview}")
            
            processed_item = await process_scraped_item(llm, item, query, item.text)
            processed_items.append(processed_item)
        
        # --- BEGIN: Local KB Search (after web search processing for the current query) ---
        use_local_kb = state.get("use_local_kb", False)
        if use_local_kb:
            console.print(f"[cyan]Searching local KB for: {query}...[/cyan]")
            local_kb_items = load_local_kb() # Assumes kb_utils.py is in shandu/utils/
            local_matches_added_count = 0
            
            current_source_urls_in_state = {s.get("url") for s in state.get("sources", [])}

            for kb_item_dict in local_kb_items:
                title_match = query.lower() in kb_item_dict.get("title", "").lower()
                content_match = query.lower() in kb_item_dict.get("extracted_content", "").lower()

                if title_match or content_match:
                    local_url = kb_item_dict.get("url")
                    if local_url and local_url in current_source_urls_in_state:
                        console.print(f"[dim]Skipping duplicate local KB item: {local_url}[/dim]")
                        continue # Already added, possibly from a previous subquery or identical web URL

                    kb_id = kb_item_dict.get("metadata", {}).get("kb_id")
                    extracted_content = kb_item_dict.get("extracted_content", "")
                    snippet = (extracted_content[:200] + "...") if extracted_content else ""

                    local_source_entry = {
                        "url": local_url,
                        "title": kb_item_dict.get("title", "Local Document"),
                        "snippet": snippet,
                        "source": "LocalKB",
                        "query": query, # Associate with the current subquery
                        "extracted_content": extracted_content,
                        "file_path": kb_item_dict.get("file_path"),
                        "original_filename": kb_item_dict.get("original_filename"),
                        "kb_id": kb_id,
                        # Ensure other fields expected by downstream processes are present or defaulted
                        "relevance_score": 1.0, # Local KB items matched by keyword are considered relevant
                        "initial_relevance_score": 1.0,
                        "retrieved_at": time.time() 
                    }
                    state["sources"].append(local_source_entry)
                    current_source_urls_in_state.add(local_url) # Add to set to prevent duplicates within this query's local search
                    local_matches_added_count += 1
            
            if local_matches_added_count > 0:
                log_chain_of_thought(state, f"Added {local_matches_added_count} sources from Local KB for query '{query}'.")
                console.print(f"[green]Added {local_matches_added_count} sources from Local KB for '{query}'.[/green]")
            else:
                console.print(f"[dim]No relevant items found in local KB for '{query}'.[/dim]")
        # --- END: Local KB Search ---

        # Content analysis should ideally consider both web and local items.
        # For this iteration, local items' content is in state["sources"] but not directly in `processed_items`.
        # The existing `analyze_content` will only use `processed_items` (web content).
        # A future refactor could unify this.

        if not processed_items and not (use_local_kb and local_matches_added_count > 0): # if no web items AND (local kb not used or no local items found)
            log_chain_of_thought(state, f"No content (web or local) could be gathered for analysis for '{query}'")
            return # Skip analysis if nothing to analyze
        
        # Prepare content for analysis - current logic only includes web items from processed_items
        combined_content = ""
        if processed_items: # Only build combined_content if there are web items
            for item in processed_items:
                combined_content += f"\n\n## SOURCE: {item['item'].url}\n"
                combined_content += f"## TITLE: {item['item'].title or 'No title'}\n"
                combined_content += f"## RELIABILITY: {item['rating']}\n"
                combined_content += f"## CONTENT START\n{item['content']}\n## CONTENT END\n"
        
        if combined_content: # Only analyze if there's web content
            analysis = await analyze_content(llm, query, combined_content)
            
            # The 'sources' in content_analysis should reflect what was actually analyzed
            analyzed_source_urls = [item["item"].url for item in processed_items if processed_items]

            state["content_analysis"].append({
                "query": query,
                "sources": analyzed_source_urls, 
                "analysis": analysis
            })
            state["findings"] += f"\n\n## Analysis for: {query}\n\n{analysis}\n\n"
            log_chain_of_thought(state, f"Analyzed web content for query: {query}")
        elif use_local_kb and local_matches_added_count > 0:
            # If only local KB items were found, we might still want a form of "analysis" or summary.
            # For now, we'll just log that web content analysis was skipped.
            log_chain_of_thought(state, f"Skipped web content analysis for '{query}' as only local KB items were found/processed for combined analysis.")


        if progress_callback:
            await _call_progress_callback(progress_callback, state)

    tasks = []
    for idx, query in enumerate(recent_queries):
        tasks.append(process_query(query, idx))
    
    # Use gather to process all queries concurrently but with proper control
    await asyncio.gather(*tasks)
    
    state["current_depth"] += 1
    log_chain_of_thought(state, f"Completed depth {state['current_depth']} of {state['depth']}")

    if progress_callback and state.get("status") != "Searching":
        state["status"] = "Searching completed"
        await _call_progress_callback(progress_callback, state)
    
    return state
