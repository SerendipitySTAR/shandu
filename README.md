# Shandu 2.0: Advanced AI Research System with Robust Report Generation

Shandu is a cutting-edge AI research assistant that performs in-depth, multi-source research on any topic using advanced language models, intelligent web scraping, local document parsing, and iterative exploration to generate comprehensive, well-structured reports with proper citations, automated quality assessment, and conceptual chart generation.

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)

## 🔍 What is Shandu?

Shandu is an intelligent, LLM-powered research system that automates the comprehensive research process - from initial query clarification to in-depth content analysis and report generation. Built on LangGraph's state-based workflow, it recursively explores topics with sophisticated algorithms for source evaluation, content extraction, and knowledge synthesis. It can now also incorporate your local documents into its research process.

### Key Use Cases

- **Academic Research**: Generate literature reviews, background information, and complex topic analyses using various report styles.
- **Market Intelligence**: Analyze industry trends, competitor strategies, and market opportunities, tailoring report detail.
- **Content Creation**: Produce well-researched articles, blog posts, and reports with proper citations and quality scores.
- **Technology Exploration**: Track emerging technologies, innovations, and technical developments, including from your local files.
- **Policy Analysis**: Research regulations, compliance requirements, and policy implications with structured reports.
- **Competitive Analysis**: Compare products, services, and company strategies across industries, leveraging a local knowledge base.

## 🚀 What's New in Version 2.0

Shandu 2.0 introduces a major redesign of the report generation pipeline and adds powerful new features:

- **Modular Report Generation**: Process reports in self-contained sections, enhancing overall system reliability.
- **Robust Error Recovery**: Automatic retry mechanisms with intelligent fallbacks prevent the system from getting stuck.
- **Section-By-Section Processing**: Each section is processed independently, allowing for better error isolation.
- **Enhanced Progress Tracking**: Detailed CLI updates on the current activity, extracted themes, and selected sources.
- **Enhanced Citation Management**: More reliable citation handling ensures proper attribution throughout reports.
- **Intelligent Parallelization**: Key processes run in parallel where possible for improved performance.
- **Comprehensive Fallback Mechanisms**: If any step fails, the system gracefully degrades rather than halting.
- **Local Knowledge Base**: Integrate your own TXT, DOCX, and PDF documents into the research process.
- **Multi-Style Reports**: Generate reports in "standard", "academic", "business", or "literature_review" styles.
- **Variable Detail Levels**: Control report length and detail with "brief", "standard", "detailed", or custom word counts.
- **Conceptual Chart Generation**: Identifies data for visualization and generates Python Matplotlib code (simulation of chart embedding in Markdown).
- **Automated Quality Assessment**: Reports are automatically evaluated for quality, including citation validation and improvement suggestions.

## ⚙️ How Shandu Works

```mermaid
flowchart TB
    subgraph Input
        Q[User Query]
        P[Parameters: Depth, Breadth, Report Type, Detail Level, etc.]
        LKB[(Local KB Documents)]
    end

    subgraph Research[Research Phase]
        direction TB
        DR[Deep Research & Local KB Search]
        SQ[SERP Queries]
        PR[Process Results: Web & Local]
        NL[(Sources & Learnings)]
        ND[(Directions)]
    end

    subgraph Report[Report Generation & Evaluation]
        direction TB
        TG[Title Generation]
        TE[Theme Extraction]
        IR[Initial Report - Style & Detail Aware]
        ES[Section Enhancement - Style & Detail Aware]
        EX[Section Expansion - Style & Detail Aware]
        FR[Final Report with Charts (Simulated)]
        QE[Quality Evaluation & Suggestions]
        FinalOutput[Output: Report + Quality Score]
    end

    %% Main Flow
    Q & P & LKB --> DR
    DR --> SQ --> PR
    PR --> NL
    PR --> ND
    
    DP{depth > 0?}
    NL & ND --> DP

    RD["Next Direction:
    - Prior Goals
    - New Questions
    - Learnings"]

    %% Circular Flow
    DP -->|Yes| RD
    RD -->|New Context| DR

    %% To Report Generation
    DP -->|No| TG
    TG --> TE --> IR --> ES --> EX --> FR
    FR --> QE --> FinalOutput


    %% Styling
    classDef input fill:#7bed9f,stroke:#2ed573,color:black
    classDef process fill:#70a1ff,stroke:#1e90ff,color:black
    classDef recursive fill:#ffa502,stroke:#ff7f50,color:black
    classDef output fill:#ff4757,stroke:#ff6b81,color:white
    classDef storage fill:#a8e6cf,stroke:#3b7a57,color:black

    class Q,P,LKB input
    class DR,SQ,PR,TG,TE,IR,ES,EX,QE process
    class DP,RD recursive
    class FinalOutput output
    class NL,ND storage
```

