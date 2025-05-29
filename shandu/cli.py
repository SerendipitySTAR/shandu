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
from .local_kb.kb import LocalKB # Added for KB management
from .agents.langgraph_agent import clarify_query, display_research_progress
from .agents.langgraph_agent import ResearchGraph, AgentState
from .search.search import UnifiedSearcher
from .search.ai_search import AISearcher
from .scraper import WebScraper
from .research.researcher import DeepResearcher
from .agents.utils.agent_utils import is_shutdown_requested, get_shutdown_level

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
        Layout(name="status", size=3),
        Layout(name="progress", size=3),
        Layout(name="findings")
    )
    layout["right"].split(
        Layout(name="queries", ratio=2, minimum_size=3),
        Layout(name="selected_sources_panel", ratio=3, minimum_size=3),
        Layout(name="themes_panel", ratio=3, minimum_size=3),
        Layout(name="sources_type_count_panel", ratio=2, minimum_size=3), # Renamed from "sources"
        Layout(name="chain_of_thought", ratio=2, minimum_size=3)
    )
    
    elapsed_time = time.time() - state["start_time"]
    minutes, seconds = divmod(int(elapsed_time), 60)
    header_content = f"[bold blue]Research Query:[/] {state['query']}\n"
    header_content += f"[bold blue]Status:[/] {state['status']} | "
    header_content += f"[bold blue]Time:[/] {minutes}m {seconds}s | "
    header_content += f"[bold blue]Depth:[/] {state['current_depth']}/{state['depth']}"
    layout["header"].update(Panel(header_content, title="Shandu Deep Research"))
    
    status_table = Table(show_header=False, box=None)
    status_table.add_column("Metric", style="blue")
    status_table.add_column("Value")
    status_table.add_row("Current Depth", f"{state['current_depth']}/{state['depth']}")
    status_table.add_row("Sources Found", str(len(state['sources'])))
    status_table.add_row("Subqueries Explored", str(len(state['subqueries'])))
    layout["status"].update(Panel(status_table, title="Research Progress"))
    
    progress_percent = min(100, int((state['current_depth'] / max(1, state['depth'])) * 100))
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
    layout["sources_type_count_panel"].update(Panel(sources_table, title="Source Types Count"))

    # Panel for Selected Key Sources
    selected_sources_content = "No sources selected yet..."
    if state.get("selected_sources"):
        selected_sources_list = state["selected_sources"]
        if selected_sources_list:
            # Display up to 5 selected sources, plus a count if more
            display_max = 5
            selected_sources_display = "\n".join(selected_sources_list[:display_max])
            if len(selected_sources_list) > display_max:
                selected_sources_display += f"\n...and {len(selected_sources_list) - display_max} more."
            selected_sources_content = selected_sources_display
        else:
            selected_sources_content = "Source selection complete, but no sources were chosen."
            
    layout["selected_sources_panel"].update(Panel(selected_sources_content, title="Selected Key Sources"))

    # Panel for Identified Themes
    themes_content = "No themes identified yet..."
    if state.get("identified_themes"):
        identified_themes_text = state["identified_themes"]
        if identified_themes_text and isinstance(identified_themes_text, str) and identified_themes_text.strip():
            # Use Markdown for themes as they might have formatting
            themes_content = Markdown(identified_themes_text)
        elif not identified_themes_text.strip(): # Check if it's an empty string after stripping
             themes_content = "Themes extraction attempted, but no themes were found."
    layout["themes_panel"].update(Panel(themes_content, title="Report Outline Themes"))
    
    cot_text = "\n".join(state["chain_of_thought"][-5:]) if state["chain_of_thought"] else "No thoughts recorded yet..."
    layout["chain_of_thought"].update(Panel(cot_text, title="Chain of Thought"))
    
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

