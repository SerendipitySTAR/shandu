"""
Query generation node for research graph.
"""
import os
import re
from rich.console import Console
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from ..processors.content_processor import AgentState
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback
from ...prompts import SYSTEM_PROMPTS, USER_PROMPTS

console = Console()

# Structured output model for query generation
class SearchQueries(BaseModel):
    """Structured output for search query generation."""
    queries: list[str] = Field(
        description="List of search queries to investigate the topic further",
        min_items=1
    )
    rationale: str = Field(
        description="Explanation of why these queries were selected and how they will help the research"
    )

async def generate_queries_node(llm, progress_callback, state: AgentState) -> AgentState:
    """Generate targeted search queries based on current findings using structured output."""
    state["status"] = "Generating research queries"
    console.print("[bold yellow]Generating targeted search queries...[/]")
    
    try:
        # Use a completely direct approach to avoid template issues
        direct_prompt = f"""Generate {state['breadth']} specific search queries to investigate the topic:

Main Query: {state['query']}

Requirements:
1. Generate exactly {state['breadth']} search queries
2. Queries should be natural and conversational (like what someone would type in Google)
3. Each query should target specific facts, data points, or perspectives
4. Keep queries direct and concise - avoid complex academic phrasing
5. **CRITICAL**: All queries MUST be directly related to the main query topic. Do NOT generate queries about unrelated topics.
6. **FOCUS**: Stay strictly within the scope of the original research question.

Today's date: {state['current_date']}

Current Research Findings (for context only - do not deviate from main topic):
{state['findings'][:2000]}

Return ONLY the search queries themselves, one per line, with no additional text, numbering, or explanation.
Each query must be directly related to: {state['query']}
"""
        # Send the prompt directly to the model
        response = await llm.ainvoke(direct_prompt)

        new_queries = [line.strip() for line in response.content.split("\n") if line.strip()]
        # Remove any numbering, bullet points, or other formatting
        new_queries = [re.sub(r'^[\d\s\-\*•\.\)]+\s*', '', line).strip() for line in new_queries]
        # Remove phrases like "Here are...", "I'll search for..." etc.
        new_queries = [re.sub(r'^(here are|i will|i\'ll|let me|these are|i recommend|completed:|search for:).*?:', '', line, flags=re.IGNORECASE).strip() for line in new_queries]
        # Filter out any empty lines or lines that don't look like actual queries
        new_queries = [q for q in new_queries if q and len(q.split()) >= 2 and not q.lower().startswith(("query", "search", "investigate", "explore", "research"))]

        # 【新增】主题一致性检查 - 过滤掉与原始查询不相关的查询
        original_query_keywords = set(state['query'].lower().split())
        filtered_queries = []
        for query in new_queries:
            query_keywords = set(query.lower().split())
            # 检查是否有共同关键词或相关性
            if original_query_keywords.intersection(query_keywords) or any(keyword in query.lower() for keyword in original_query_keywords):
                filtered_queries.append(query)
            else:
                console.print(f"[yellow]Filtered out unrelated query: {query}[/]")

        new_queries = filtered_queries[:state["breadth"]]
        
        log_chain_of_thought(state, f"Generated {len(new_queries)} search queries for investigation")
        
    except Exception as e:
        from ...utils.logger import log_error
        log_error("Error in structured query generation", e, 
                 context=f"Query: {state['query']}, Function: generate_queries_node")
        console.print(f"[dim red]Error in structured query generation: {str(e)}. Using simpler approach.[/dim red]")
        try:
            # Even simpler fallback approach
            response = await llm.ainvoke(f"Generate {state['breadth']} simple search queries for {state['query']}. Return only the queries, one per line.")

            new_queries = [line.strip() for line in response.content.split("\n") if line.strip()]
            # Remove any numbering, bullet points, or other formatting
            new_queries = [re.sub(r'^[\d\s\-\*•\.\)]+\s*', '', line).strip() for line in new_queries]
            # Remove phrases like "Here are...", "I'll search for..." etc.
            new_queries = [re.sub(r'^(here are|i will|i\'ll|let me|these are|i recommend|completed:|search for:).*?:', '', line, flags=re.IGNORECASE).strip() for line in new_queries]
            # Filter out any empty lines or lines that don't look like actual queries
            new_queries = [q for q in new_queries if q and len(q.split()) >= 2 and not q.lower().startswith(("query", "search", "investigate", "explore", "research"))]
            # Limit to the specified breadth
            new_queries = new_queries[:state["breadth"]]
        except Exception as e2:
            console.print(f"[dim red]Error in fallback query generation: {str(e2)}. Using default queries.[/dim red]")

            new_queries = [
                f"{state['query']} latest research",
                f"{state['query']} examples",
                f"{state['query']} applications"
            ][:state["breadth"]]
    
    if not new_queries and state["query"]:
        new_queries = [state["query"]]
    
    state["messages"].append(HumanMessage(content="Generating new research directions..."))
    state["messages"].append(AIMessage(content="Generated queries:\n" + "\n".join(new_queries)))
    state["subqueries"].extend(new_queries)
    
    console.print("[bold green]Generated search queries:[/]")
    for i, query in enumerate(new_queries, 1):
        console.print(f"  {i}. {query}")
    
    log_chain_of_thought(state, f"Generated {len(new_queries)} search queries for investigation")
    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state
