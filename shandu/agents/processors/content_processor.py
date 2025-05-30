"""
Content processing utilities for research agents.
Contains functionality for handling search results, extracting content, and analyzing information.
"""

import os
from typing import List, Dict, Optional, Any, Union, TypedDict, Sequence
from dataclasses import dataclass
import json
import time
import asyncio
import re
from datetime import datetime
from rich.console import Console
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from ...search.search import SearchResult
from ...scraper import WebScraper, ScrapedContent

console = Console()

class AgentState(TypedDict):
    messages: Sequence[Union[HumanMessage, AIMessage]]
    query: str
    depth: int
    breadth: int
    current_depth: int
    findings: str
    sources: List[Dict[str, Any]]
    selected_sources: List[str]
    formatted_citations: str
    subqueries: List[str]
    content_analysis: List[Dict[str, Any]]
    start_time: float
    chain_of_thought: List[str]
    status: str
    current_date: str
    detail_level: str
    identified_themes: str
    initial_report: str
    enhanced_report: str
    final_report: str
    chart_theme: str
    chart_colors: Optional[str]
    report_template: str
    language: str # Added language field
    consistency_suggestions: Optional[str] # For storing feedback from global consistency check

# Structured output models
class UrlRelevanceResult(BaseModel):
    """Structured output for URL relevance check."""
    is_relevant: bool = Field(description="Whether the URL is relevant to the query")
    reason: str = Field(description="Reason for the relevance decision")

class ContentRating(BaseModel):
    """Structured output for content reliability rating."""
    rating: str = Field(description="Reliability rating: HIGH, MEDIUM, or LOW")
    justification: str = Field(description="Justification for the rating")
    extracted_content: str = Field(description="Extracted relevant content from the source")

class ContentAnalysis(BaseModel):
    """Structured output for content analysis."""
    key_findings: List[str] = Field(description="List of key findings from the content")
    main_themes: List[str] = Field(description="Main themes identified in the content")
    analysis: str = Field(description="Comprehensive analysis of the content")
    source_evaluation: str = Field(description="Evaluation of the sources' credibility and relevance")