# Helper function to get LocalKB instance
def get_kb_manager():
    """Initializes and returns a LocalKB instance based on global config."""
    kb_dir = config.get("local_kb", "kb_dir", "local_kb_data")
    # Ensure kb_dir is absolute if it's meant to be, or handle relative paths consistently.
    # LocalKB itself should ideally manage making the path absolute if needed.
    try:
        return LocalKB(kb_dir=kb_dir)
    except Exception as e:
        console.print(f"[red]Error initializing Local Knowledge Base: {sanitize_error(e)}[/]")
        console.print(f"[yellow]Please ensure dependencies like 'sentence-transformers' and 'faiss-cpu' are installed, and the embedding model path is correct.[/]")
        sys.exit(1)

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
@click.option("--include-chain-of_thought", "-c", is_flag=True, help="Include chain of thought in report") # Corrected option name
@click.option("--include-objective", "-i", is_flag=True, help="Include objective section in report")
@click.option("--chart-theme", default="default", type=str, help="Theme for generated charts (e.g., 'default', 'ggplot', 'seaborn-darkgrid').")
@click.option("--chart-colors", default=None, type=str, help="Comma-separated list of preferred colors for charts (e.g., '#FF5733,#33FF57').")
@click.option(
    "--report-type",
    default="standard",
    type=click.Choice(["standard", "academic", "business", "literature_review"], case_sensitive=False),
    help="Type of report to generate."
)
@click.option(
    "--report-detail",
    default="standard",
    type=str,
    help="Set the detail level for the report: 'brief', 'standard', 'detailed', or 'custom_WORDCOUNT' (e.g., 'custom_1500')."
)
@click.option("--local-files", "-lf", default=None, type=str, help="Comma-separated list of local file paths to include in the research context.")
def research(
    query: str, 
    depth: Optional[int], 
    breadth: Optional[int], 
    output: Optional[str], 
    verbose: bool,
    strategy: str,
    include_chain_of_thought: bool, # Corrected parameter name
    include_objective: bool,
    chart_theme: str,
    chart_colors: Optional[str],
    report_type: str,
    report_detail: str,
    local_files: Optional[str]
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

    session_kb_dir_override = None
    original_kb_dir_config = config.get("local_kb", "kb_dir")
    temp_session_kb_path = None

    if local_files:
        console.print("[bold yellow]Processing local files for this research session...[/]")
        files_to_add = [f.strip() for f in local_files.split(',')]
        valid_files = []
        for f_path in files_to_add:
            if os.path.exists(f_path) and os.path.isfile(f_path):
                valid_files.append(os.path.abspath(f_path))
            else:
                console.print(f"[red]Warning: Local file '{f_path}' not found or is not a file. Skipping.[/red]")
        
        if valid_files:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # Create a unique temporary directory for this session's KB
            # Default parent is the configured kb_dir, or 'local_kb_data' if not set
            base_kb_parent_dir = original_kb_dir_config or "local_kb_data" 
            os.makedirs(base_kb_parent_dir, exist_ok=True) # Ensure parent exists

            temp_session_kb_path = os.path.join(base_kb_parent_dir, f"session_kb_{timestamp}")
            os.makedirs(temp_session_kb_path, exist_ok=True)
            
            console.print(f"Initializing temporary Local KB for session at: {temp_session_kb_path}")
            try:
                session_kb = LocalKB(kb_dir=temp_session_kb_path)
                for f_path in valid_files:
                    console.print(f"Adding '{os.path.basename(f_path)}' to session Local KB...")
                    session_kb.add_document(f_path) # add_document handles parsing and indexing
                
                # Override the global config for KB directory for the duration of this research
                session_kb_dir_override = temp_session_kb_path
                config.set("local_kb", "kb_dir", session_kb_dir_override)
                config.set("local_kb", "enabled", True) # Ensure KB is enabled if local files are provided
                console.print(f"[green]Session Local KB created and configured with {len(valid_files)} files.[/green]")
            except Exception as e:
                console.print(f"[red]Error initializing or populating session Local KB: {sanitize_error(e)}[/red]")
                console.print("[yellow]Proceeding without session-specific local files.[/yellow]")
                if temp_session_kb_path and os.path.exists(temp_session_kb_path):
                    import shutil
                    shutil.rmtree(temp_session_kb_path) # Clean up partially created temp KB
                temp_session_kb_path = None # Reset path to prevent cleanup later if it failed
                # Restore original config if it was changed before error
                if session_kb_dir_override: config.set("local_kb", "kb_dir", original_kb_dir_config)


    console.print(Panel(
        f"[bold blue]Query:[/] {query}\n"
        f"[bold blue]Depth:[/] {depth}\n"
        f"[bold blue]Breadth:[/] {breadth}\n"
        f"[bold blue]Strategy:[/] {strategy}\n"
        f"[bold blue]Model:[/] {model}",
        title="Research Parameters",
        border_style="blue"
    ))
    
    try:
        refined_query = asyncio.run(clarify_query(query, llm))
    except KeyboardInterrupt:
        console.print("\n[yellow]Query clarification cancelled. Using original query.[/]")
        refined_query = query

    research_result = None
    try:
        if strategy == "langgraph":
            graph = ResearchGraph(llm=llm, searcher=searcher, scraper=scraper) # ResearchGraph will use the (potentially overridden) config for LocalKB

            with Live(console=console, auto_refresh=True, screen=False, transient=False) as live:
                console.print("[bold green]Starting research...[/]")
                # ... (rest of the Live display setup remains the same)
                last_state_hash = None
                def debounced_update_display(state):
                    nonlocal last_state_hash
                    status = state.get("status", "")
                    current_depth = state.get("current_depth", 0)
                    sources_count = len(state.get("sources", []))
                    subqueries_count = len(state.get("subqueries", []))
                    current_hash = f"{status}_{current_depth}_{sources_count}_{subqueries_count}"
                    if current_hash != last_state_hash:
                        last_state_hash = current_hash
                        if verbose:
                            dashboard = create_research_dashboard(state)
                            live.update(dashboard)
                        else:
                            tree = display_research_progress(state)
                            live.update(tree)
                
                research_result = graph.research_sync(
                    refined_query,
                    depth=depth,
                    breadth=breadth,
                    progress_callback=debounced_update_display,
                    include_objective=include_objective,
                    chart_theme=chart_theme,
                    chart_colors=chart_colors,
                    report_template=report_type,
                    detail_level=report_detail
                )
        else: # agent-based strategy (assuming it also uses the global config for any LocalKB interaction)
            from .agents.agent import ResearchAgent
            agent = ResearchAgent(llm=llm, searcher=searcher, scraper=scraper)
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                BarColumn(), TimeElapsedColumn(), console=console
            ) as progress:
                task = progress.add_task("[green]Researching...", total=depth)
                research_result = agent.research_sync(
                    refined_query, depth=depth, engines=config.get("search", "engines")
                )
                progress.update(task, completed=depth)
        
        # Display result
        console.print("\n[bold green]Research complete![/]")
        if research_result and output:
            research_result.save_to_file(output, include_chain_of_thought, include_objective)
            console.print(f"[green]Report saved to {output}[/]")
        elif research_result:
            console.print(Markdown(research_result.to_markdown(include_chain_of_thought, include_objective)))

    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user.[/]")
        sys.exit(0)
    except Exception as e:
        error_msg = sanitize_markup(str(e))
        console.print(f"\n[red]Error during research: {error_msg}[/]")
        sys.exit(1)
    finally:
        # Restore original KB directory config and clean up session KB if created
        if session_kb_dir_override:
            config.set("local_kb", "kb_dir", original_kb_dir_config)
            # Potentially restore original "enabled" state for local_kb if it was changed
            # For now, just restoring dir. If local_files were provided, we forced enabled=True.
            # A more robust restoration would store the original enabled state too.
            logger.info(f"Restored Local KB directory configuration to: {original_kb_dir_config}")
        
        if temp_session_kb_path and os.path.exists(temp_session_kb_path):
            try:
                import shutil
                shutil.rmtree(temp_session_kb_path)
                console.print(f"[dim]Cleaned up temporary session Local KB at: {temp_session_kb_path}[/dim]")
            except Exception as e:
                console.print(f"[red]Warning: Failed to clean up temporary session Local KB: {sanitize_error(e)}[/red]")


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