## 🌟 Key Features

- **Intelligent State-based Workflow**: Leverages LangGraph for a structured, step-by-step research process.
- **Iterative Deep Exploration**: Recursively explores topics with dynamic depth and breadth parameters.
- **Hybrid Information Synthesis**: Analyzes data from search engines, web content, and a user-managed local knowledge base.
- **Enhanced Web Scraping**: Features dynamic JS rendering, content extraction, and ethical scraping practices.
- **Smart Source Evaluation**: Automatically assesses source credibility, relevance, and information value.
- **Content Analysis Pipeline**: Uses advanced NLP to extract key information, identify patterns, and synthesize findings.
- **Style-Aware & Detail-Controlled Report Generation**: Produces reports in various styles (academic, business, etc.) and detail levels.
- **Sectional Report Generation**: Creates detailed reports by processing individual sections for maximum reliability.
- **Conceptual Chart Generation**: Identifies visualizable data and generates Matplotlib code, with simulated embedding in reports.
- **Automated Report Quality Assessment**: Provides a quality score, dimensional feedback, citation validation, and improvement suggestions.
- **Full Citation Management**: Properly attributes all sources with formatted citations in multiple styles (APA, MLA, Chicago).
- **Local Knowledge Base**: Allows users to add and manage their own TXT, DOCX, and PDF documents for inclusion in research.

## 🏁 Quick Start

```bash
# Install from PyPI (once available)
# pip install shandu

# Install from source
git clone https://github.com/jolovicdev/shandu.git # Replace with actual repo if different
cd shandu
pip install -e .
playwright install # Installs browser binaries for web scraping

# Configure API settings (supports various LLM providers)
shandu configure

# Add documents to your local knowledge base (optional)
shandu local add /path/to/your/document.pdf
shandu local add ./research_paper.docx

# Run comprehensive research
shandu research "Impact of AI on renewable energy" --depth 2 --breadth 4 --output report.md --use-local-kb --report-type academic --detail-level detailed

# Quick AI-powered search with web scraping
shandu aisearch "Latest advancements in quantum cryptography" --detailed
```

## 📚 Detailed Usage

### Research Command

The main command for performing research.

```bash
shandu research "Your research query" [OPTIONS]
```

**Key Options:**

*   `--depth INT`: How deep to explore the topic (1-5, default: 2). Higher values mean more thorough research but take longer.
*   `--breadth INT`: How many parallel queries or aspects to explore at each depth level (2-10, default: 4).
*   `--output FILE_PATH`: Save the final report to the specified file (e.g., `report.md`). If omitted, prints to console.
*   `--verbose`: Show a detailed, real-time dashboard of the research progress. Without it, a simpler tree view is shown.
*   `--report-type TYPE`: Specify the style of the generated report.
    *   `standard`: A comprehensive, well-structured general-purpose report (default).
    *   `academic`: A formal report suitable for academic purposes, often using APA citations. Emphasizes critical analysis and evidence-based claims.
    *   `business`: A report focused on practicality, clarity, and decision support. Prioritizes key findings and actionable insights.
    *   `literature_review`: A survey of scholarly articles, books, and other sources relevant to a particular issue, area of research, or theory. Often uses MLA citations.
*   `--detail-level LEVEL`: Control the desired length and detail of report sections.
    *   `brief`: Sections will be concise, focusing on main points.
    *   `standard`: A balanced level of detail for each section (default).
    *   `detailed`: Sections will be significantly expanded with in-depth analysis and examples.
    *   `custom_XXXX` (e.g., `custom_1500`): Aims for approximately XXXX words per major section where applicable (enhancement/expansion phases).
