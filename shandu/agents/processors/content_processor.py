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
        log_error("Error in structured relevance check", e, 
                 context=f"Query: {query}, Function: is_relevant_url")
        console.print(f"[dim red]Error in structured relevance check: {str(e)}. Using simpler approach.[/dim red]")
        # Escape any literal curly braces in the fallback prompt
        safe_fb_url = url.replace("{", "{{").replace("}", "}}")
        safe_fb_title = title.replace("{", "{{").replace("}", "}}")
        safe_fb_snippet = snippet.replace("{", "{{").replace("}", "}}")
        safe_fb_query = query.replace("{", "{{").replace("}", "}}")
        
        simple_prompt = (
            f"Evaluate if this search result is RELEVANT or NOT RELEVANT to the query.\n"
            "Answer with ONLY \"RELEVANT\" or \"NOT RELEVANT\".\n\n"
            f"Query: {safe_fb_query}\n"
            f"Title: {safe_fb_title}\n"
            f"URL: {safe_fb_url}\n"
            f"Snippet: {safe_fb_snippet}"
        )
        response = await llm.ainvoke(simple_prompt)
        result_text = response.content
        return "RELEVANT" in result_text.upper()

async def process_scraped_item(llm: ChatOpenAI, item: ScrapedContent, subquery: str, main_content: str) -> Dict[str, Any]:
    """
    Process a scraped item to evaluate reliability and extract content using structured output.
    """
    try:
        # Escape any literal curly braces in the content to avoid format string errors
        safe_content = main_content[:8000].replace("{", "{{").replace("}", "}}")
        safe_url = item.url.replace("{", "{{").replace("}", "}}")
        safe_title = item.title.replace("{", "{{").replace("}", "}}")
        safe_subquery = subquery.replace("{", "{{").replace("}", "}}")
        
        structured_llm = llm.with_structured_output(ContentRating)
        system_prompt = (
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
        user_message = (
            f"Analyze this web content:\n\n"
            f"URL: {safe_url}\n"
            f"Title: {safe_title}\n"
            f"Query: {safe_subquery}\n\n"
            "Content:\n"
            f"{safe_content}"
        )
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ])
        mapping = {"url": item.url, "title": item.title, "subquery": subquery}
        # Chain the prompt with the structured LLM
        chain = prompt | structured_llm
        result = await chain.ainvoke(mapping)
        return {
            "item": item,
            "rating": result.rating,
            "justification": result.justification,
            "content": result.extracted_content
        }
    except Exception as e:
        from ...utils.logger import log_error
        log_error("Error in structured content processing", e, 
                 context=f"Query: {subquery}, Function: process_scraped_item")
        console.print(f"[dim red]Error in structured content processing: {str(e)}. Using simpler approach.[/dim red]")
        current_file = os.path.basename(__file__)
        # Escape any literal curly braces in the fallback content
        safe_shorter_content = main_content[:5000].replace("{", "{{").replace("}", "}}")
        safe_fb_url = item.url.replace("{", "{{").replace("}", "}}")
        safe_fb_title = item.title.replace("{", "{{").replace("}", "}}")
        safe_fb_subquery = subquery.replace("{", "{{").replace("}", "}}")
        
        simple_prompt = (
            f"Analyze web content for reliability (HIGH/MEDIUM/LOW) and extract relevant information.\n"
            "Format your response as:\n"
            "RELIABILITY: [rating]\n"
            "JUSTIFICATION: [brief explanation]\n"
            "EXTRACTED_CONTENT: [relevant content]\n\n"
            f"URL: {safe_fb_url}\n"
            f"Title: {safe_fb_title}\n"
            f"Query: {safe_fb_subquery}\n\n"
            "Content:\n"
            f"{safe_shorter_content}"
        )
        response = await llm.ainvoke(simple_prompt)
        content = response.content
        rating = "MEDIUM"  # Default fallback rating
        justification = ""
        extracted_content = content

        if "RELIABILITY:" in content:
            reliability_match = re.search(r"RELIABILITY:\s*(HIGH|MEDIUM|LOW)", content)
            if reliability_match:
                rating = reliability_match.group(1)
        if "JUSTIFICATION:" in content:
            justification_match = re.search(r"JUSTIFICATION:\s*(.+?)(?=\n\n|EXTRACTED_CONTENT:|$)", content, re.DOTALL)
            if justification_match:
                justification = justification_match.group(1).strip()
        if "EXTRACTED_CONTENT:" in content:
            content_match = re.search(r"EXTRACTED_CONTENT:\s*(.+?)(?=$)", content, re.DOTALL)
            if content_match:
                extracted_content = content_match.group(1).strip()

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
    try:
        structured_llm = llm.with_structured_output(ContentAnalysis)
        system_prompt = (
            "You are analyzing and synthesizing information from multiple web sources.\n\n"
            "Your task is to:\n"
            "1. Identify the most important and relevant information related to the query\n"
            "2. Extract key findings and main themes\n"
            "3. Organize the information into a coherent analysis\n"
            "4. Evaluate the credibility and relevance of the sources\n"
            "5. Maintain source attributions when presenting facts or claims\n\n"
            "Create a thorough, well-structured analysis that captures the most valuable insights.\n"
        )
        user_message = (
            f"Analyze the following content related to the query: \"{subquery}\"\n\n"
            f"{content_text}\n\n"
            "Provide a comprehensive analysis that synthesizes the most relevant information "
            "from these sources, organized into a well-structured format with key findings."
        )
        # Escape any literal curly braces in the content to avoid format string errors
        system_prompt_escaped = system_prompt.replace("{", "{{").replace("}", "}}")
        user_message_escaped = user_message.replace("{", "{{").replace("}", "}}")
        
        prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": system_prompt_escaped},
            {"role": "user", "content": user_message_escaped}
        ])
        mapping = {"query": subquery}
        # Chain the prompt with the structured LLM (using a modified config if needed)
        chain = prompt | structured_llm.with_config({"timeout": 180})
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
        log_error("Error in structured content analysis", e, 
                 context=f"Query: {subquery}, Function: analyze_content")
        console.print(f"[dim red]Error in structured content analysis: {str(e)}. Using simpler approach.[/dim red]")
        # Escape any literal curly braces in the fallback content
        safe_ac_subquery = subquery.replace("{", "{{").replace("}", "}}")
        safe_ac_content = content_text[:5000].replace("{", "{{").replace("}", "}}")
        
        simple_prompt = (
            f"Analyze and synthesize information from multiple web sources.\n"
            "Provide a concise but comprehensive analysis of the content related to the query.\n\n"
            f"Analyze content related to: {safe_ac_subquery}\n\n"
            f"{safe_ac_content}"
        )
        simple_llm = llm.with_config({"timeout": 60})
        response = await simple_llm.ainvoke(simple_prompt)
        return response.content