# --- Local Knowledge Base Management Commands ---
@click.group("kb", help="Manage the Local Knowledge Base.")
def kb():
    """Commands for managing the Local Knowledge Base."""
    pass

@kb.command("add", help="Add a document to the Local Knowledge Base.")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--source-type", default="local_file", help="Type of the source, e.g., 'local_file', 'personal_notes'.")
@click.option("--content-type", default=None, help="Content type, e.g., 'article', 'research_paper'. Guessed if not provided.")
@click.option("--metadata-json", default=None, help="JSON string for additional metadata, e.g., '{\"author\": \"name\"}'.")
def kb_add_document(file_path: str, source_type: str, content_type: Optional[str], metadata_json: Optional[str]):
    """Adds a document to the Local Knowledge Base."""
    kb_manager = get_kb_manager()
    metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON provided for metadata: {sanitize_error(e)}[/]")
            return

    console.print(f"Attempting to add document: {file_path}")
    source_info = kb_manager.add_document(
        file_path=file_path, # file_path is already absolute due to resolve_path=True
        source_type=source_type,
        content_type=content_type,
        metadata=metadata
    )

    if source_info:
        console.print(Panel(f"[green]Document '{source_info.title}' added successfully to the Local Knowledge Base.[/green]",
                            title="Success", border_style="green"))
        if not source_info.extracted_content:
             console.print(f"[yellow]Warning: No text content was extracted from '{source_info.title}'. "
                           f"The document was added, but it might not be searchable if it's an empty or non-text file.[/yellow]")
    else:
        console.print(Panel(f"[red]Failed to add document: {file_path}[/red]", title="Error", border_style="red"))

