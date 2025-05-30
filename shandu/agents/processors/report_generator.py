"""Report generation utilities with structured output."""
import os
from typing import List, Dict, Optional, Any, Union
import re
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from shandu.prompts import get_system_prompt # Added import
from ..utils.citation_registry import CitationRegistry

# Structured output models
class ReportTitle(BaseModel):
    """Structured output for report title generation."""
    title: str = Field(description="A concise, professional title for the research report")
    
class ThemeExtraction(BaseModel):
    """Structured output for theme extraction."""
    themes: List[str] = Field(description="List of key themes identified in the research")
    descriptions: List[str] = Field(description="Brief descriptions of each theme")
    
class InitialReport(BaseModel):
    """Structured output for initial report generation."""
    executive_summary: str = Field(description="Executive summary of the research findings")
    introduction: str = Field(description="Introduction to the research topic")
    sections: List[Dict[str, str]] = Field(description="List of report sections with titles and content")
    conclusion: str = Field(description="Conclusion summarizing the key findings")
    
class EnhancedReport(BaseModel):
    """Structured output for enhanced report generation."""
    enhanced_sections: List[Dict[str, str]] = Field(description="Enhanced sections with additional details")
    
class ExpandedSection(BaseModel):
    """Structured output for section expansion."""
    section_title: str = Field(description="Title of the section being expanded")
    expanded_content: str = Field(description="Expanded content for the section")

async def generate_title(llm: ChatOpenAI, query: str) -> str:
    """Generate a professional title for the report using structured output."""
    # Use structured output for title generation
    structured_llm = llm.with_structured_output(ReportTitle, method="function_calling")
    
    # Use a direct system prompt without template variables
    system_prompt = """You are creating a professional, concise title for a research report.
    
    CRITICAL REQUIREMENTS - YOUR TITLE MUST:
    1. Be EXTREMELY CONCISE (8 words maximum)
    2. Be DESCRIPTIVE of the main topic
    3. Be PROFESSIONAL in tone
    4. NEVER start with words like "Evaluating", "Analyzing", "Assessment", "Study", "Investigation", etc.
    5. NEVER contain generic phrases like "A Comprehensive Overview", "An In-depth Look", etc.
    6. NEVER use the word "report", "research", "analysis", or similar meta-terms
    7. NEVER include prefixes like "Topic:", "Subject:", etc.
    8. NEVER be in question format
    9. NEVER be in sentence format - should be a noun phrase
    
    EXAMPLES OF GOOD TITLES:
    "NVIDIA RTX 5000 Series Gaming Performance"
    "Quantum Computing Applications in Cryptography"
    "Clean Energy Transition: Global Market Trends"
    """

    user_message = f"Create a professional, concise title (8 words max) for research about: {query}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_message)
    ])
    
    try:
        # Direct non-structured approach to avoid errors
        direct_prompt = f"""Create a professional, concise title (8 words max) for this research topic: {query}
        
        The title should be:
        - Extremely concise (8 words max)
        - Descriptive of the main topic
        - Professional in tone
        - NOT use words like "Evaluating", "Analyzing", "Assessment", "Report", etc.
        - NOT use generic phrases like "A Comprehensive Overview"
        - Be a noun phrase, not a question or sentence
        
        Return ONLY the title, nothing else. No quotation marks, no explanations.
        """
        
        # Use a direct, simplified approach
        simple_llm = llm.with_config({"temperature": 0.2})
        response = await simple_llm.ainvoke(direct_prompt)

        clean_title = response.content.replace("Title:", "").replace("\"", "").strip()
        return clean_title
    except Exception as e:
        print(f"Error in structured title generation: {str(e)}. Using simpler approach.")

        from ...utils.logger import log_error
        log_error("Error in structured title generation", e, 
                 context=f"Query: {query}, Function: generate_title")
        # Fallback to non-structured approach
        simple_prompt = ChatPromptTemplate.from_messages([
            ("system", "Create a professional, concise title (8 words max) for a research report."),
            ("user", f"Topic: {query}")
        ])
        
        simple_llm = llm.with_config({"temperature": 0.2})
        simple_chain = simple_prompt | simple_llm
        title = await simple_chain.ainvoke({})

        clean_title = title.content.replace("Title: ", "").replace("\"", "").strip()
        
        return clean_title