*   `--use-local-kb`: A flag to enable searching within your personal local knowledge base in addition to web sources.
*   `--chart-theme THEME`: (Future Feature) Specify a theme for generated chart visualizations (e.g., "default", "ggplot", "seaborn-darkgrid"). Currently conceptual.
*   `--chart-colors COLORS`: (Future Feature) Provide a comma-separated list of preferred hex colors for charts (e.g., "'#FF5733,#33FF57'"). Currently conceptual.
*   `--include-chain-of-thought`: Include the agent's internal "thoughts" or reasoning steps in the final report output.
*   `--include-objective`: Include an "Objective" section at the beginning of the report, outlining the research goals.

**Example:**

```bash
shandu research "The role of gut microbiome in neurodegenerative diseases" \
    --depth 3 \
    --breadth 5 \
    --report-type academic \
    --detail-level detailed \
    --use-local-kb \
    --output microbiome_neuro_report.md \
    --verbose
```

### Local Knowledge Base Management

Shandu allows you to build and manage a local knowledge base of your own documents (TXT, DOCX, PDF). This KB can then be included in your research process.

The local KB is stored as a JSON file at `~/.shandu/local_kb.json`.

**Commands:**

*   **`shandu local add <file_path>`**
    *   Adds a document to your local knowledge base.
    *   Supported formats: `.txt`, `.docx`, `.pdf`.
    *   The document is parsed, and its text content and metadata are stored.
    *   Example: `shandu local add ./my_research_notes.docx`

*   **`shandu local list`**
    *   Lists all documents currently in your local knowledge base, showing KB ID, Title, Source Type, and Original Filename.
    *   Example: `shandu local list`

*   **`shandu local remove <kb_identifier>`**
    *   Removes a document from the local knowledge base using its unique KB ID (obtained from the `list` command).
    *   Example: `shandu local remove a1b2c3d4e5`

**Using the Local KB in Research:**
To include your local knowledge base in the research process, use the `--use-local-kb` flag with the `shandu research` command. Shandu will then perform keyword searches against the titles and extracted content of your local documents relevant to the research queries.

### Example Reports

You can find example reports in the `examples` directory of the repository, showcasing various features.

1.  **The Intersection of Quantum Computing, Synthetic Biology, and Climate Modeling**
    ```bash
    shandu research "The Intersection of Quantum Computing, Synthetic Biology, and Climate Modeling" --depth 3 --breadth 3 --output examples/quantum_bio_climate.md --report-type academic --detail-level detailed
    ```
2.  **Impact of Remote Work on Commercial Real Estate**
    ```bash
    shandu research "Impact of Remote Work on Commercial Real Estate" --depth 2 --breadth 4 --report-type business --use-local-kb --output examples/remote_work_real_estate.md
    ```

## 📚 Advanced Report Features

Shandu 2.0 includes several advanced features to customize and evaluate the generated reports:

### Multi-Style Reports
Controlled by the `--report-type` option:
*   **Academic**: Formal tone, structured arguments, emphasis on evidence and critical analysis. Typically uses APA citation style for bibliographies.
*   **Business**: Clear, concise, actionable insights. Often includes executive summaries and recommendations. Typically uses APA citation style.
*   **Literature Review**: A comprehensive survey of existing scholarly work on a topic, identifying themes, gaps, and relationships. Typically uses MLA citation style.
*   **Standard**: A general-purpose, well-structured, and comprehensive report. Uses APA citation style by default.

### Report Detail Levels
Controlled by the `--detail-level` option, this influences the length and depth of content generated, particularly during report enhancement and section expansion phases:
*   **brief**: Focuses on concise summaries and main points.
*   **standard**: Provides a balanced, standard level of detail.
*   **detailed**: Aims for significantly more in-depth analysis, examples, and explanations.
*   **custom_XXXX** (e.g., `custom_1500`): Instructs the LLM to aim for approximately XXXX words for sections being enhanced or expanded. This is a target and actual length may vary.

### Visualization Chart Generation (Conceptual)
Shandu can identify data within sources that is suitable for visualization.
*   **Data Identification**: During content analysis, potentially visualizable datasets are flagged.
*   **Python Matplotlib Code**: For these datasets, Shandu generates Python code using the Matplotlib library to create charts (e.g., bar charts, line graphs).
*   **Simulated Embedding**: The final Markdown report includes *references* to these charts as if they were image files (e.g., `charts/chart_filename.png`). Currently, Shandu does not execute this code to save actual image files.
*   **Using the Code**: Users can (in future versions or by accessing state logs if available) retrieve the generated Matplotlib code and run it in a Python environment to produce the actual chart images.
*   **Styling (Future)**: The `--chart-theme` and `--chart-colors` options are placeholders for future enhancements that will allow styling of the generated Matplotlib code.