async def is_relevant_url(llm: ChatOpenAI, url: str, title: str, snippet: str, query: str) -> bool:
    """
    Check if a URL is relevant to the query using structured output.
    """
    # First use simple heuristics to avoid LLM calls for obviously irrelevant domains
    irrelevant_domains = [
        "pinterest", "instagram", "facebook", "twitter", "youtube", "tiktok",
        "reddit", "quora", "linkedin", "amazon.com", "ebay.com", "etsy.com",
        "walmart.com", "target.com"
    ]
    if any(domain in url.lower() for domain in irrelevant_domains):
        return False

    # Escape any literal curly braces in the inputs
    safe_url = url.replace("{", "{{").replace("}", "}}")
    safe_title = title.replace("{", "{{").replace("}", "}}")
    safe_snippet = snippet.replace("{", "{{").replace("}", "}}")
    safe_query = query.replace("{", "{{").replace("}", "}}")
    
    # Use structured output for relevance check
    structured_llm = llm.with_structured_output(UrlRelevanceResult)
    system_prompt = (
        "You are evaluating search results for relevance to a specific query.\n\n"
        "DETERMINE if the search result is RELEVANT or NOT RELEVANT to answering the query.\n"
        "Consider the title, URL, and snippet to make your determination.\n\n"
        "Provide a structured response with your decision and reasoning.\n"
    )
    user_content = (
        f"Query: {safe_query}\n\n"
        f"Search Result:\nTitle: {safe_title}\nURL: {safe_url}\nSnippet: {safe_snippet}\n\n"
        "Is this result relevant to the query?"
    )
    # Build the prompt chain by piping the prompt into the structured LLM.
    prompt = ChatPromptTemplate.from_messages([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ])
    mapping = {"query": query, "title": title, "url": url, "snippet": snippet}
    try:
        # Chain the prompt and structured LLM; then call invoke with the mapping
        chain = prompt | structured_llm
        result = await chain.ainvoke(mapping)
        return result.is_relevant
    except Exception as e:
        from ...utils.logger import log_error

        # Attempt to get raw response from the original prompt for logging purposes (diagnostic)
        raw_content_for_logging = "Could not retrieve raw content for logging diagnostic"
        try:
            # 'prompt' and 'mapping' are from the outer scope relative to the original try block
            # 'llm' is the base LLM passed to is_relevant_url
            temp_chain_for_logging = prompt | llm | StrOutputParser()
            raw_content_for_logging = await temp_chain_for_logging.ainvoke(mapping)
        except Exception as log_e:
            raw_content_for_logging = f"Failed to retrieve raw content for logging diagnostic: {str(log_e)}"

        log_error("Error in structured relevance check (Attempt 1)", e, 
                  context={ 
                      "query": query, 
                      "url": url, 
                      "title": title, 
                      "function": "is_relevant_url",
                      "original_exception_type": e.__class__.__name__,
                      "original_exception": str(e),
                      "diagnostic_raw_content": raw_content_for_logging 
                  })
        console.print(f"[dim red]Error in structured relevance check (Attempt 1) for URL {url}: {str(e)}. Attempting recovery...[/dim red]")
        if raw_content_for_logging != "Could not retrieve raw content for logging diagnostic" and not isinstance(raw_content_for_logging, Exception):
             console.print(f"[dim yellow]Diagnostic raw content from LLM (same prompt, new call): '{raw_content_for_logging}'[/dim yellow]")

        # New Attempt (Second attempt with modified prompt)
        try:
            console.print(f"[dim blue]Retrying relevance check for {url} with explicit JSON prompt...[/dim blue]")
            retry_system_prompt = (
                "You are evaluating search results for relevance to a specific query.\n\n"
                "DETERMINE if the search result is RELEVANT or NOT RELEVANT to answering the query.\n"
                "Consider the title, URL, and snippet to make your determination.\n\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the Pydantic model structure provided by the system.\n"
                "The structure is: class UrlRelevanceResult(BaseModel):\n"
                "    is_relevant: bool\n"
                "    reason: str\n\n"
                "If you cannot determine relevance or encounter an issue, you MUST return a JSON object like: "
                "{\"is_relevant\": false, \"reason\": \"Error: Could not determine relevance due to [your specific issue here].\"}."
            )
            # user_content is defined in the outer scope of the original try block
            retry_prompt_template = ChatPromptTemplate.from_messages([
                {"role": "system", "content": retry_system_prompt},
                {"role": "user", "content": user_content} # user_content from outer scope of original try
            ])
            
            # structured_llm and mapping are from the outer scope of the original try block
            retry_chain = retry_prompt_template | structured_llm
            result = await retry_chain.ainvoke(mapping) 
            console.print(f"[dim green]Successfully parsed relevance for {url} with retry prompt. Relevant: {result.is_relevant}[/dim green]")
            return result.is_relevant

        except Exception as e2:
            log_error("Error in structured relevance check (Attempt 2 - Retry failed)", e2, 
                      context={
                          "query": query,
                          "url": url,
                          "title": title,
                          "function": "is_relevant_url",
                          "original_exception_type": e.__class__.__name__,
                          "original_exception": str(e),
                          "retry_exception_type": e2.__class__.__name__,
                          "retry_exception": str(e2)
                      })
            console.print(f"[dim red]Error in structured relevance check (Attempt 2) for {url}: {str(e2)}. Falling back to simpler approach.[/dim red]")
            
            # Existing fallback mechanism (simpler prompt)
            # Escape any literal curly braces in the fallback prompt
            safe_fb_url = url.replace("{", "{{").replace("}", "}}")
            safe_fb_title = title.replace("{", "{{").replace("}", "}}")
            safe_fb_snippet = snippet.replace("{", "{{").replace("}", "}}")
            safe_fb_query = query.replace("{", "{{").replace("}", "}}")
            
            simple_prompt_text = ( # Renamed variable to avoid conflict if 'simple_prompt' name is used elsewhere
                f"Evaluate if this search result is RELEVANT or NOT RELEVANT to the query.\n"
                "Answer with ONLY \"RELEVANT\" or \"NOT RELEVANT\".\n\n"
                f"Query: {safe_fb_query}\n"
                f"Title: {safe_fb_title}\n"
                f"URL: {safe_fb_url}\n"
                f"Snippet: {safe_fb_snippet}"
            )
            response = await llm.ainvoke(simple_prompt_text)
            result_text = response.content
            return "RELEVANT" in result_text.upper()

