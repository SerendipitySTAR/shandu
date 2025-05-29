"""
Search node for research graph.
"""
import asyncio
import time
import random
import logging
import os
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..processors.content_processor import AgentState, is_relevant_url, process_scraped_item, analyze_content
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback, is_shutdown_requested
from ...search.search import SearchResult
from ...search.local_search import LocalSearcher
from ...local_kb.kb import LocalKB
from ...config import config # Use the global config instance


console = Console()

# Structured output model for search results
class SearchResultAnalysis(BaseModel): # Not used in this node directly, but good to keep for context
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
    Search for information based on the current subqueries, integrating web and local KB search.
    
    Args:
        llm: Language model to use
        searcher: UnifiedSearcher instance for web search
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

    # Load Local KB configurations
    LOCAL_KB_ENABLED = config.get("local_kb", "enabled", False)
    LOCAL_KB_DIR = config.get("local_kb", "kb_dir", "local_kb_data")
    LOCAL_KB_MAX_RESULTS_PER_QUERY = config.get("local_kb", "max_results_per_query", 3)

    local_searcher_instance: Optional[LocalSearcher] = None
    if LOCAL_KB_ENABLED:
        try:
            # Ensure LOCAL_KB_DIR is resolved correctly if it's relative
            # For simplicity, LocalKB itself should handle path resolution (e.g., making it absolute if needed)
            logger.info(f"Attempting to initialize LocalKB with directory: {LOCAL_KB_DIR}")
            local_kb = LocalKB(kb_dir=LOCAL_KB_DIR)
            # Check if LocalKB has an embedding model available via its retriever
            if local_kb.retriever and local_kb.retriever.embedding_model is not None:
                local_searcher_instance = LocalSearcher(local_kb=local_kb, max_results=LOCAL_KB_MAX_RESULTS_PER_QUERY)
                logger.info(f"Local Knowledge Base enabled, using directory: {LOCAL_KB_DIR}")
            else:
                logger.warning(f"LocalKB retriever's embedding model not available. Disabling local search for this run.")
                LOCAL_KB_ENABLED = False # Effectively disable if model is missing
        except ImportError as ie:
            logger.error(f"ImportError during LocalKB/LocalSearcher initialization (likely missing dependencies like sentence-transformers or faiss-cpu): {ie}. Disabling local search.")
            LOCAL_KB_ENABLED = False
        except Exception as e:
            logger.error(f"Failed to initialize LocalKB or LocalSearcher: {e}. Disabling local search for this run.", exc_info=True)
            LOCAL_KB_ENABLED = False # Disable on any other error
    
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
            
            web_search_results: List[SearchResult] = []
            try:
                web_search_results = await searcher.search(query, engines=engines)
            except Exception as e:
                console.print(f"[red]Error during web search for '{query}': {e}[/]")
                log_chain_of_thought(state, f"Error during web search for '{query}': {str(e)}")
            
            local_search_results: List[SearchResult] = []
            if local_searcher_instance:
                try:
                    local_search_results = await local_searcher_instance.search(query) # k is set in LocalSearcher constructor
                    log_chain_of_thought(state, f"Retrieved {len(local_search_results)} results from Local KB for '{query}'")
                except Exception as e:
                    logger.error(f"Error searching Local KB for '{query}': {e}", exc_info=True)
                    log_chain_of_thought(state, f"Error searching Local KB for '{query}': {str(e)}")

            all_search_results = web_search_results + local_search_results
            if not all_search_results:
                logger.warning(f"No search results found from any source for: {query}")
                log_chain_of_thought(state, f"No search results found for '{query}' from any source.")
                return
                
        except Exception as e: # Catch-all for unexpected issues before this point
            console.print(f"[red]Generic error during search phase for '{query}': {e}[/]")
            log_chain_of_thought(state, f"Generic error during search phase for '{query}': {str(e)}")
            return
        
        # Filter relevant sources in batches
        relevant_sources: List[SearchResult] = [] # Holds SearchResult objects
        # Batching helps manage LLM calls for relevance checking if many web results
        # Local results bypass this LLM check for now.
        
        # Process local results first (assumed relevant)
        for local_res in local_search_results:
            if is_shutdown_requested(): break
            relevant_sources.append(local_res)
            state["sources"].append({
                "url": local_res.url, # file://path
                "title": local_res.title,
                "snippet": local_res.snippet,
                "source": local_res.source, # "Local Knowledge Base"
                "query": query
            })
            logger.info(f"Local result '{local_res.url}' considered relevant for query '{query}'. Snippet: {local_res.snippet[:100]}...")

        # Process web results with relevance checking
        web_url_batches = [web_search_results[i:i+10] for i in range(0, len(web_search_results), 10)]
        for batch in web_url_batches:
            if is_shutdown_requested(): break
            relevance_tasks = []
            for result in batch: # result is SearchResult from web
                relevance_task = is_relevant_url(llm, result.url, result.title, result.snippet, query)
                relevance_tasks.append((result, relevance_task))
            
            for result, relevance_task in relevance_tasks:
                if is_shutdown_requested(): break
                try:
                    is_relevant = await relevance_task
                    if is_relevant:
                        relevant_sources.append(result)
                        state["sources"].append({
                            "url": result.url,
                            "title": result.title,
                            "snippet": result.snippet,
                            "source": result.source,
                            "query": query
                        })
                except Exception as e:
                    logger.error(f"Error checking relevance for {result.url}: {e}", exc_info=True)
        
        if not relevant_sources:
            log_chain_of_thought(state, f"No relevant sources (web or local) found for '{query}' after filtering.")
            return
        
        # Limit the number of sources to process further for efficiency
        # Prioritize local sources if many, then web sources.
        # This simple sort puts local first if source name is "Local Knowledge Base" < "Google", etc.
        relevant_sources.sort(key=lambda r: r.source) 
        # Max sources to fully process (scrape/use content from)
        # This can be made configurable.
        MAX_SOURCES_TO_PROCESS = config.get("research", "max_urls_per_query", 3) * 2 # Allow more if local is enabled
        relevant_sources = relevant_sources[:MAX_SOURCES_TO_PROCESS]
        
        processed_items = [] # Holds items for content analysis

        # Separate web and local sources for content processing
        web_sources_to_process = [r for r in relevant_sources if r.source != "Local Knowledge Base"]
        local_sources_to_process = [r for r in relevant_sources if r.source == "Local Knowledge Base"]

        if web_sources_to_process:
            urls_to_scrape = [r.url for r in web_sources_to_process]
            try:
                scraped_web_contents = await scraper.scrape_urls(urls_to_scrape, dynamic=False, force_refresh=False)
                for item_scraped in scraped_web_contents: # item_scraped is ScrapedItem
                    if is_shutdown_requested(): break
                    if item_scraped.is_successful():
                        original_sr = next((s for s in web_sources_to_process if s.url == item_scraped.url), None)
                        query_context = query # Use the main query for context here
                        if original_sr and hasattr(original_sr, 'query') and original_sr.query: # If SearchResult stored its originating query
                             query_context = original_sr.query
                        
                        logger.info(f"Processing scraped web content from: {item_scraped.url}")
                        processed_web_item = await process_scraped_item(llm, item_scraped, query_context, item_scraped.text)
                        processed_items.append(processed_web_item)
            except Exception as e:
                logger.error(f"Error scraping URLs for query '{query}': {e}", exc_info=True)
                log_chain_of_thought(state, f"Error scraping URLs for query '{query}': {str(e)}")
        
        for local_doc_chunk in local_sources_to_process: # local_doc_chunk is SearchResult from LocalSearcher
            if is_shutdown_requested(): break
            logger.info(f"Processing local KB content from: {local_doc_chunk.url}")
            # Content is already in local_doc_chunk.snippet (this is the text chunk)
            # Rating is assumed high for local KB content.
            processed_local_item = {
                "item": local_doc_chunk, # Store the SearchResult object for reference
                "content": local_doc_chunk.snippet, 
                "rating": {"score": 0.95, "reason": "Content from Local Knowledge Base, assumed relevant."},
                "query": query # Query that led to this local result
            }
            processed_items.append(processed_local_item)
        
        if not processed_items:
            log_chain_of_thought(state, f"No content could be extracted or processed (web or local) for '{query}'.")
            return
        
        # Prepare content for analysis in a structured way
        combined_content = ""
        for item_to_analyze in processed_items:
            # Ensure item['item'] has 'url' and 'title' attributes, SearchResult does.
            source_identifier = item_to_analyze['item'].url
            title_text = item_to_analyze['item'].title or 'No title'
            
            combined_content += f"\n\n## SOURCE: {source_identifier}\n"
            combined_content += f"## TITLE: {title_text}\n"
            combined_content += f"## RELIABILITY: {item_to_analyze['rating']}\n" # Rating dict
            combined_content += f"## CONTENT START\n{item_to_analyze['content']}\n## CONTENT END\n"
        
        analysis = await analyze_content(llm, query, combined_content)
        
        state["content_analysis"].append({
            "query": query,
            "sources": [item["item"].url for item in processed_items],
            "analysis": analysis
        })
        
        state["findings"] += f"\n\n## Analysis for: {query}\n\n{analysis}\n\n"
        
        log_chain_of_thought(state, f"Analyzed content for query: {query}")
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