### Automatic Report Quality Evaluation
At the end of each research task, Shandu performs an automated quality assessment of the final report. This evaluation is stored in the agent's state and can be accessed if the research results are saved or inspected programmatically.
The quality report includes:
*   **Overall Score**: A single score (0.0-10.0) representing the LLM's overall assessment.
*   **Dimensional Scores**: Scores (1-10) for:
    *   `Content Integrity`: Accuracy, completeness, depth.
    *   `Logical Consistency`: Coherence, flow, absence of contradictions.
    *   `Language Style`: Clarity, conciseness, grammar, appropriateness for the chosen `report_type`.
    *   `Citation Presence`: Whether inline citations are present where expected.
*   **Textual Feedback**: Brief strengths and weaknesses for each dimension.
*   **Summary**: Overall key strengths and areas for improvement.
*   **Citation Validation Details**: Granular output from `CitationRegistry.validate_citations()`, showing `used_citation_ids`, `registered_citation_ids`, `correctly_used_ids`, `out_of_range_ids_in_text`, `unregistered_ids_in_text`, and `unused_registered_ids`.
*   **Improvement Suggestions**: A structured list of actionable suggestions, often referencing specific issues from the assessment or citation validation (e.g., `[{"area": "Content Integrity", "suggestion": "Elaborate on topic X."}]`).

**Interpreting the Quality Report**: Users can review this detailed feedback to understand the generated report's strengths and weaknesses, identify areas for manual improvement, or guide further research iterations.

## 💻 Python API

```python
from shandu.agents import ResearchGraph
from langchain_openai import ChatOpenAI # Or your preferred LLM provider

# Initialize with custom LLM if desired
# Ensure your LLM provider is configured in ~/.shandu/config.ini or via environment variables
llm = ChatOpenAI(model="gpt-4-turbo") # Example

# Initialize the research graph
researcher = ResearchGraph(
    llm=llm,
    temperature=0.2 # Lower temperature for more factual/deterministic generation
)

# Perform deep research with new options
results_object = researcher.research_sync(
    query="Advancements in AI-driven drug discovery and its ethical implications",
    depth=2,
    breadth=3,
    report_template="academic", # "standard", "business", "literature_review"
    detail_level="detailed",   # "brief", "standard", "detailed", "custom_1200"
    use_local_kb=True,         # Set to True to include local documents
    # chart_theme="ggplot",    # Conceptual, for future use
    # chart_colors="#007ACC,#FF4500" # Conceptual, for future use
)

# Access the report content
final_report_markdown = results_object.summary # 'summary' field holds the final report

# Access quality evaluation (if research completed fully)
# The structure of final_state would be available if you directly invoke the graph:
# final_state = asyncio.run(researcher.graph.ainvoke(initial_agent_state))
# quality_report_data = final_state.get("quality_report")
# For now, quality report is part of internal state but not directly in ResearchResult.
# This would be an area for future enhancement to expose it more easily via API.

# Save or print the report
with open("ai_drug_discovery_report.md", "w", encoding="utf-8") as f:
    f.write(final_report_markdown)
print("Report saved to ai_drug_discovery_report.md")

# To see the full agent state including quality report after a run,
# you might need to modify ResearchGraph.research or research_sync
# to return the full final_state or parts of it.
```

## 🧩 Advanced Architecture

### Research Pipeline

Shandu's research pipeline consists of these key stages:

1.  **Query Clarification**: Interactive questions to understand research needs.
2.  **Research Planning**: Strategic planning for comprehensive topic coverage.
3.  **Iterative Exploration**:
    *   Smart query generation based on knowledge gaps (informed by reflection).
    *   Hybrid Search: Multi-engine web search and local knowledge base search.
    *   Relevance filtering of search results.
    *   Intelligent web scraping with content extraction.
    *   Source credibility assessment.
    *   Information analysis and synthesis from web and local sources.
    *   Reflection on findings to identify gaps.

### Report Generation Pipeline

Shandu 2.0 introduces a robust, modular report generation pipeline:

1.  **Data Preparation**: Registration of all sources and their metadata for proper citation.
2.  **Title Generation**: Creating a concise, professional title.
3.  **Theme Extraction**: Identifying key themes to organize the report structure.
4.  **Citation Formatting**: Properly formatting all citations for the bibliography.
5.  **Initial Report Generation**: Creating a comprehensive draft report, respecting `report_type` and `detail_level`.
6.  **Section Enhancement**: Individually processing each section to add detail and depth, guided by `report_type` and `detail_level`.
7.  **Key Section Expansion**: Identifying and expanding the most important sections, guided by `report_type` and `detail_level`.
8.  **Report Finalization**: Final processing, cleanup, and inclusion of simulated chart references.
9.  **Quality Evaluation**: Automated assessment of the final report, including citation validation and improvement suggestions.

Each step includes:
- Comprehensive error handling
- Automatic retries with exponential backoff
- Intelligent fallbacks when issues occur
- Progress tracking for transparency
- Validation to ensure quality output

## 🔌 Supported Search Engines & Sources

- **Web Search**: Google Search, DuckDuckGo, Wikipedia, ArXiv (academic papers).
- **Local Knowledge Base**: User-provided `.txt`, `.docx`, and `.pdf` documents.
- Custom search engines can be added by extending the `UnifiedSearcher`.

## 📊 Technical Capabilities

- **Dynamic JS Rendering**: Handles JavaScript-heavy websites via Playwright.
- **Content Extraction**: Identifies and extracts main content from web pages using Trafilatura.
- **Document Parsing**: Parses local TXT, DOCX (via `python-docx`), and PDF (via `pypdf`) files.
- **Parallel Processing**: Concurrent execution of searches and scraping.
- **Caching**: Efficient caching of search results and scraped content.
- **Rate Limiting**: Respectful access to web resources.
- **Robots.txt Compliance**: Ethical web scraping practices.
- **Flexible Output Formats**: Markdown, JSON (for internal state), plain text.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap: Local Vector Retrieval with `all-MiniLM-L6-v2`

This section outlines the planned approach to integrate efficient local vector retrieval using the `sentence-transformers/all-MiniLM-L6-v2` model. This will significantly enhance the local knowledge base search beyond the current keyword-based approach.

**1. Dependency Management:**
    *   Add `sentence-transformers` to `requirements.txt`.
    *   The application will be configured to load the `all-MiniLM-L6-v2` model from a user-specified local path, with `/media/sc/AI/self-llm/embed_model/sentence-transformers/all-MiniLM-L6-v2` as a documented example path.

**2. Embedding Generation during `shandu local add`:**
    *   Modify the `shandu local add` command in `shandu/cli.py`.
    *   After parsing the document, the `text_content` (or meaningful chunks for longer documents) will be embedded using the loaded `all-MiniLM-L6-v2` model.
    *   **Text Chunking:** For long documents, text may be split into smaller, overlapping chunks, with each chunk receiving an embedding linked to the parent document ID.

**3. Storage of Embeddings:**
    *   Embeddings will be stored. Initial thoughts lean towards:
        *   **Simplified Storage:** Directly within the `local_kb.json` file, where each document entry (or chunk) would have an `embedding` field (list of floats).
        *   **Future Enhancement:** Integration with a lightweight local vector database (e.g., FAISS, ChromaDB) for better scalability and performance.
    *   The initial implementation will focus on the simplified storage method.

**4. Query Embedding in `search_node`:**
    *   Modify `shandu/agents/nodes/search.py`.
    *   When local vector search is active, the input search `query` will be embedded using the same `all-MiniLM-L6-v2` model.

**5. Similarity Search Logic in `search_node`:**
    *   The embedded query vector will be compared against stored document/chunk embeddings using cosine similarity.
    *   Documents/chunks with similarity scores above a configurable threshold will be considered matches.
    *   A top N relevant local items will be selected, and their content will be used in the research process.

**6. CLI Options/Flags:**
    *   The existing `--use-local-kb` flag will continue to enable local KB searching.
    *   A new option, possibly `--local-search-mode <mode>` (e.g., `keyword`, `vector`), may be introduced to control the search strategy. Vector search might become the default if embeddings are available for local documents.

**7. Fallback and Hybrid Search:**
    *   The system may support falling back to keyword search if vector search yields insufficient results, or allow for a hybrid approach.