async def process_scraped_item(llm: ChatOpenAI, item: ScrapedContent, subquery: str, main_content: str) -> Dict[str, Any]:
    """
    Process a scraped item to evaluate reliability and extract content using structured output.
    """
    # Escape any literal curly braces in the content to avoid format string errors
    safe_content = main_content[:8000].replace("{", "{{").replace("}", "}}")
    safe_url = item.url.replace("{", "{{").replace("}", "}}")
    safe_title = item.title.replace("{", "{{").replace("}", "}}")
    safe_subquery = subquery.replace("{", "{{").replace("}", "}}")
    
    structured_llm = llm.with_structured_output(ContentRating)
    system_prompt_text = ( # Renamed to avoid conflict in case 'system_prompt' is used elsewhere
        "You are analyzing web content for reliability and extracting the most relevant information.\n\n"
        "Evaluate the RELIABILITY of the content using these criteria:\n"
        "1. Source credibility and expertise\n"
        "2. Evidence quality\n"
        "3. Consistency with known facts\n"
        "4. Publication date recency\n"
        "5. Presence of citations or references\n\n"
        "Rate the source as \"HIGH\", \"MEDIUM\", or \"LOW\" reliability with a brief justification.\n\n"
        "Then, EXTRACT the most relevant and valuable content related to the query.\n"
    )
    user_message_text = ( # Renamed to avoid conflict
        f"Analyze this web content:\n\n"
        f"URL: {safe_url}\n"
        f"Title: {safe_title}\n"
        f"Query: {safe_subquery}\n\n"
        "Content:\n"
        f"{safe_content}"
    )
    original_prompt_template = ChatPromptTemplate.from_messages([ # Renamed
        {"role": "system", "content": system_prompt_text},
        {"role": "user", "content": user_message_text}
    ])
    mapping = {"url": item.url, "title": item.title, "subquery": subquery, "content_to_analyze": main_content[:8000]} # Added content for mapping

    try:
        # Chain the prompt with the structured LLM
        chain = original_prompt_template | structured_llm
        result = await chain.ainvoke(mapping)
        return {
            "item": item,
            "rating": result.rating,
            "justification": result.justification,
            "content": result.extracted_content
        }
    except Exception as e:
        from ...utils.logger import log_error

        raw_content_for_logging = "Could not retrieve raw content for logging diagnostic"
        try:
            temp_chain_for_logging = original_prompt_template | llm | StrOutputParser()
            raw_content_for_logging = await temp_chain_for_logging.ainvoke(mapping)
        except Exception as log_e:
            raw_content_for_logging = f"Failed to retrieve raw content for logging diagnostic: {str(log_e)}"

        log_error("Error in structured content processing (Attempt 1)", e, 
                  context={
                      "subquery": subquery,
                      "url": item.url,
                      "title": item.title,
                      "function": "process_scraped_item",
                      "original_exception_type": e.__class__.__name__,
                      "original_exception": str(e),
                      "diagnostic_raw_content": raw_content_for_logging
                  })
        console.print(f"[dim red]Error in structured content processing (Attempt 1) for URL {item.url}: {str(e)}. Attempting recovery...[/dim red]")
        if raw_content_for_logging != "Could not retrieve raw content for logging diagnostic" and not isinstance(raw_content_for_logging, Exception):
             console.print(f"[dim yellow]Diagnostic raw content from LLM (same prompt, new call): '{raw_content_for_logging}'[/dim yellow]")

        # New Attempt (Second attempt with modified prompt)
        try:
            console.print(f"[dim blue]Retrying content processing for {item.url} with explicit JSON prompt...[/dim blue]")
            retry_system_prompt_text = (
                "You are analyzing web content for reliability and extracting the most relevant information.\n\n"
                "Evaluate the RELIABILITY of the content (HIGH, MEDIUM, LOW) and EXTRACT relevant information.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the Pydantic model structure provided by the system.\n"
                "The structure is: class ContentRating(BaseModel):\n"
                "    rating: str = Field(description=\"Reliability rating: HIGH, MEDIUM, or LOW\")\n"
                "    justification: str = Field(description=\"Justification for the rating\")\n"
                "    extracted_content: str = Field(description=\"Extracted relevant content from the source\")\n\n"
                "If you cannot provide a valid response, return JSON like: "
                "{\"rating\": \"LOW\", \"justification\": \"Error: Could not process content due to [issue].\", \"extracted_content\": \"\"}."
            )
            retry_prompt_template = ChatPromptTemplate.from_messages([
                {"role": "system", "content": retry_system_prompt_text},
                {"role": "user", "content": user_message_text} # Use the same user message
            ])
            
            retry_chain = retry_prompt_template | structured_llm
            result = await retry_chain.ainvoke(mapping) # Use the same mapping
            console.print(f"[dim green]Successfully processed content for {item.url} with retry prompt.[/dim green]")
            return {
                "item": item,
                "rating": result.rating,
                "justification": result.justification,
                "content": result.extracted_content
            }
        except Exception as e2:
            log_error("Error in structured content processing (Attempt 2 - Retry failed)", e2, 
                      context={
                          "subquery": subquery,
                          "url": item.url,
                          "title": item.title,
                          "function": "process_scraped_item",
                          "original_exception_type": e.__class__.__name__,
                          "original_exception": str(e),
                          "retry_exception_type": e2.__class__.__name__,
                          "retry_exception": str(e2)
                      })
            console.print(f"[dim red]Error in structured content processing (Attempt 2) for {item.url}: {str(e2)}. Falling back to simpler approach.[/dim red]")

            # Existing fallback mechanism
            # current_file = os.path.basename(__file__) # Not used, can remove
            safe_shorter_content = main_content[:5000].replace("{", "{{").replace("}", "}}")
            # safe_fb_url, safe_fb_title, safe_fb_subquery already defined if needed, or use original safe_url etc.
            # Using original safe_url, safe_title, safe_subquery for fallback prompt
            
            simple_prompt_text = ( # Renamed variable
                f"Analyze web content for reliability (HIGH/MEDIUM/LOW) and extract relevant information.\n"
                "Format your response as:\n"
                "RELIABILITY: [rating]\n"
                "JUSTIFICATION: [brief explanation]\n"
                "EXTRACTED_CONTENT: [relevant content]\n\n"
                f"URL: {safe_url}\n" # Used safe_url from outer scope
                f"Title: {safe_title}\n" # Used safe_title
                f"Query: {safe_subquery}\n\n" # Used safe_subquery
                "Content:\n"
                f"{safe_shorter_content}"
            )
            response = await llm.ainvoke(simple_prompt_text)
            content_str = response.content # Renamed to avoid conflict
            rating = "MEDIUM" 
            justification = "Fallback due to parsing error." # Default justification for fallback
            extracted_content = content_str # Default to full content if regex fails

            # Regex parsing from original fallback
            reliability_match = re.search(r"RELIABILITY:\s*(HIGH|MEDIUM|LOW)", content_str, re.IGNORECASE)
            if reliability_match:
                rating = reliability_match.group(1).upper()
            
            justification_match = re.search(r"JUSTIFICATION:\s*(.*?)(?=\nEXTRACTED_CONTENT:|\nRELIABILITY:|$)", content_str, re.IGNORECASE | re.DOTALL)
            if justification_match:
                justification = justification_match.group(1).strip()
            
            content_match = re.search(r"EXTRACTED_CONTENT:\s*(.*)", content_str, re.IGNORECASE | re.DOTALL)
            if content_match:
                extracted_content = content_match.group(1).strip()
            else: # If no EXRACTED_CONTENT label, try to take what's after justification
                fallback_content_parts = content_str.split("EXTRACTED_CONTENT:", 1)
                if len(fallback_content_parts) > 1:
                     extracted_content = fallback_content_parts[1].strip()
                elif not justification_match : # if no labels at all, use a portion of the content
                     extracted_content = content_str[:2000]


            return {
                "item": item,
                "rating": rating,
                "justification": justification,
                "content": extracted_content
            }

