"""
CLI interface for Shandu deep research system.
Provides commands for configuration and research with rich display.
"""
import os
import sys
import json
import asyncio
import time
import signal
import threading
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
import click
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.markdown import Markdown
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.syntax import Syntax
from langchain_openai import ChatOpenAI
from .config import config
from .agents.langgraph_agent import clarify_query, display_research_progress
from .agents.langgraph_agent import ResearchGraph, AgentState
from .search.search import UnifiedSearcher
from .search.ai_search import AISearcher
from .scraper import WebScraper
from .research.researcher import DeepResearcher
from .agents.utils.agent_utils import is_shutdown_requested, get_shutdown_level
from .agents.utils.citation_manager import SourceInfo # For Local KB
from .document_parser import parse_document # For Local KB
from .utils.kb_utils import load_local_kb, save_local_kb, generate_kb_id, _ensure_kb_dir_exists as ensure_kb_dir_for_cli # Renamed to avoid conflict
import dataclasses # For Local KB (asdict)
# hashlib is now used within kb_utils.py

console = Console()

# Global flag for force exit
_force_exit_requested = False
_force_exit_lock = threading.Lock()

def sanitize_markup(text):
    """
    Universal sanitizer for any text that will be displayed using Rich.
    
    This function prevents any square bracket content from being interpreted as
    Rich markup tags. It can be used on any text that will be displayed in the console.
    
    Args:
        text: The text to sanitize
        
    Returns:
        Sanitized text safe for Rich console display
    """

    text_str = str(text)
    
    # Step 1: Remove empty brackets which can be interpreted as empty tags
    text_str = re.sub(r'\[\]', '', text_str)
    
    # Step 2: Remove any PDF-style tags that often cause problems with Rich
    text_str = re.sub(r'\[\/?(?:PDF|Text|ImageB|ImageC|ImageI)(?:\/?|\])(?:[^\]]*\])?', '', text_str)
    
    # Step 3: Remove any orphaned or malformed tags
    text_str = re.sub(r'\[\/?[^\]]*\]?', '', text_str)
    
    # Step 4: Remove all remaining square bracket content that could be misinterpreted
    text_str = re.sub(r'\[[^\]]*\]', '', text_str)
    
    # Step 5: Escape the entire string to handle any other Rich markup characters
    return escape(text_str)

def sanitize_error(error_msg):
    """
    Sanitize error messages to prevent Rich markup errors.
    
    This function removes all potential Rich markup from error messages
    to prevent rendering errors in the console.
    """
    return sanitize_markup(error_msg)

def setup_force_exit_handler():
    """Set up a force exit handler for the CLI."""
    def force_exit_handler(sig, frame):
        global _force_exit_requested
        with _force_exit_lock:
            _force_exit_requested = True
            console.print("\n[bold red]Force exit requested. Exiting immediately.[/]")
            os._exit(1)  # Force exit
    
    # Register the handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, force_exit_handler)

def display_banner():
    """Display the Shandu banner."""
    banner = """
    ███████╗██╗  ██╗ █████╗ ███╗   ██╗██████╗ ██╗   ██╗
    ██╔════╝██║  ██║██╔══██╗████╗  ██║██╔══██╗██║   ██║
    ███████╗███████║███████║██╔██╗ ██║██║  ██║██║   ██║
    ╚════██║██╔══██║██╔══██║██║╚██╗██║██║  ██║██║   ██║
    ███████║██║  ██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ 
                Deep Research System
    """
    console.print(Panel(banner, style="bold blue"))