async def extract_themes(llm: ChatOpenAI, findings: str) -> str:
    """Extract key themes from research findings using structured output."""
    # Use structured output for theme extraction
    structured_llm = llm.with_structured_output(ThemeExtraction, method="function_calling")
    
    # Use a direct system prompt without template variables
    system_prompt = """You are analyzing research findings to identify key themes for a report structure.
    Extract 4-7 major themes (dont mention word Theme)from the content that would make logical report sections.
    These themes should emerge naturally from the content rather than following a predetermined structure.
    For each theme, provide a brief description of what content would be included."""

    user_message = f"Analyze these research findings and extract 4-7 key themes that should be used as main sections in a report:\n\n{findings}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_message)
    ])
    
    try:
        # Direct non-structured approach to avoid errors
        direct_prompt = f"""Extract 4-7 key themes from these research findings that would make logical report sections.
        
        Research findings:
        {findings[:3000]}
        
        Format your response as:
        
        ## Theme 1 (dont mention word Theme)
        Description of theme 1
        
        ## Theme 2 (dont mention word Theme)
        Description of theme 2
        
        And so on. Each theme should have a clear, concise title and a brief description.
        
        Do not include any other text or explanations outside of the themes and descriptions.
        """
        
        # Use direct approach
        simple_llm = llm.with_config({"temperature": 0.3})
        response = await simple_llm.ainvoke(direct_prompt)

        return response.content
    except Exception as e:
        print(f"Error in structured theme extraction: {str(e)}. Using simpler approach.")

        from ...utils.logger import log_error
        log_error("Error in structured theme extraction", e, 
                 context=f"Findings length: {len(findings)}, Function: extract_themes")
        
        # Fallback to non-structured approach
        simple_prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract 4-7 key themes from research findings that would make logical report sections.
            Format your response as:
            
            ## Theme 1 (dont mention word Theme)
            Description of theme 1
            
            ## Topic 2 (dont mention word Topic)
            Description of topic 2
            
            And so on."""),
            ("user", f"Extract topics from these findings:\n\n{findings[:10000]}")
        ])
        
        simple_llm = llm.with_config({"temperature": 0.3})
        simple_chain = simple_prompt | simple_llm
        themes = await simple_chain.ainvoke({})
        
        return themes.content

async def format_citations(
    llm: ChatOpenAI, 
    selected_sources: List[str], 
    sources: List[Dict[str, Any]], 
    citation_registry: Optional[CitationRegistry] = None
) -> str:
    """
    Format citations for selected sources.
    
    Args:
        llm: The language model to use
        selected_sources: List of source URLs to format as citations
        sources: List of source metadata dictionaries
        citation_registry: Optional CitationRegistry instance to use for citation tracking
        
    Returns:
        String of formatted citations
    """
    if not selected_sources:
        return ""
    
    # If we have a citation registry, use it to get all properly cited sources
    if citation_registry:

        all_citations = citation_registry.get_all_citations()
        
        # Only format citations that were actually used
        # Sort by citation ID to ensure consistent ordering
        citations = []
        for cid in sorted(all_citations.keys()):
            citation_info = all_citations[cid]
            url = citation_info.get("url")

            source_meta = next((s for s in sources if s.get("url") == url), {})

            domain = url.split("//")[1].split("/")[0] if "//" in url else "Unknown Source"
            title = source_meta.get("title", citation_info.get("title", "Untitled"))
            date = source_meta.get("date", citation_info.get("date", "n.d."))
            
            citation = f"[{cid}] *{domain}*, \"{title}\", {url}"
            citations.append(citation)
        
        if citations:
            return "\n".join(citations)

    sources_text = ""
    for i, url in enumerate(selected_sources, 1):

        source_meta = {}
        for source in sources:
            if source.get("url") == url:
                source_meta = source
                break

        sources_text += f"Source {i}:\nURL: {url}\n"
        if source_meta.get("title"):
            sources_text += f"Title: {source_meta.get('title')}\n"
        if source_meta.get("source"):
            sources_text += f"Publication: {source_meta.get('source')}\n"
        if source_meta.get("date"):
            sources_text += f"Date: {source_meta.get('date')}\n"
        sources_text += "\n"
    
    # Use an enhanced citation formatter prompt with direct system message
    system_prompt = """Format the following source information into properly numbered citations for a research report.
    
    FORMATTING REQUIREMENTS:
    1. Each citation MUST start with [n] where n is the citation number
    2. Each citation MUST include the following elements (when available):
       - Website domain name in italics
       - Title of the article/page in quotes
       - Publication date
       - Complete URL
    
    EXAMPLE PROPER CITATIONS:
    [1] *techreview.com*, "Advances in GPU Architecture", 2024-01-15, https://techreview.com/articles/gpu-advances
    [2] *arxiv.org*, "Neural Network Performance Optimization", 2023-11-30, https://arxiv.org/papers/nn-optimization
    
    MISSING INFORMATION:
    - If website domain is missing, extract it from the URL
    - If title is missing, use "Untitled"
    - If date is missing, use "n.d." (no date)
    
    IMPORTANT: DO NOT generate citations from your training data. ONLY use the provided source information.
    DO NOT create academic-style citations like "Journal of Medicine (2020)". 
    ONLY create web citations with the exact format shown in the examples.
    
    FORMAT ALL CITATIONS IN A CONSISTENT STYLE.
    Number citations sequentially starting from [1].
    Place each citation on a new line.
    """

    user_message = f"Format these sources into proper citations:\n\n{sources_text}"
    
    citation_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_message)
    ])
    
    formatter_chain = citation_prompt | llm
    formatted_citations = (await formatter_chain.ainvoke({})).content
    
    # Verify citations have proper format [n] at the beginning
    if not re.search(r'\[\d+\]', formatted_citations):

        citations = []
        for i, url in enumerate(selected_sources, 1):
            source_meta = next((s for s in sources if s.get("url") == url), {})
            title = source_meta.get("title", "Untitled")
            domain = url.split("//")[1].split("/")[0] if "//" in url else "Unknown Source"
            date = source_meta.get("date", "n.d.")
            
            citation = f"[{i}] *{domain}*, \"{title}\", {date}, {url}"
            citations.append(citation)
        
        formatted_citations = "\n".join(citations)
    
    return formatted_citations

async def generate_initial_report(
    llm: ChatOpenAI,
    query: str,
    findings: str,
    extracted_themes: str,
    report_title: str,
    selected_sources: List[str],
    formatted_citations: str,
    current_date: str,
    detail_level: str,
    include_objective: bool,
    citation_registry: Optional[CitationRegistry] = None,
    report_style_instructions: str = "", # Added
    language: str = "en" # Added
) -> str:
    """Generate the initial report draft using structured output."""
    
    system_prompt_template = get_system_prompt("report_generation", language)
    
    # Variables to be injected into the system prompt template
    # Note: report_style_instructions is already localized by the caller
    # objective_instruction needs to be determined based on include_objective
    objective_instruction_text = ""
    if not include_objective:
        objective_instruction_text = "\n\nIMPORTANT: DO NOT include an \"Objective\" section at the beginning of the report. Let your content and analysis naturally determine the structure."

    # Prepare available sources text
    available_sources_text = ""
    if citation_registry:
        available_sources = []
        for cid in sorted(citation_registry.citations.keys()):
            citation_info = citation_registry.citations[cid]
            url = citation_info.get("url", "")
            title = citation_info.get("title", "") # Assuming title is stored
            available_sources.append(f"[{cid}] - {title} ({url})")
        if available_sources:
            available_sources_text = "\n\nAVAILABLE SOURCES FOR CITATION:\n" + "\n".join(available_sources)

    # Populate the system prompt using .format() for clarity with potentially complex fetched templates
    # The main template placeholders are {{current_date}}, {{report_style_instructions}}, {{objective_instruction}}
    # The system_prompt_template fetched from get_system_prompt should already contain these.
    # We also need to ensure detail_level is part of the system prompt if it's used there.
    # The original f-string was:
    # system_prompt = f"""You are generating a comprehensive research report...
    # - The level of detail should be {detail_level.upper()}.
    # - As of {current_date}, incorporate the most up-to-date information available.
    # - Create a dynamic structure based on the content themes rather than a rigid template.{objective_instruction}"""
    # The fetched template should ideally contain placeholders for these.
    # Let's assume the fetched `report_generation` prompt template has placeholders for:
    # {{current_date}}, {{report_style_instructions}}, {{objective_instruction}}, {{detail_level_placeholder}}

    # For now, I'll manually insert detail_level into the user message or assume it's part of report_style_instructions
    # or that the main system prompt template was designed to work without it explicitly.
    # The current `SYSTEM_PROMPTS["report_generation"]` does not have a placeholder for detail_level.
    # It's usually part of report_style_instructions or a general guideline.
    
    # The user message will carry the main content specifics
    user_message = f"""Create an extensive, in-depth research report on this topic.

Title: {report_title}
Analyzed Findings: {findings[:5000]} 
Number of sources: {len(selected_sources)}
Key themes identified in the research: 
{extracted_themes}
{available_sources_text} 

Organize your report around these key themes that naturally emerged from the research.
Create a dynamic, organic structure that best presents the findings, rather than forcing content into predetermined sections.
Ensure comprehensive coverage while maintaining a logical flow between topics.
The level of detail should be {detail_level.upper()}.

Your report must be extensive, detailed, and grounded in the research. Include all relevant data, examples, and insights found in the research.
Use proper citations to the sources throughout, referring only to the available sources listed above.

IMPORTANT: Begin your report with the exact title provided: "{report_title}" - do not modify or rephrase it."""

    # Create the prompt using the localized system template
    # The system prompt itself will be formatted by LangChain using these values.
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_template), # Localized base template
        ("user", user_message)
    ])
    
    # Context for LangChain's .ainvoke method if system prompt has {{placeholders}}
    prompt_context = {
        "current_date": current_date,
        "report_style_instructions": report_style_instructions, # Already localized
        "objective_instruction": objective_instruction_text,
        # Add other placeholders if the fetched system_prompt_template uses them
    }

    try:
        # Fallback direct_prompt also needs localization.
        # For simplicity, we might use a generic instruction here or a simplified localized prompt.
        # Let's assume the main path with ChatPromptTemplate works.
        # The original direct_prompt was an f-string. If we want to localize this,
        # it also needs to be fetched. For now, let's focus on the main path.
        # If direct_prompt is still needed, its template should be fetched via get_system_prompt.
        # Simplified direct_prompt for fallback:
        direct_prompt_template_key = "direct_initial_report_generation" # Needs to be in prompts.py
        direct_prompt_base_template = get_system_prompt(direct_prompt_template_key, language)
        if not direct_prompt_base_template: # Fallback if key not found
            direct_prompt_base_template = """Create an extremely comprehensive, detailed research report.
Title: {report_title}
Based on findings: {findings_preview}
Themes: {themes}
Sources available: {sources_info}
Detail level: {detail_level}. Current date: {current_date}.
Follow Markdown format. Include title, intro, sections by theme, conclusion, and references with correct citations [n]."""

        direct_prompt_content = direct_prompt_base_template.format(
            report_title=report_title,
            findings_preview=findings[:2000], # Preview to keep prompt manageable
            themes=extracted_themes,
            sources_info=available_sources_text,
            detail_level=detail_level.upper(),
            current_date=current_date,
            report_style_instructions=report_style_instructions # Pass this too
        )
        
        report_llm = llm.with_config({"max_tokens": 32768, "temperature": 0.6})
        # Invoke with the structured prompt first
        # response = await (prompt | report_llm).ainvoke(prompt_context) # This would be the ideal structured way
        
        # The original code uses a direct invoke on a manually constructed "direct_prompt_content" for the main path.
        # This "direct_prompt_content" should be constructed from a localized template.
        # The `report_generation` system prompt is quite complex.
        # Let's use the fetched system_prompt_template for the main call if possible,
        # but the user message is very specific.
        # Re-constructing the main path to use the fetched system prompt with ChatPromptTemplate:

        final_system_prompt = system_prompt_template.format(
            current_date=current_date,
            report_style_instructions=report_style_instructions,
            objective_instruction=objective_instruction_text,
            # detail_level is in user_message for now
        )

        final_prompt_messages = [
            ("system", final_system_prompt),
            ("user", user_message)
        ]
        
        response = await report_llm.ainvoke(final_prompt_messages)
        return response.content
        
    except Exception as e:
        print(f"Error in structured report generation: {str(e)}. Using simpler approach.")
        from ...utils.logger import log_error
        log_error("Error in structured report generation", e, 
                 context={"query": query, "report_title": report_title, "language": language, "function": "generate_initial_report"})
        
        # Fallback to simpler report generation
        simple_system_template = get_system_prompt("simple_report_fallback", language) # New key needed
        if not simple_system_template:
            simple_system_template = "Generate a research report based on findings. Date: {current_date}."
        
        simple_system_message = simple_system_template.format(current_date=current_date)
        
        simple_user_message = f"Title: {report_title}\n\nFindings (preview): {findings[:5000]}\n{available_sources_text}"
        
        simple_prompt = ChatPromptTemplate.from_messages([
            ("system", simple_system_message),
            ("user", simple_user_message)
        ])
        
        simple_llm = llm.with_config({"max_tokens": 16000, "temperature": 0.6})
        response = await (simple_prompt | simple_llm).ainvoke({})
        return response.content