async def analyze_content(llm: ChatOpenAI, subquery: str, content_text: str) -> str:
    """
    Analyze content from multiple sources and synthesize the information using structured output.
    """
    structured_llm_instance = llm.with_structured_output(ContentAnalysis) # Renamed instance
    
    # Original system and user message definitions
    system_prompt_text = ( # Renamed
        "You are analyzing and synthesizing information from multiple web sources.\n\n"
        "Your task is to:\n"
        "1. Identify the most important and relevant information related to the query\n"
        "2. Extract key findings and main themes\n"
        "3. Organize the information into a coherent analysis\n"
        "4. Evaluate the credibility and relevance of the sources\n"
        "5. Maintain source attributions when presenting facts or claims\n\n"
        "Create a thorough, well-structured analysis that captures the most valuable insights.\n"
    )
    user_message_text = ( # Renamed
        f"Analyze the following content related to the query: \"{subquery}\"\n\n"
        f"{content_text}\n\n" # content_text can be large, ensure it's handled
        "Provide a comprehensive analysis that synthesizes the most relevant information "
        "from these sources, organized into a well-structured format with key findings."
    )
    # Escape any literal curly braces
    system_prompt_escaped = system_prompt_text.replace("{", "{{").replace("}", "}}")
    user_message_escaped = user_message_text.replace("{", "{{").replace("}", "}}") # This might truncate if content_text is huge.
                                                                               # However, LLMs handle large contexts. Assuming it's fine.

    original_prompt_template = ChatPromptTemplate.from_messages([ # Renamed
        {"role": "system", "content": system_prompt_escaped},
        {"role": "user", "content": user_message_escaped}
    ])
    # Mapping might need to include content_text if not part of user_message_escaped for some reason,
    # but here user_message_escaped already incorporates content_text.
    mapping = {"query": subquery, "input": content_text} # 'input' is a common key for LangChain invoke.

    try:
        chain = original_prompt_template | structured_llm_instance.with_config({"timeout": 180})
        result = await chain.ainvoke(mapping)
        
        formatted_analysis = "### Key Findings\n\n"
        for i, finding in enumerate(result.key_findings, 1):
            formatted_analysis += f"{i}. {finding}\n"
        formatted_analysis += "\n### Main Themes\n\n"
        for i, theme in enumerate(result.main_themes, 1):
            formatted_analysis += f"{i}. {theme}\n"
        formatted_analysis += f"\n### Analysis\n\n{result.analysis}\n"
        formatted_analysis += f"\n### Source Evaluation\n\n{result.source_evaluation}\n"
        return formatted_analysis
    except Exception as e:
        from ...utils.logger import log_error

        raw_content_for_logging = "Could not retrieve raw content for logging diagnostic"
        try:
            temp_chain_for_logging = original_prompt_template | llm | StrOutputParser() # Use base llm
            raw_content_for_logging = await temp_chain_for_logging.ainvoke(mapping)
        except Exception as log_e:
            raw_content_for_logging = f"Failed to retrieve raw content for logging diagnostic: {str(log_e)}"

        log_error("Error in structured content analysis (Attempt 1)", e, 
                  context={
                      "subquery": subquery,
                      "function": "analyze_content",
                      "original_exception_type": e.__class__.__name__,
                      "original_exception": str(e),
                      "diagnostic_raw_content_length": len(raw_content_for_logging), # Log length due to potential size
                      "diagnostic_raw_content_preview": raw_content_for_logging[:500] # Log a preview
                  })
        console.print(f"[dim red]Error in structured content analysis (Attempt 1) for query '{subquery}': {str(e)}. Attempting recovery...[/dim red]")
        if raw_content_for_logging != "Could not retrieve raw content for logging diagnostic" and not isinstance(raw_content_for_logging, Exception):
             console.print(f"[dim yellow]Diagnostic raw content preview (Attempt 1): '{raw_content_for_logging[:200]}...'[/dim yellow]")
        
        # New Attempt (Second attempt with modified prompt)
        try:
            console.print(f"[dim blue]Retrying content analysis for query '{subquery}' with explicit JSON prompt...[/dim blue]")
            retry_system_prompt_text = (
                "You are analyzing and synthesizing information from multiple web sources.\n\n"
                "Your task is to:\n"
                "1. Identify key findings and main themes related to the query.\n"
                "2. Provide a coherent analysis and evaluate source credibility.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the Pydantic model structure provided by the system.\n"
                "The structure is: class ContentAnalysis(BaseModel):\n"
                "    key_findings: List[str]\n"
                "    main_themes: List[str]\n"
                "    analysis: str\n"
                "    source_evaluation: str\n\n"
                "If you cannot provide a valid response, return JSON like: "
                "{\"key_findings\": [\"Error: Analysis failed\"], \"main_themes\": [], \"analysis\": \"Could not perform analysis due to [issue].\", \"source_evaluation\": \"N/A\"}."
            )
            # user_message_escaped is from the outer scope
            retry_prompt_template = ChatPromptTemplate.from_messages([
                {"role": "system", "content": retry_system_prompt_text}, # Note: Escaping not strictly needed here as it's a fixed string.
                {"role": "user", "content": user_message_escaped} 
            ])
            
            retry_chain = retry_prompt_template | structured_llm_instance.with_config({"timeout": 180})
            result = await retry_chain.ainvoke(mapping) # Use the same mapping
            
            console.print(f"[dim green]Successfully analyzed content for query '{subquery}' with retry prompt.[/dim green]")
            # Format the result as in the original try block
            formatted_analysis = "### Key Findings\n\n"
            for i, finding in enumerate(result.key_findings, 1):
                formatted_analysis += f"{i}. {finding}\n"
            formatted_analysis += "\n### Main Themes\n\n"
            for i, theme in enumerate(result.main_themes, 1):
                formatted_analysis += f"{i}. {theme}\n"
            formatted_analysis += f"\n### Analysis\n\n{result.analysis}\n"
            formatted_analysis += f"\n### Source Evaluation\n\n{result.source_evaluation}\n"
            return formatted_analysis

        except Exception as e2:
            log_error("Error in structured content analysis (Attempt 2 - Retry failed)", e2, 
                      context={
                          "subquery": subquery,
                          "function": "analyze_content",
                          "original_exception_type": e.__class__.__name__,
                          "original_exception": str(e),
                          "retry_exception_type": e2.__class__.__name__,
                          "retry_exception": str(e2)
                      })
            console.print(f"[dim red]Error in structured content analysis (Attempt 2) for query '{subquery}': {str(e2)}. Falling back to simpler approach.[/dim red]")

            # Existing fallback mechanism
            safe_ac_subquery = subquery.replace("{", "{{").replace("}", "}}")
            # Ensure content_text is also sliced for the fallback to avoid overly large prompts
            safe_ac_content = content_text[:10000].replace("{", "{{").replace("}", "}}") # Increased slice for fallback analysis
            
            simple_prompt_text = ( # Renamed variable
                f"Analyze and synthesize information from multiple web sources.\n"
                "Provide a concise but comprehensive analysis of the content related to the query.\n\n"
                f"Analyze content related to: {safe_ac_subquery}\n\n"
                f"{safe_ac_content}"
            )
            # Use the base llm, not structured_llm_instance for simple fallback
            simple_llm_call = llm.with_config({"timeout": 60}) # Fallback uses base llm
            response = await simple_llm_call.ainvoke(simple_prompt_text)
            return response.content