def create_research_dashboard(state: AgentState) -> Layout:
    """Create a rich dashboard layout for research progress."""
    layout = Layout()
    
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=1)
    )
    layout["left"].split(
        Layout(name="status", size=5), # Increased size for Last Activity
        Layout(name="progress", size=3),
        Layout(name="themes_panel", ratio=1, minimum_size=3, visible=False), 
        Layout(name="findings", ratio=2)
    )
    layout["right"].split(
        Layout(name="queries", ratio=1),
        Layout(name="sources", ratio=1),
        Layout(name="selected_titles_panel", ratio=1, minimum_size=3, visible=False),
        Layout(name="chain_of_thought", ratio=1)
    )
    
    elapsed_time = time.time() - state.get("start_time", time.time()) # Use .get for safety
    minutes, seconds = divmod(int(elapsed_time), 60)
    header_content = f"[bold blue]Research Query:[/] {state['query']}\n"
    header_content += f"[bold blue]Status:[/] {state['status']} | "
    header_content += f"[bold blue]Time:[/] {minutes}m {seconds}s | "
    header_content += f"[bold blue]Depth:[/] {state['current_depth']}/{state['depth']}"
    layout["header"].update(Panel(header_content, title="Shandu Deep Research"))
    
    status_table = Table(show_header=False, box=None)
    status_table.add_column("Metric", style="blue")
    status_table.add_column("Value")
    status_table.add_row("Current Depth", f"{state.get('current_depth', 0)}/{state.get('depth', 0)}")
    status_table.add_row("Sources Found", str(len(state.get('sources', []))))
    status_table.add_row("Subqueries Explored", str(len(state.get('subqueries', []))))
    last_activity_text = state.get("last_node_activity", "N/A")
    status_table.add_row("Last Activity", sanitize_markup(last_activity_text))
    layout["status"].update(Panel(status_table, title="Research Progress"))

    # Themes Panel
    current_themes_text = state.get("current_extracted_themes")
    if current_themes_text:
        layout["themes_panel"].visible = True
        layout["themes_panel"].update(Panel(Markdown(sanitize_markup(current_themes_text)), title="Extracted Themes"))
    else:
        layout["themes_panel"].visible = False # Or update with "No themes yet."

    progress_percent = min(100, int((state.get('current_depth', 0) / max(1, state.get('depth', 1))) * 100)) # Avoid division by zero
    progress_bar = f"[{'#' * (progress_percent // 5)}{' ' * (20 - progress_percent // 5)}] {progress_percent}%"
    layout["progress"].update(Panel(progress_bar, title="Completion"))
    
    findings_text = state["findings"][-2000:] if state["findings"] else "No findings yet..."
    layout["findings"].update(Panel(Markdown(findings_text), title="Latest Findings"))
    queries_table = Table(show_header=True)
    queries_table.add_column("#", style="dim")
    queries_table.add_column("Query")
    for i, query in enumerate(state["subqueries"][-10:], 1):  # Show last 10 queries
        queries_table.add_row(str(i), query)
    layout["queries"].update(Panel(queries_table, title="Research Paths"))
    
    sources_table = Table(show_header=True)
    sources_table.add_column("Source", style="dim")
    sources_table.add_column("Count")
    source_counts = {}
    for source in state["sources"]:
        source_type = source.get("source", "Unknown")
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
    for source_type, count in source_counts.items():
        sources_table.add_row(source_type, str(count))
    layout["sources"].update(Panel(sources_table, title="Sources Overview"))

    # Selected Source Titles Panel
    current_selected_titles = state.get("current_selected_source_titles")
    if current_selected_titles and isinstance(current_selected_titles, list) and len(current_selected_titles) > 0:
        titles_display_text = "\n".join([f"{i+1}. {sanitize_markup(title)}" for i, title in enumerate(current_selected_titles)])
        layout["selected_titles_panel"].visible = True
        layout["selected_titles_panel"].update(Panel(titles_display_text, title=f"Selected Source Titles ({len(current_selected_titles)})"))
    else:
        layout["selected_titles_panel"].visible = False # Or update with "No titles yet."
    
    cot_text = "\n".join(state.get("chain_of_thought", [])[-5:]) if state.get("chain_of_thought") else "No thoughts recorded yet..."
    layout["chain_of_thought"].update(Panel(cot_text, title="Chain of Thought (Last 5)"))
    
    footer_text = "Press Ctrl+C to stop research"
    if is_shutdown_requested():
        shutdown_level = get_shutdown_level()
        footer_text = f"[yellow]Shutdown requested (attempt {shutdown_level}). Press Ctrl+C {4 - shutdown_level} more times to force exit.[/]"
    
    layout["footer"].update(Panel(footer_text, style="dim"))
    
    return layout