@kb.command("remove", help="Remove a document from the Local Knowledge Base.")
@click.argument("file_path", type=click.Path(resolve_path=True)) # exists=True not required for removal
def kb_remove_document(file_path: str):
    """Removes a document from the Local Knowledge Base."""
    kb_manager = get_kb_manager()
    abs_file_path = os.path.abspath(file_path) # Ensure it's absolute for consistency with KB storage

    if not kb_manager.get_document(abs_file_path): # Check if doc exists before trying to remove
        console.print(f"[yellow]Document not found in Local Knowledge Base: {abs_file_path}[/yellow]")
        return

    console.print(f"Attempting to remove document: {abs_file_path}")
    if kb_manager.remove_document(abs_file_path):
        console.print(Panel(f"[green]Document '{abs_file_path}' removed successfully from the Local Knowledge Base.[/green]",
                            title="Success", border_style="green"))
    else:
        # This case might be redundant if get_document check is robust, but good for safety.
        console.print(Panel(f"[red]Failed to remove document: {abs_file_path}. It might not exist or an error occurred.[/red]", 
                            title="Error", border_style="red"))


@kb.command("list", help="List all documents in the Local Knowledge Base.")
def kb_list_documents():
    """Lists all documents in the Local Knowledge Base."""
    kb_manager = get_kb_manager()
    documents = kb_manager.list_documents()

    if not documents:
        console.print("[yellow]No documents found in the Local Knowledge Base.[/yellow]")
        return

    console.print(Panel(f"Found {len(documents)} documents in the Local Knowledge Base:", style="bold blue"))
    
    table = Table(title="Local KB Documents")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="green", min_width=20, overflow="fold")
    table.add_column("Path", style="blue", min_width=30, overflow="fold")
    table.add_column("Type", style="cyan", min_width=15, overflow="fold")
    table.add_column("Indexed Chunks", style="magenta", width=10) # Placeholder

    for idx, doc_info in enumerate(documents, 1):
        # Try to get chunk count if retriever and index metadata exist
        chunk_count_display = "N/A"
        if kb_manager.retriever and kb_manager.retriever.document_chunks and doc_info.file_path:
            # This is a simplified way; a more robust way would be to store chunk count per doc in SourceInfo or query retriever
            doc_abs_path = os.path.abspath(doc_info.file_path)
            count = sum(1 for chunk in kb_manager.retriever.document_chunks if chunk.get("source_file_path") == doc_abs_path)
            chunk_count_display = str(count) if count > 0 else "0"
            if kb_manager.retriever.index is None or kb_manager.retriever.index.ntotal == 0:
                 chunk_count_display = "No Index"


        table.add_row(
            str(idx),
            doc_info.title or "N/A",
            doc_info.file_path or "N/A", # Should always have file_path for local KB
            doc_info.content_type or "N/A",
            chunk_count_display
        )
    console.print(table)

@kb.command("reindex", help="Re-index all documents in the Local Knowledge Base.")
def kb_reindex_documents():
    """Rebuilds the search index for all documents in the Local Knowledge Base."""
    kb_manager = get_kb_manager()
    console.print("Starting re-indexing process...")
    
    if kb_manager.retriever is None or kb_manager.retriever.embedding_model is None:
        console.print("[red]Retriever or embedding model not available. Cannot re-index.[/red]")
        console.print("[yellow]Please ensure dependencies like 'sentence-transformers' and 'faiss-cpu' are installed, and the embedding model path is correct.[/yellow]")
        return

    docs = kb_manager.list_documents()
    if docs:
        try:
            kb_manager.retriever.build_index_from_documents(docs, reindex=True)
            console.print(Panel("[green]Successfully re-indexed all documents.[/green]", 
                                title="Success", border_style="green"))
        except Exception as e:
            console.print(f"[red]An error occurred during re-indexing: {sanitize_error(e)}[/red]")
    else:
        console.print("[yellow]No documents in the knowledge base to re-index.[/yellow]")

cli.add_command(kb)

if __name__ == "__main__":
    cli()