async def enhance_report(
    llm: ChatOpenAI, 
    initial_report: str, 
    current_date: str, 
    # formatted_citations: str, # Not directly used in prompt construction here
    # selected_sources: List,   # Not directly used
    # sources: List[Dict],      # Not directly used
    citation_registry: Optional[CitationRegistry] = None,
    report_style_instructions: str = "", 
    language: str = "en",
    length_instruction: str = "" # Added
) -> str:
    """Enhance the report with additional detail while preserving structure and providing context."""

    if not initial_report or len(initial_report.strip()) < 500:
        return initial_report

    title_match = re.match(r'# ([^\n]+)', initial_report)
    report_title = title_match.group(1) if title_match else "Research Report" 

    # Store sections as list of dicts to easily access header and content
    raw_sections = re.compile(r'(#+\s+[^\n]+)((?:\n\n[^#]+?)*)(?=\n#+\s+|\Z)', re.DOTALL).findall(initial_report)
    sections_data = [{'header': header, 'content': content.strip()} for header, content in raw_sections if header and content.strip()]

    if not sections_data:
        return initial_report

    # Determine report_summary_context
    report_summary_context = "Summary not available."
    if sections_data:
        first_section_title = sections_data[0]['header'].lower().replace('#', '').strip()
        if "introduction" in first_section_title or "executive summary" in first_section_title:
            report_summary_context = sections_data[0]['content'][:500] + "..." if len(sections_data[0]['content']) > 500 else sections_data[0]['content']
        else: # Fallback to first few paras of the report if no clear intro/summary
            intro_text_match = re.search(r'#\s*[^\n]+\n+([^#]+)', initial_report, re.DOTALL)
            if intro_text_match:
                report_summary_context = intro_text_match.group(1).strip()[:500] + "..." if len(intro_text_match.group(1).strip()) > 500 else intro_text_match.group(1).strip()


    enhanced_report_parts = [f"# {report_title}\n\n"]
    
    base_section_prompt_template = get_system_prompt("enhance_section_detail_template", language)
    if not base_section_prompt_template: 
        base_section_prompt_template = """Enhance this section of a research report with additional depth and detail:

{section_header_content}{available_sources_text}

Your task is to:
1. Add more detailed explanations to key concepts
2. Expand on examples and case studies
3. Enhance the analysis and interpretation of findings
4. Improve the flow within this section
5. Add relevant statistics, data points, or evidence
6. Ensure proper citation [n] format throughout
7. Maintain scientific accuracy and up-to-date information (current as of {current_date})

CITATION REQUIREMENTS:
- ONLY use the citation IDs provided in the AVAILABLE SOURCES list above
- Format citations as [n] where n is the exact ID of the source
- Place citations at the end of the relevant sentences or paragraphs
- Do not make up your own citation numbers
- Do not cite sources that aren't in the available sources list

IMPORTANT:
- DO NOT change the section heading
- DO NOT add information not supported by the research
- DO NOT use academic-style citations like "Journal of Medicine (2020)"
- DO NOT include PDF/Text/ImageB/ImageC/ImageI tags or any other markup
- Return ONLY the enhanced section with the original heading

Return the enhanced section with the exact same heading but with expanded content.
""" # This is the fallback English version of the template from prompts.py

    for i, current_section in enumerate(sections_data):
        section_header = current_section['header']
        section_content = current_section['content']

        if "references" in section_header.lower(): 
            enhanced_report_parts.append(f"{section_header}\n\n{section_content}\n\n")
            continue

        preceding_section_context = "This is the first main section."
        if i > 0:
            prev_content = sections_data[i-1]['content']
            preceding_section_context = (prev_content[:150] + "..." + prev_content[-150:]) if len(prev_content) > 300 else prev_content
        
        succeeding_section_context = "This is the last main section."
        if i < len(sections_data) - 1:
            next_content = sections_data[i+1]['content']
            succeeding_section_context = (next_content[:150] + "..." + next_content[-150:]) if len(next_content) > 300 else next_content
            
        available_sources_text = ""
        if citation_registry:
            sources_list = [f"[{cid}] - {info.get('title', 'Untitled')} ({info.get('url', '')})" 
                            for cid, info in sorted(citation_registry.citations.items())]
            if sources_list:
                available_sources_text = "\n\nAVAILABLE SOURCES FOR CITATION:\n" + "\n".join(sources_list)
        
        # Core instructions for the current section, formatted from the fetched template
        formatted_core_instructions = base_section_prompt_template.format(
            section_header_content=f"{section_header}\n\n{section_content}", # Note: section_header_content is one var now
            available_sources_text=available_sources_text,
            current_date=current_date
            # Other placeholders specific to enhance_section_detail_template if any
        )

        # Construct the full prompt with context
        section_prompt_for_llm = f"""{report_style_instructions}
{length_instruction}

You are enhancing a specific section of a larger research report. Maintain consistency with the overall report structure and tone.

Report Title: {report_title}
Overall Report Summary:
{report_summary_context}

Preceding Section Content (Context):
{preceding_section_context}

Succeeding Section Content (Context):
{succeeding_section_context}

---
BEGIN SECTION TO ENHANCE (Instructions from template apply to this part):
{formatted_core_instructions}
---
"""
        
        try:
            enhance_llm = llm.with_config({"max_tokens": 4096, "temperature": 0.2})
            response = await enhance_llm.ainvoke(section_prompt_for_llm)
            section_text = response.content
            # Basic cleanup: remove potential markup tags if LLM adds them
            section_text = re.sub(r'\[\/?(?:PDF|Text|ImageB|ImageC|ImageI)(?:\/?|\])(?:[^\]]*\])?', '', section_text)
            section_text = re.sub(r'\[\/[^\]]*\]', '', section_text)


            if not section_text.strip().startswith(section_header.strip()):
                section_text = f"{section_header}\n\n{section_text.strip()}" # Ensure header and strip extra newlines
            enhanced_report_parts.append(f"{section_text.strip()}\n\n")
        except Exception as e:
            print(f"Error enhancing section '{section_header.strip()}': {str(e)}")
            enhanced_report_parts.append(f"{section_header}\n\n{section_content}\n\n") # Use original on error
    
    return "".join(enhanced_report_parts).strip()