@click.group()
def cli():
    """Shandu deep research system."""

    setup_force_exit_handler()
    display_banner()
    pass

@cli.command()
def configure():
    """Configure API settings."""
    console.print(Panel("Configure Shandu API Settings", style="bold blue"))

    api_base = click.prompt(
        "OpenAI API Base URL",
        default=config.get("api", "base_url")
    )
    api_key = click.prompt(
        "OpenAI API Key",
        default=config.get("api", "api_key"),
        hide_input=True
    )
    model = click.prompt(
        "Model Name",
        default=config.get("api", "model")
    )
    proxy = click.prompt(
        "Proxy URL (optional, press Enter to skip)",
        default="",
        show_default=False
    )
    
    user_agent = click.prompt(
        "User Agent",
        default=config.get("search", "user_agent")
    )
    
    # Save config
    config.set("api", "base_url", api_base)
    config.set("api", "api_key", api_key)
    config.set("api", "model", model)
    config.set("scraper", "proxy", proxy)
    config.set("search", "user_agent", user_agent)
    config.save()
    
    console.print(Panel("[green]Configuration saved successfully!", 
                       title="Success", 
                       border_style="green"))

@cli.command()
def info():
    """Display information about the current configuration."""
    console.print(Panel("Shandu Configuration Information", style="bold blue"))
    
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("API Base URL", config.get("api", "base_url"))
    table.add_row("API Key", "****" + config.get("api", "api_key")[-4:] if config.get("api", "api_key") else "Not set")
    table.add_row("Model", config.get("api", "model"))
    
    table.add_row("Default Search Engines", ", ".join(config.get("search", "engines")))
    table.add_row("User Agent", config.get("search", "user_agent"))
    
    table.add_row("Default Depth", str(config.get("research", "default_depth")))
    table.add_row("Default Breadth", str(config.get("research", "default_breadth")))
    
    console.print(table)

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation")
@click.option("--cache-only", "-c", is_flag=True, help="Delete only cache files, keep configuration")
def clean(force: bool, cache_only: bool):
    """Delete configuration and cache files."""
    config_path = os.path.expanduser("~/.shandu")
    
    if not os.path.exists(config_path):
        console.print("[yellow]No configuration or cache files found.[/]")
        return
    
    if cache_only:
        cache_path = os.path.join(config_path, "cache")
        if os.path.exists(cache_path):
            if not force:
                confirm = click.confirm(f"Are you sure you want to delete all cache files in {cache_path}?")
                if not confirm:
                    console.print("[yellow]Operation cancelled.[/]")
                    return
            
            try:
                import shutil
                shutil.rmtree(cache_path)
                console.print(Panel("[green]Cache files deleted successfully!", 
                                   title="Success", 
                                   border_style="green"))
            except Exception as e:
                console.print(f"[red]Error deleting cache files: {sanitize_error(e)}[/]")
        else:
            console.print("[yellow]No cache files found.[/]")
    else:
        if not force:
            confirm = click.confirm(f"Are you sure you want to delete all configuration and cache files in {config_path}?")
            if not confirm:
                console.print("[yellow]Operation cancelled.[/]")
                return
        
        try:
            import shutil
            shutil.rmtree(config_path)
            console.print(Panel("[green]Configuration and cache files deleted successfully!", 
                               title="Success", 
                               border_style="green"))
        except Exception as e:
            console.print(f"[red]Error deleting configuration: {sanitize_error(e)}[/]")

@cli.command()
@click.argument("query")
@click.option("--depth", "-d", default=None, type=int, help="Research depth (1-5)")
@click.option("--breadth", "-b", default=None, type=int, help="Research breadth (3-10)")
@click.option("--output", "-o", help="Save report to file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
@click.option("--strategy", "-s", default="langgraph", type=click.Choice(["langgraph", "agent"]), 
              help="Research strategy to use")
@click.option("--include-chain-of-thought", "-c", is_flag=True, help="Include chain of thought in report")
@click.option("--include-objective", "-i", is_flag=True, help="Include objective section in report")
@click.option(
    "--use-local-kb",
    is_flag=True,
    default=False,
    help="Enable searching within the local knowledge base."
)
def research(
    query: str, 
    depth: Optional[int], 
    breadth: Optional[int], 
    output: Optional[str], 
    verbose: bool,
    strategy: str,
    include_chain_of_thought: bool,
    include_objective: bool,
    use_local_kb: bool # New parameter
):
    """Perform deep research on a topic."""
    if depth is None:
        depth = config.get("research", "default_depth", 2)
    if breadth is None:
        breadth = config.get("research", "default_breadth", 4)
    
    if depth < 1 or depth > 5:
        console.print("[red]Error: Depth must be between 1 and 5[/]")
        sys.exit(1)
    if breadth < 2 or breadth > 10:
        console.print("[red]Error: Breadth must be between 2 and 10[/]")
        sys.exit(1)
    
    api_base = config.get("api", "base_url")
    api_key = config.get("api", "api_key")
    model = config.get("api", "model")
    temperature = config.get("api", "temperature", 0)
    
    llm = ChatOpenAI(
        base_url=api_base,
        api_key=api_key,
        model=model,
        temperature=temperature
    )
    
    searcher = UnifiedSearcher()
    scraper = WebScraper(proxy=config.get("scraper", "proxy"))
    
    console.print(Panel(
        f"[bold blue]Query:[/] {query}\n"
        f"[bold blue]Depth:[/] {depth}\n"
        f"[bold blue]Breadth:[/] {breadth}\n"
        f"[bold blue]Strategy:[/] {strategy}\n"
        f"[bold blue]Local KB Search:[/] {'Enabled' if use_local_kb else 'Disabled'}\n"
        f"[bold blue]Model:[/] {model}",
        title="Research Parameters",
        border_style="blue"
    ))
    
    try:
        refined_query = asyncio.run(clarify_query(query, llm))
    except KeyboardInterrupt:
        console.print("\n[yellow]Query clarification cancelled. Using original query.[/]")
        refined_query = query

    if strategy == "langgraph":
        graph = ResearchGraph(llm=llm, searcher=searcher, scraper=scraper)

        with Live(console=console, auto_refresh=True, screen=False, transient=False) as live:
            console.print("[bold green]Starting research...[/]")
            console.print("[bold blue]This will show detailed information about the search process and pages being analyzed.[/]")
            console.print("[dim]The research process may take some time depending on depth and breadth settings.[/]")
            console.print("[dim]You'll see search queries, selected URLs, and content analysis in real-time.[/]")
            
            # Track the last displayed state hash to avoid duplicate updates
            last_state_hash = None
            
            def debounced_update_display(state):
                nonlocal last_state_hash

                # Only consider elements that should trigger a UI refresh
                status = state.get("status", "")
                current_depth = state.get("current_depth", 0)
                sources_count = len(state.get("sources", []))
                subqueries_count = len(state.get("subqueries", []))

                current_hash = f"{status}_{current_depth}_{sources_count}_{subqueries_count}"
                
                # Only update if there's a meaningful change to display
                if current_hash != last_state_hash:
                    last_state_hash = current_hash
                    
                    if verbose:
                        dashboard = create_research_dashboard(state)
                        live.update(dashboard)
                    else:
                        tree = display_research_progress(state)
                        live.update(tree)
            
            try:
                result = graph.research_sync(
                    refined_query,
                    depth=depth,
                    breadth=breadth,
                    progress_callback=debounced_update_display,
                    include_objective=include_objective,
                    use_local_kb=use_local_kb # Pass new flag
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Research interrupted by user.[/]")
                sys.exit(0)
            except Exception as e:
                # Use the universal sanitizer for the error message
                error_msg = sanitize_markup(str(e))
                console.print(f"\n[red]Error during research: {error_msg}[/]")
                sys.exit(1)
    else:
        # Use agent-based research
        from .agents.agent import ResearchAgent
        agent = ResearchAgent(llm=llm, searcher=searcher, scraper=scraper)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]Researching...", total=depth)
            
            try:
                result = agent.research_sync(
                    refined_query,
                    depth=depth,
                    engines=config.get("search", "engines")
                )
                
                progress.update(task, completed=depth)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Research interrupted by user.[/]")
                sys.exit(0)
            except Exception as e:
                console.print(f"\n[red]Error during research: {sanitize_error(e)}[/]")
                sys.exit(1)
    
    # Display result
    console.print("\n[bold green]Research complete![/]")
    
    if output:
        result.save_to_file(output, include_chain_of_thought, include_objective)
        console.print(f"[green]Report saved to {output}[/]")
    else:
        console.print(Markdown(result.to_markdown(include_chain_of_thought, include_objective)))

@cli.command()
@click.argument("query")
@click.option("--engines", "-e", default=None, help="Comma-separated list of search engines to use")
@click.option("--max-results", "-m", default=10, type=int, help="Maximum number of results to return")
@click.option("--output", "-o", help="Save results to file")
@click.option("--detailed", "-d", is_flag=True, help="Generate a detailed analysis")
def aisearch(query: str, engines: Optional[str], max_results: int, output: Optional[str], detailed: bool):
    """Perform AI-powered search with analysis of results."""
    if engines:
        engine_list = [e.strip() for e in engines.split(",")]
    else:
        engine_list = config.get("search", "engines")
    
    api_base = config.get("api", "base_url")
    api_key = config.get("api", "api_key")
    model = config.get("api", "model")
    temperature = config.get("api", "temperature", 0)
    
    llm = ChatOpenAI(
        base_url=api_base,
        api_key=api_key,
        model=model,
        temperature=temperature
    )
    
    searcher = UnifiedSearcher(max_results=max_results)
    ai_searcher = AISearcher(llm=llm, searcher=searcher, max_results=max_results)
    
    console.print(Panel(
        f"[bold blue]Query:[/] {query}\n"
        f"[bold blue]Engines:[/] {', '.join(engine_list)}\n"
        f"[bold blue]Max Results:[/] {max_results}\n"
        f"[bold blue]Analysis:[/] {'Detailed' if detailed else 'Concise'}",
        title="AI Search Parameters",
        border_style="blue"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Searching and analyzing...", total=1)
        
        try:
            result = ai_searcher.search_sync(query, engine_list, detailed)
            progress.update(task, completed=1)
        except Exception as e:
            console.print(f"[red]Error during AI search: {sanitize_error(e)}[/]")
            sys.exit(1)
    
    # Display result
    console.print("\n[bold green]Search and analysis complete![/]")
    
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result.to_markdown())
        console.print(f"[green]Results saved to {output}[/]")
    else:
        console.print(Markdown(result.to_markdown()))

@cli.command()
@click.argument("query")
@click.option("--engines", "-e", default=None, help="Comma-separated list of search engines to use")
@click.option("--max-results", "-m", default=10, type=int, help="Maximum number of results to return")
def search(query: str, engines: Optional[str], max_results: int):
    """Perform a quick search without deep research."""
    if engines:
        engine_list = [e.strip() for e in engines.split(",")]
    else:
        engine_list = config.get("search", "engines")
    searcher = UnifiedSearcher(max_results=max_results)
    console.print(Panel(
        f"[bold blue]Query:[/] {query}\n"
        f"[bold blue]Engines:[/] {', '.join(engine_list)}\n"
        f"[bold blue]Max Results:[/] {max_results}",
        title="Search Parameters",
        border_style="blue"
    ))
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Searching...", total=1)
        
        try:
            results = searcher.search_sync(query, engine_list)
            progress.update(task, completed=1)
            
        except Exception as e:
            console.print(f"[red]Error during search: {sanitize_error(e)}[/]")
            sys.exit(1)
    
    console.print(f"\n[bold green]Found {len(results)} results:[/]")

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Source", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("URL", style="blue")
    table.add_column("Snippet", style="dim")
    
    for result in results:
        table.add_row(
            result.source,
            result.title[:50] + "..." if len(result.title) > 50 else result.title,
            result.url[:50] + "..." if len(result.url) > 50 else result.url,
            result.snippet[:100] + "..." if len(result.snippet) > 100 else result.snippet
        )
    
    console.print(table)

@cli.command()
@click.argument("url")
@click.option("--dynamic", "-d", is_flag=True, help="Use dynamic rendering (for JavaScript-heavy sites)")
def scrape(url: str, dynamic: bool):
    """Scrape and analyze a webpage."""
    scraper = WebScraper(proxy=config.get("scraper", "proxy"))
    
    console.print(Panel(
        f"[bold blue]URL:[/] {url}\n"
        f"[bold blue]Dynamic Rendering:[/] {'Enabled' if dynamic else 'Disabled'}",
        title="Scrape Parameters",
        border_style="blue"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Scraping...", total=1)
        
        try:
            result = asyncio.run(scraper.scrape_url(url, dynamic=dynamic))
            progress.update(task, completed=1)
            
        except Exception as e:
            console.print(f"[red]Error during scraping: {sanitize_error(e)}[/]")
            sys.exit(1)
    
    if result.is_successful():
        console.print(f"\n[bold green]Successfully scraped {url}[/]")
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )
        layout["body"].split_row(
            Layout(name="content", ratio=2),
            Layout(name="metadata", ratio=1)
        )
        
        header_content = f"[bold blue]Title:[/] {result.title}\n"
        header_content += f"[bold blue]URL:[/] {result.url}\n"
        header_content += f"[bold blue]Content Type:[/] {result.content_type}"
        layout["header"].update(Panel(header_content, title="Page Information"))
        content_preview = result.text[:2000] + "..." if len(result.text) > 2000 else result.text
        layout["content"].update(Panel(content_preview, title="Content Preview"))
        metadata_table = Table(show_header=True)
        metadata_table.add_column("Key", style="cyan")
        metadata_table.add_column("Value", style="green")
        
        for key, value in result.metadata.items():
            if value and isinstance(value, str):
                metadata_table.add_row(key, value[:50] + "..." if len(value) > 50 else value)
        
        layout["metadata"].update(Panel(metadata_table, title="Metadata"))
        
        console.print(layout)
    else:
        console.print(f"[red]Failed to scrape {url}: {result.error}[/]")

if __name__ == "__main__":
    cli()

# --- Local Knowledge Base CLI Commands ---
@cli.group()
def local():
    """Manage the local knowledge base."""
    _ensure_kb_dir_exists() # Ensure directory exists when group is invoked
    pass

@local.command("add")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def add(file_path: str):
    """Add a document to the local knowledge base."""
    console.print(f"Attempting to add document: {file_path}")

    parsed_info = parse_document(file_path)

    if parsed_info is None or parsed_info.get("metadata", {}).get("error"):
        error_message = parsed_info.get("metadata", {}).get("error", "Failed to parse document.") if parsed_info else "Failed to parse document."
        console.print(f"[red]Error parsing document: {sanitize_error(error_message)}[/red]")
        return

    kb_id = generate_kb_id(file_path)
    kb_data = load_local_kb()

    if any(item.get("metadata", {}).get("kb_id") == kb_id for item in kb_data):
        console.print(f"[red]Error: Document with ID {kb_id} (from path {file_path}) already exists in the knowledge base.[/red]")
        return

    try:
        stat_info = os.stat(file_path)
        creation_date = stat_info.st_ctime
        last_modified_date = stat_info.st_mtime
    except Exception as e:
        console.print(f"[yellow]Warning: Could not retrieve file dates for {file_path}: {sanitize_error(e)}[/yellow]")
        creation_date = time.time() # Fallback to current time
        last_modified_date = time.time() # Fallback to current time

    file_extension = os.path.splitext(file_path)[1].lower()
    content_type_map = {
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    
    source_info_metadata = parsed_info.get("metadata", {})
    source_info_metadata["kb_id"] = kb_id # Add kb_id to the document's own metadata

    source_info_obj = SourceInfo(
        url="localfile:" + kb_id,
        title=parsed_info.get("title") or os.path.basename(file_path),
        source_type=f"local_{file_extension.strip('.')}",
        content_type=content_type_map.get(file_extension, "application/octet-stream"),
        file_path=file_path,
        original_filename=os.path.basename(file_path),
        creation_date=creation_date,
        last_modified_date=last_modified_date,
        extracted_content=parsed_info.get("text_content", ""),
        metadata=source_info_metadata,
        # Initialize other SourceInfo fields not directly from parser if needed
        snippet="", 
        access_time=time.time(), 
        domain="local", # Or consider leaving blank for local files
        reliability_score=0.0, # Default for local files, can be adjusted
        visualizable_data=[] 
    )

    # Convert SourceInfo dataclass instance to dictionary
    source_info_dict = dataclasses.asdict(source_info_obj)
    
    kb_data.append(source_info_dict)
    save_local_kb(kb_data)
    console.print(f"[green]Successfully added '{source_info_obj.title}' to local knowledge base with ID: {kb_id}[/green]")

@local.command("list")
def list_command():
    """List documents in the local knowledge base."""
    kb_data = load_local_kb()

    if not kb_data:
        console.print("[yellow]Local knowledge base is empty.[/yellow]")
        return

    table = Table(title="Local Knowledge Base Documents")
    table.add_column("KB ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Source Type", style="green")
    table.add_column("Original Filename", style="blue")
    table.add_column("File Path", style="dim")


    for item in kb_data:
        # metadata.get('kb_id') is safer as 'metadata' itself might be missing if data is malformed
        metadata = item.get("metadata", {})
        kb_id = metadata.get("kb_id", "N/A") 
        
        table.add_row(
            kb_id,
            item.get("title", "N/A"),
            item.get("source_type", "N/A"),
            item.get("original_filename", "N/A"),
            item.get("file_path", "N/A")
        )
    
    console.print(table)

@local.command("remove")
@click.argument("kb_identifier", type=str)
def remove(kb_identifier: str):
    """Remove a document from the local knowledge base by its KB_ID."""
    kb_data = load_local_kb()
    
    item_to_remove = None
    item_index = -1

    for i, item in enumerate(kb_data):
        metadata = item.get("metadata", {})
        if metadata.get("kb_id") == kb_identifier:
            item_to_remove = item
            item_index = i
            break
            
    if item_to_remove is None:
        console.print(f"[red]Error: No document found with KB_ID '{kb_identifier}'.[/red]")
        return
        
    # Confirm removal
    title_to_remove = item_to_remove.get('title', kb_identifier)
    if not click.confirm(f"Are you sure you want to remove '{title_to_remove}' (ID: {kb_identifier}) from the local knowledge base?"):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    kb_data.pop(item_index)
    save_local_kb(kb_data)
    console.print(f"[green]Successfully removed '{title_to_remove}' (ID: {kb_identifier}) from the local knowledge base.[/green]")

# --- End Local Knowledge Base CLI Commands ---