async def expand_key_sections(
    llm: ChatOpenAI, 
    report: str, 
    # identified_themes: str, # Not directly used in prompt construction here
    current_date: str,
    citation_registry: Optional[CitationRegistry] = None,
    report_style_instructions: str = "", 
    language: str = "en",
    length_instruction: str = "", # Added
    expansion_requirements_text: str = "" # Added for dynamically built requirements
) -> str:
    """Expand key sections of the report while preserving structure and avoiding markup errors."""
    if not report or len(report.strip()) < 1000:
        return report

    report_title_match = re.match(r'# ([^\n]+)', report)
    report_title = report_title_match.group(1) if report_title_match else "Research Report"

    # Store sections as list of dicts to easily access header and content
    raw_sections = re.compile(r'(#+\s+[^\n]+)((?:\n\n[^#]+?)*)(?=\n#+\s+|\Z)', re.DOTALL).findall(report)
    sections_data = [{'header': header, 'content': content.strip()} for header, content in raw_sections if header and content.strip()]
    
    if not sections_data: return report
    
    # Determine report_summary_context (similar to enhance_report)
    report_summary_context = "Summary not available."
    if sections_data:
        first_section_title_lower = sections_data[0]['header'].lower().replace('#', '').strip()
        if "introduction" in first_section_title_lower or "executive summary" in first_section_title_lower:
            report_summary_context = sections_data[0]['content'][:500] + "..." if len(sections_data[0]['content']) > 500 else sections_data[0]['content']
        else:
            intro_text_match = re.search(r'#\s*[^\n]+\n+([^#]+)', report, re.DOTALL)
            if intro_text_match:
                report_summary_context = intro_text_match.group(1).strip()[:500] + "..." if len(intro_text_match.group(1).strip()) > 500 else intro_text_match.group(1).strip()

    important_sections_to_process = []
    original_indices = [] # To replace sections correctly in the original list of parts

    # Identify ## sections to expand, excluding common ones
    for i, section_data_item in enumerate(sections_data):
        header = section_data_item['header']
        # Only consider ## level sections for expansion
        if header.startswith("## ") and header.lower().replace('#', '').strip() not in \
           ["executive summary", "introduction", "conclusion", "references"]:
            important_sections_to_process.append(section_data_item)
            original_indices.append(i)
    
    important_sections_to_process = important_sections_to_process[:3] # Limit to 3
    original_indices = original_indices[:3]

    if not important_sections_to_process: return report
    
    # Work on a list of all report parts (title, sections)
    all_report_parts = [f"# {report_title}\n\n"] + [f"{sd['header']}\n\n{sd['content']}\n\n" for sd in sections_data]

    section_prompt_template_key = "expand_section_detail_template"
    base_section_prompt_template = get_system_prompt(section_prompt_template_key, language)

    if not base_section_prompt_template: 
        base_section_prompt_template = """Expand this section of a research report with much greater depth and detail:

{section_header_content}{available_sources_text}

EXPANSION REQUIREMENTS:
{expansion_requirements} 
Ensure all information is accurate as of {current_date}.

CITATION REQUIREMENTS:
- ONLY use the citation IDs provided in the AVAILABLE SOURCES list above
- Format citations as [n] where n is the exact ID of the source
- Place citations at the end of the relevant sentences or paragraphs
- Do not make up your own citation numbers
- Do not cite sources that aren't in the available sources list
- Ensure each major claim or statistic has an appropriate citation

IMPORTANT:
- DO NOT change the section heading
- DO NOT add information not supported by the research
- DO NOT use academic-style citations like "Journal of Medicine (2020)"
- DO NOT include PDF/Text/ImageB/ImageC/ImageI tags or any other markup
- Return ONLY the expanded section with the original heading

Return the expanded section with the exact same heading but with expanded content.
""" # Fallback English version

    for idx, section_data_to_expand in enumerate(important_sections_to_process):
        original_report_part_index = original_indices[idx] + 1 # +1 because all_report_parts[0] is the title

        section_header = section_data_to_expand['header']
        section_content = section_data_to_expand['content']
        title = section_header.replace('#', '').strip() # For logging

        preceding_section_context = "This is the first main section after the introduction/summary."
        # Find true preceding content part index
        if original_report_part_index > 1: # If not the first content part after title
            prev_content_full = all_report_parts[original_report_part_index - 1]
            # Strip header from prev_content_full
            prev_content_text_match = re.search(r'#+\s*[^\n]+\n+([^#]+)', prev_content_full, re.DOTALL)
            prev_content_text = prev_content_text_match.group(1).strip() if prev_content_text_match else prev_content_full.strip()
            preceding_section_context = (prev_content_text[:150] + "..." + prev_content_text[-150:]) if len(prev_content_text) > 300 else prev_content_text
        
        succeeding_section_context = "This is the last main section before the conclusion/references."
        if original_report_part_index < len(all_report_parts) - 1:
            next_content_full = all_report_parts[original_report_part_index + 1]
            next_content_text_match = re.search(r'#+\s*[^\n]+\n+([^#]+)', next_content_full, re.DOTALL)
            next_content_text = next_content_text_match.group(1).strip() if next_content_text_match else next_content_full.strip()
            succeeding_section_context = (next_content_text[:150] + "..." + next_content_text[-150:]) if len(next_content_text) > 300 else next_content_text

        available_sources_text = ""
        if citation_registry:
            sources_list = [f"[{cid}] - {info.get('title', 'Untitled')} ({info.get('url', '')})"
                            for cid, info in sorted(citation_registry.citations.items())]
            if sources_list:
                available_sources_text = "\n\nAVAILABLE SOURCES FOR CITATION:\n" + "\n".join(sources_list)
        
        # Core instructions for the current section
        formatted_core_instructions = base_section_prompt_template.format(
            section_header_content=f"{section_header}\n\n{section_content}",
            available_sources_text=available_sources_text,
            current_date=current_date,
            expansion_requirements=expansion_requirements_text # Dynamically built by node
        )

        # Construct the full prompt with context
        section_prompt_for_llm = f"""{report_style_instructions}
{length_instruction}

You are expanding a specific section of a larger research report. Maintain consistency with the overall report structure and tone.

Report Title: {report_title}
Overall Report Summary:
{report_summary_context}

Preceding Section Content (Context):
{preceding_section_context}

Succeeding Section Content (Context):
{succeeding_section_context}

---
BEGIN SECTION TO EXPAND (Instructions from template apply to this part):
{formatted_core_instructions}
---
"""
        try:
            expand_llm = llm.with_config({"max_tokens": 6144, "temperature": 0.2})
            response = await expand_llm.ainvoke(section_prompt_for_llm)
            expanded_content_text = response.content 
            expanded_content_text = re.sub(r'\[\/?(?:PDF|Text|ImageB|ImageC|ImageI)(?:\/?|\])(?:[^\]]*\])?', '', expanded_content_text)
            expanded_content_text = re.sub(r'\[\/[^\]]*\]', '', expanded_content_text)


            if not expanded_content_text.strip().startswith(section_header.strip()):
                expanded_content_text = f"{section_header}\n\n{expanded_content_text.strip()}"
            
            all_report_parts[original_report_part_index] = f"{expanded_content_text.strip()}\n\n" # Update the part in the list
            
        except Exception as e:
            print(f"Error expanding section '{title}': {str(e)}")
            # If error, the original part remains in all_report_parts
    
    return "".join(all_report_parts).strip()
