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

# 字数控制和验证函数
def count_chinese_and_english_chars(text: str) -> int:
    """统计中文字符和英文字符的总数"""
    chinese_count = 0
    english_count = 0

    # 定义中文字符的Unicode范围
    chinese_unicode_range = range(0x4E00, 0x9FFF + 1)

    for char in text:
        # 统计中文字符
        if ord(char) in chinese_unicode_range:
            chinese_count += 1
        # 统计英文字符
        elif char.isalpha():
            english_count += 1

    return chinese_count + english_count

def get_word_count_requirements(detail_level: str) -> Dict[str, int]:
    """根据详细程度获取字数要求"""
    if detail_level == "brief":
        return {
            "total_min": 4000,
            "total_target": 4000,
            "total_max": 5000,
            "main_section_min": 800,
            "sub_section_min": 300,
            "paragraph_min": 120
        }
    elif detail_level == "detailed":
        return {
            "total_min": 15000,
            "total_target": 15000,
            "total_max": 18000,
            "main_section_min": 2500,
            "sub_section_min": 1000,
            "paragraph_min": 150
        }
    elif detail_level.startswith("custom_"):
        try:
            word_count = int(detail_level.split('_')[1])
            return {
                "total_min": word_count,  # 严格要求达到目标字数
                "total_target": word_count,
                "total_max": int(word_count * 1.2),
                "main_section_min": max(word_count // 4, 1500),  # 增加主章节最小字数
                "sub_section_min": max(word_count // 8, 600),    # 增加子章节最小字数
                "paragraph_min": max(word_count // 40, 150)      # 增加段落最小字数
            }
        except (ValueError, IndexError):
            pass

    # Default to standard - 大幅提高标准要求
    return {
        "total_min": 15000,  # 【增强】提高最低字数要求
        "total_target": 18000,  # 【增强】提高目标字数
        "total_max": 22000,  # 【增强】提高最大字数
        "main_section_min": 3000,  # 【增强】提高主章节最小字数
        "sub_section_min": 1200,  # 【增强】提高子章节最小字数
        "paragraph_min": 200  # 【增强】提高段落最小字数
    }

def analyze_report_structure(report_content: str) -> Dict[str, Any]:
    """分析报告结构和字数分布"""
    # 使用正确的字数统计方法
    total_chars = count_chinese_and_english_chars(report_content)

    # 提取章节
    sections = []
    section_pattern = re.compile(r'(##\s+[^\n]+)(.*?)(?=##\s+|\Z)', re.DOTALL)
    section_matches = section_pattern.findall(report_content)

    for header, content in section_matches:
        section_chars = count_chinese_and_english_chars(content.strip())

        # 提取子章节
        subsections = []
        subsection_pattern = re.compile(r'(###\s+[^\n]+)(.*?)(?=###\s+|##\s+|\Z)', re.DOTALL)
        subsection_matches = subsection_pattern.findall(content)

        for sub_header, sub_content in subsection_matches:
            subsection_chars = count_chinese_and_english_chars(sub_content.strip())

            # 统计段落数
            paragraphs = [p.strip() for p in sub_content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
            paragraph_count = len(paragraphs)
            avg_paragraph_length = sum(count_chinese_and_english_chars(p) for p in paragraphs) / max(paragraph_count, 1)

            subsections.append({
                "header": sub_header.strip(),
                "char_count": subsection_chars,
                "paragraph_count": paragraph_count,
                "avg_paragraph_length": avg_paragraph_length
            })

        sections.append({
            "header": header.strip(),
            "char_count": section_chars,
            "subsections": subsections
        })

    return {
        "total_chars": total_chars,
        "sections": sections,
        "section_count": len(sections)
    }

def validate_report_quality(report_content: str, detail_level: str) -> Dict[str, Any]:
    """验证报告质量是否达到要求"""
    requirements = get_word_count_requirements(detail_level)
    analysis = analyze_report_structure(report_content)

    issues = []
    warnings = []

    # 检查总字数（使用字符数）
    if analysis["total_chars"] < requirements["total_min"]:
        issues.append(f"总字数不足：{analysis['total_chars']} < {requirements['total_min']}")
    elif analysis["total_chars"] < requirements["total_target"]:
        warnings.append(f"总字数偏少：{analysis['total_chars']} < {requirements['total_target']}")

    # 检查章节质量
    short_sections = []
    short_subsections = []
    one_sentence_subsections = []

    for section in analysis["sections"]:
        # 跳过参考文献等特殊章节
        if any(keyword in section["header"].lower() for keyword in ["参考文献", "references", "致谢", "acknowledgments"]):
            continue

        if section["char_count"] < requirements["main_section_min"]:
            short_sections.append(f"{section['header']}: {section['char_count']}字")

        for subsection in section["subsections"]:
            if subsection["char_count"] < requirements["sub_section_min"]:
                short_subsections.append(f"{subsection['header']}: {subsection['char_count']}字")

            if subsection["paragraph_count"] <= 1:
                one_sentence_subsections.append(subsection["header"])

    if short_sections:
        issues.append(f"过短的主要章节 ({len(short_sections)}个): {', '.join(short_sections[:3])}")

    if short_subsections:
        issues.append(f"过短的子章节 ({len(short_subsections)}个): {', '.join(short_subsections[:3])}")

    if one_sentence_subsections:
        issues.append(f"只有一个段落的子章节 ({len(one_sentence_subsections)}个): {', '.join(one_sentence_subsections[:3])}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "analysis": analysis,
        "requirements": requirements
    }

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
    try:
        structured_llm = llm.with_structured_output(ReportTitle, method="json_mode")
    except Exception:
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
    try:
        structured_llm = llm.with_structured_output(ThemeExtraction, method="json_mode")
    except Exception:
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
    language: str = "en", # Added
    length_instruction: str = "" # 【新增】字数控制指令参数
) -> str:
    """Generate the initial report draft using structured output."""

    # 获取字数要求
    requirements = get_word_count_requirements(detail_level)

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
    if language.lower() == 'zh':
        user_message = f"""🚨🚨🚨 强制性深度学术报告生成任务 - 字数验证模式 🚨🚨🚨

### 📋 绝对强制要求（违背将导致任务失败）：
- **总字数要求**：必须严格达到 {requirements['total_target']} 字（中文字符+英文字符总数）
- **字数验证**：生成后将进行严格的字数统计验证，不达标将被拒绝
- **学术深度**：必须达到硕士论文或学术期刊质量水平
- **内容形式**：绝对禁止大纲式、要点式内容，必须是连贯的学术文章
- **段落要求**：每个段落至少200-300字，包含完整的论证过程

{length_instruction}

### 📊 报告规格：
标题：{report_title}
原始研究查询：{query}
分析发现：{findings[:5000]}
来源数量：{len(selected_sources)}
研究中识别的关键主题：
{extracted_themes}
{available_sources_text}

**重要提醒**：报告内容必须严格围绕原始研究查询"{query}"展开，不得偏离主题或混入无关内容。

### 🎯 强制性内容深度要求（每项都将被验证）：
1. **章节字数**：每个主要章节至少 {requirements['main_section_min']} 字
2. **子章节字数**：每个子章节至少 {requirements['sub_section_min']} 字
3. **段落密度**：每个子章节必须包含至少6-8个完整段落
4. **论证深度**：每个观点都要从理论基础、历史背景、现实意义、未来影响、学术争议五个维度展开
5. **具体案例**：每个子章节必须包含至少2-3个具体案例或实例分析

### 🔥 内容质量标准（将被严格检查）：
- **理论深度**：提供详尽的理论分析、概念阐释、学术背景、理论发展脉络
- **实证支撑**：添加具体案例、数据分析、实证研究、权威引用、学者观点
- **学术论证**：每个段落必须包含主题句、论据展开、深入分析、反思批判、小结过渡
- **连贯叙述**：采用连贯的学术叙述风格，绝对禁止条目式、列表式表达
- **逻辑严密**：确保段落间、章节间有清晰的逻辑过渡和内在联系
- **深度分析**：对每个观点进行多层次、多角度的深入剖析

### ⚠️ 绝对禁止（违反将导致重新生成）：
- 大纲式内容（如"- 要点1"、"• 要点2"等）
- 简单的要点罗列
- 过短的段落（少于200字）
- 缺乏论证的观点陈述
- 框架式或提纲式内容
- 浅层次的分析和讨论

### 📝 具体写作指导：
- 每个段落开头要有明确的主题句
- 每个段落中间要有充分的论证和分析
- 每个段落结尾要有小结或过渡
- 使用丰富的学术词汇和表达
- 引用具体的研究发现和数据
- 提供深入的理论分析和批判思考

围绕这些从研究中自然涌现的关键主题组织您的报告。
创建一个动态、有机的结构，以最佳方式呈现发现，而不是将内容强制放入预定的章节中。
确保全面覆盖，同时保持主题之间的逻辑流程。
详细程度应为{detail_level.upper()}。

您的报告必须广泛、详细，并以研究为基础。包括研究中发现的所有相关数据、示例和见解。
在整个报告中使用适当的引文，仅引用上面列出的可用来源。

关键要求：您必须严格遵循系统提示中提供的所有`report_style_instructions`指令，包括所选报告样式特定的结构、语调和内容要求：{report_style_instructions}

🎯 **最终执行指令**：请立即生成一份严格达到 {requirements['total_target']} 字的深度学术研究报告。每个章节、每个段落都必须有充分的内容深度和学术质量。生成后将进行字数验证，不达标将被要求重新生成。

重要提示：以提供的确切标题开始您的报告："{report_title}" - 不要修改或重新表述它。"""
    else:
        user_message = f"""🚨🚨 MANDATORY DEEP ACADEMIC REPORT GENERATION TASK 🚨🚨

### 📋 CORE REQUIREMENTS (ABSOLUTELY NON-NEGOTIABLE):
- **Total Word Count**: Must strictly reach {requirements['total_target']} words
- **Academic Depth**: Must meet master's thesis or academic journal quality standards
- **Content Form**: Absolutely NO outline-style or bullet-point content, must be coherent academic prose
- **Paragraph Requirements**: Each paragraph minimum 150-250 words with complete argumentation

{length_instruction}

### 📊 REPORT SPECIFICATIONS:
Title: {report_title}
Analyzed Findings: {findings[:5000]}
Number of sources: {len(selected_sources)}
Key themes identified in the research:
{extracted_themes}
{available_sources_text}

### 🎯 MANDATORY CONTENT DEPTH REQUIREMENTS:
1. **Section Word Count**: Each major section minimum {requirements['main_section_min']} words
2. **Subsection Word Count**: Each subsection minimum {requirements['sub_section_min']} words
3. **Paragraph Density**: Each subsection must contain at least 4-6 complete paragraphs
4. **Argumentation Depth**: Each point must be developed from theoretical foundation, historical background, current significance, and future implications

### 🔥 CONTENT QUALITY STANDARDS:
- **Theoretical Depth**: Provide detailed theoretical analysis, concept explanation, academic background
- **Empirical Support**: Add specific cases, data analysis, empirical research and authoritative citations
- **Academic Argumentation**: Each paragraph must include topic sentence, evidence development, analytical interpretation, transitional conclusion
- **Coherent Narrative**: Use coherent academic narrative style, absolutely NO itemized or list-style expression
- **Logical Rigor**: Ensure clear logical transitions and internal connections between paragraphs and sections

### ⚠️ ABSOLUTELY FORBIDDEN:
- Outline-style content (like "- Point 1", "• Point 2", etc.)
- Simple bullet point lists
- Overly short paragraphs (less than 150 words)
- Unsupported opinion statements
- Framework or outline-style content

Organize your report around these key themes that naturally emerged from the research.
Create a dynamic, organic structure that best presents the findings, rather than forcing content into predetermined sections.
Ensure comprehensive coverage while maintaining a logical flow between topics.
The level of detail should be {detail_level.upper()}.

Your report must be extensive, detailed, and grounded in the research. Include all relevant data, examples, and insights found in the research.
Use proper citations to the sources throughout, referring only to the available sources listed above.

It is CRITICAL that you strictly follow all directives within the `report_style_instructions` provided in the system prompt, including structural, tonal, and content requirements specific to the chosen report style: {report_style_instructions}

🎯 **EXECUTION COMMAND**: Immediately generate a {requirements['total_target']}-word deep academic research report ensuring each section has sufficient content depth and academic quality.

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
            if language == "zh":
                direct_prompt_base_template = f"""🚨🚨 强制性深度学术报告生成任务 🚨🚨

### 📋 核心要求（绝对不可违背）：
- **总字数要求**：必须严格达到 {requirements['total_target']} 字
- **学术深度**：必须达到硕士论文或学术期刊质量水平
- **内容形式**：绝对禁止大纲式、要点式内容，必须是连贯的学术文章
- **段落要求**：每个段落至少150-250字，包含完整的论证过程

### 📊 报告规格：
标题：{{report_title}}
基于研究发现：{{findings_preview}}
主题结构：{{themes}}
可用来源：{{sources_info}}
详细程度：{{detail_level}}
当前日期：{{current_date}}

### 🎯 强制性内容要求：
1. **章节字数**：每个主要章节至少 {requirements['main_section_min']} 字
2. **子章节字数**：每个子章节至少 {requirements['sub_section_min']} 字
3. **段落密度**：每个子章节必须包含至少4-6个完整段落
4. **论证深度**：每个观点都要从理论基础、历史背景、现实意义、未来影响四个维度展开

### 🔥 内容质量标准：
- **理论深度**：提供详尽的理论分析、概念阐释、学术背景
- **实证支撑**：添加具体案例、数据分析、实证研究和权威引用
- **学术论证**：每个段落必须包含主题句、论据展开、分析阐释、小结过渡
- **连贯叙述**：采用连贯的学术叙述风格，绝对禁止条目式、列表式表达
- **逻辑严密**：确保段落间、章节间有清晰的逻辑过渡和内在联系

### 📝 格式要求：
- 遵循Markdown格式
- 包含标题、摘要、引言、按主题分章节、讨论与分析、结论和带正确引用[n]的参考文献
- 每个章节都要有详细的子章节划分
- 确保引用格式正确，使用[n]格式

### ⚠️ 绝对禁止：
- 大纲式内容（如"- 要点1"、"• 要点2"等）
- 简单的要点罗列
- 过短的段落（少于150字）
- 缺乏论证的观点陈述
- 框架式或提纲式内容

🎯 **执行指令**：请立即生成一份达到 {requirements['total_target']} 字的深度学术研究报告，确保每个章节都有充分的内容深度和学术质量。"""
            else:
                direct_prompt_base_template = f"""🚨🚨 MANDATORY DEEP ACADEMIC REPORT GENERATION TASK 🚨🚨

### 📋 CORE REQUIREMENTS (ABSOLUTELY NON-NEGOTIABLE):
- **Total Word Count**: Must strictly reach {requirements['total_target']} words
- **Academic Depth**: Must meet master's thesis or academic journal quality standards
- **Content Form**: Absolutely NO outline-style or bullet-point content, must be coherent academic prose
- **Paragraph Requirements**: Each paragraph minimum 150-250 words with complete argumentation

### 📊 REPORT SPECIFICATIONS:
Title: {{report_title}}
Based on findings: {{findings_preview}}
Theme structure: {{themes}}
Available sources: {{sources_info}}
Detail level: {{detail_level}}
Current date: {{current_date}}

### 🎯 MANDATORY CONTENT REQUIREMENTS:
1. **Section Word Count**: Each major section minimum {requirements['main_section_min']} words
2. **Subsection Word Count**: Each subsection minimum {requirements['sub_section_min']} words
3. **Paragraph Density**: Each subsection must contain at least 4-6 complete paragraphs
4. **Argumentation Depth**: Each point must be developed from theoretical foundation, historical background, current significance, and future implications

### 🔥 CONTENT QUALITY STANDARDS:
- **Theoretical Depth**: Provide detailed theoretical analysis, concept explanation, academic background
- **Empirical Support**: Add specific cases, data analysis, empirical research and authoritative citations
- **Academic Argumentation**: Each paragraph must include topic sentence, evidence development, analytical interpretation, transitional conclusion
- **Coherent Narrative**: Use coherent academic narrative style, absolutely NO itemized or list-style expression
- **Logical Rigor**: Ensure clear logical transitions and internal connections between paragraphs and sections

### 📝 FORMAT REQUIREMENTS:
- Follow Markdown format
- Include title, abstract, introduction, thematic sections, discussion & analysis, conclusion and references with correct [n] citations
- Each section must have detailed subsection divisions
- Ensure correct citation format using [n] format

### ⚠️ ABSOLUTELY FORBIDDEN:
- Outline-style content (like "- Point 1", "• Point 2", etc.)
- Simple bullet point lists
- Overly short paragraphs (less than 150 words)
- Unsupported opinion statements
- Framework or outline-style content

🎯 **EXECUTION COMMAND**: Immediately generate a {requirements['total_target']}-word deep academic research report ensuring each section has sufficient content depth and academic quality."""

        direct_prompt_content = direct_prompt_base_template.format(
            report_title=report_title,
            findings_preview=findings[:3000], # 增加预览内容以提供更多信息
            themes=extracted_themes,
            sources_info=available_sources_text,
            detail_level=detail_level.upper(),
            current_date=current_date,
            report_style_instructions=report_style_instructions,
            length_instruction=length_instruction  # 【修复】添加缺失的length_instruction参数
        )

        report_llm = llm.with_config({"max_tokens": 120000, "temperature": 0.5})  # 【增强】提高max_tokens和温度
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
        initial_report = response.content

        # 验证报告质量并进行重试
        max_retries = 3
        for attempt in range(max_retries):
            validation = validate_report_quality(initial_report, detail_level)

            if validation["is_valid"]:
                print(f"✅ 报告质量验证通过 (总字数: {validation['analysis']['total_chars']})")
                return initial_report

            print(f"⚠️ 报告质量验证失败 (尝试 {attempt + 1}/{max_retries})")
            for issue in validation["issues"]:
                print(f"   - {issue}")

            if attempt < max_retries - 1:
                # 构建强制性改进提示
                current_chars = validation['analysis']['total_chars']
                needed_chars = validation['requirements']['total_target'] - current_chars

                improvement_prompt = f"""🚨🚨 强制性报告修复任务 🚨🚨

**当前问题诊断：**
- 当前字数：{current_chars}字（严重不足）
- 目标字数：{validation['requirements']['total_target']}字
- 需要增加：{needed_chars}字

**具体问题：**
{chr(10).join(f"- {issue}" for issue in validation["issues"])}

**原始报告：**
{initial_report}

### 🚨 强制性修复要求（绝对不可违背）：

#### 1. 字数强制要求
- **总字数**：必须达到{validation['requirements']['total_target']}字
- **主章节**：每个主要章节至少{validation['requirements']['main_section_min']}字
- **子章节**：每个子章节至少{validation['requirements']['sub_section_min']}字

#### 2. 内容深度要求
- **段落密度**：每个子章节必须包含至少4-6个完整段落
- **段落长度**：每个段落至少150-250字，包含完整的论证过程
- **学术深度**：必须达到硕士论文或学术期刊质量水平

#### 3. 结构完整性
- **消除空章节**：所有章节都必须有实质性内容
- **逻辑连贯**：确保章节间有清晰的逻辑过渡
- **内容充实**：每个观点都要提供详细的理论分析和实证支撑

#### 4. 质量标准
- **绝对禁止**：大纲式、要点式内容
- **必须采用**：连贯的学术叙述风格
- **深度论证**：每个观点从理论基础、历史背景、现实意义、未来影响四个维度展开

🎯 **执行指令**：请立即生成一份完全符合上述要求的{validation['requirements']['total_target']}字深度学术研究报告。"""

                retry_llm = llm.with_config({"max_tokens": 120000, "temperature": 0.4})  # 【增强】提高重试时的max_tokens
                retry_response = await retry_llm.ainvoke(improvement_prompt)
                initial_report = retry_response.content

        # 如果所有重试都失败，进行强制性字数扩展
        print(f"⚠️ 经过 {max_retries} 次重试，报告仍未完全达到要求，开始强制性扩展...")

        # 【新增】强制性多轮扩展机制
        try:
            final_expanded_report = await force_word_count_compliance(
                llm, initial_report, detail_level, language
            )

            # 最终验证
            final_validation = validate_report_quality(final_expanded_report, detail_level)
            if final_validation["is_valid"]:
                print(f"✅ 强制扩展成功，报告质量达标 (总字数: {final_validation['analysis']['total_chars']})")
                return final_expanded_report
            else:
                print(f"⚠️ 强制扩展后仍有问题，但字数已改善 (总字数: {final_validation['analysis']['total_chars']})")
                return final_expanded_report
        except Exception as e:
            print(f"❌ 强制扩展失败: {e}")
            return initial_report

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

        if language.lower() == 'zh':
            simple_user_message = f"标题：{report_title}\n\n发现（预览）：{findings[:5000]}\n{available_sources_text}"
        else:
            simple_user_message = f"Title: {report_title}\n\nFindings (preview): {findings[:5000]}\n{available_sources_text}"

        simple_prompt = ChatPromptTemplate.from_messages([
            ("system", simple_system_message),
            ("user", simple_user_message)
        ])

        # 根据字数要求调整max_tokens
        required_chars = requirements['total_target']
        # 估算需要的tokens（中文字符约1.5倍，英文字符约0.25倍）
        estimated_tokens = int(required_chars * 1.8)  # 保守估计
        max_tokens = min(estimated_tokens, 120000)  # 不超过模型限制

        simple_llm = llm.with_config({"max_tokens": max_tokens, "temperature": 0.6})
        response = await (simple_prompt | simple_llm).ainvoke({})

        # 验证生成的内容字数
        generated_content = response.content
        actual_chars = count_chinese_and_english_chars(generated_content)

        # 如果字数严重不足，尝试重新生成
        if actual_chars < requirements['total_min'] * 0.7:  # 少于最低要求的70%
            print(f"初次生成字数不足({actual_chars}字)，尝试重新生成...")

            # 使用更强的提示词重新生成
            enhanced_prompt = f"""🚨🚨🚨 紧急字数要求 🚨🚨🚨

当前生成的内容只有{actual_chars}字，严重不足！

必须重新生成一份至少{requirements['total_target']}字的完整报告。

{user_message}

⚠️ 特别注意：
- 每个段落必须至少300字
- 每个子章节必须至少800字
- 每个主要章节必须至少2000字
- 绝对不能是大纲式内容
- 必须是连贯的学术文章

请立即重新生成完整的{requirements['total_target']}字报告！"""

            enhanced_llm = llm.with_config({"max_tokens": max_tokens, "temperature": 0.7})
            enhanced_response = await enhanced_llm.ainvoke(enhanced_prompt)
            generated_content = enhanced_response.content
            actual_chars = count_chinese_and_english_chars(generated_content)
            print(f"重新生成后字数: {actual_chars}字")

        return generated_content

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

Ensure your enhancements strictly align with the overall `report_style_instructions` ({report_style_instructions}) for tone, depth, and focus.
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
            enhance_llm = llm.with_config({"max_tokens": 80000, "temperature": 0.4})  # 【增强】提高章节增强的max_tokens
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

    enhanced_report = "".join(enhanced_report_parts).strip()

    # 验证增强后的报告质量
    validation = validate_report_quality(enhanced_report, "standard")  # 使用标准级别验证
    if not validation["is_valid"]:
        print("⚠️ 增强后的报告仍存在质量问题：")
        for issue in validation["issues"]:
            print(f"   - {issue}")
    else:
        print(f"✅ 报告增强完成 (总字数: {validation['analysis']['total_chars']})")

    return enhanced_report

async def expand_short_sections(
    llm: ChatOpenAI,
    report_content: str,
    detail_level: str,
    language: str = "zh",
    length_instruction: str = ""  # 【新增】字数控制指令参数
) -> str:
    """专门扩展过短的章节"""
    validation = validate_report_quality(report_content, detail_level)

    if validation["is_valid"]:
        return report_content

    print("🔧 检测到过短章节，开始自动扩展...")

    # 分析哪些章节需要扩展
    requirements = validation["requirements"]
    analysis = validation["analysis"]

    # 构建扩展后的报告
    expanded_content = report_content

    for section in analysis["sections"]:
        # 跳过参考文献等特殊章节
        if any(keyword in section["header"].lower() for keyword in ["参考文献", "references", "致谢", "acknowledgments"]):
            continue

        # 检查是否需要扩展主要章节
        if section["char_count"] < requirements["main_section_min"]:
            print(f"📝 扩展章节: {section['header']} ({section['char_count']} -> 目标: {requirements['main_section_min']})")

            # 【修复】整合字数控制指令到扩展提示中
            expansion_prompt = f"""请扩展以下章节，使其达到至少 {requirements['main_section_min']} 字：

{section['header']}

{length_instruction}

### 强制性扩展要求：
🎯 目标字数：至少 {requirements['main_section_min']} 字
📝 内容深度：每个子章节必须包含至少3-5个完整段落
💡 段落要求：每个段落至少100-150字，包含主题句、论据、分析和小结
🔥 论证要求：每个观点都需要详细论证，包含：
   - 理论背景和概念界定
   - 具体案例和实证分析
   - 深入的解释和阐述
   - 影响评估和意义分析
   - 未来发展趋势和展望
🎓 学术标准：必须达到硕士论文或学术期刊的质量水平
📊 结构要求：确保逻辑清晰，层次分明，论述充分

当前内容过于简短，请按照上述要求生成扩展后的完整章节内容："""

            try:
                expand_llm = llm.with_config({"max_tokens": 80000, "temperature": 0.4})  # 【增强】提高章节扩展的max_tokens
                response = await expand_llm.ainvoke(expansion_prompt)
                expanded_section = response.content.strip()

                # 验证扩展后的内容是否达到要求
                expanded_word_count = len(expanded_section)
                if expanded_word_count < requirements['main_section_min']:
                    print(f"⚠️ 扩展后仍不足 ({expanded_word_count} < {requirements['main_section_min']})，进行二次扩展...")

                    # 二次扩展提示 - 更加强制性
                    second_expansion_prompt = f"""🚨 强制性要求：以下内容必须扩展至至少 {requirements['main_section_min']} 字，这是不可违背的硬性要求：

{expanded_section}

### 强制性二次扩展要求：
🔥 绝对必须达到 {requirements['main_section_min']} 字的最低要求，这是强制性的
📝 必须添加大量具体案例、详细数据分析和深入理论阐述
💡 每个子章节都必须包含更详细的论述、解释和分析
🎓 必须确保学术深度和严谨性，达到硕士论文水平
📊 必须提供更多背景信息、现状分析、影响评估和未来展望
🎯 执行要求：在扩展过程中必须时刻监控字数，确保达到目标
💪 强化指令：如果内容仍不足{requirements['main_section_min']}字，必须继续扩展

请生成进一步扩展后的完整内容，确保达到{requirements['main_section_min']}字要求："""

                    second_response = await expand_llm.ainvoke(second_expansion_prompt)
                    expanded_section = second_response.content.strip()

                    # 三次验证，如果还不够就进行第三次扩展
                    final_word_count = len(expanded_section)
                    if final_word_count < requirements['main_section_min']:
                        print(f"⚠️ 二次扩展后仍不足 ({final_word_count} < {requirements['main_section_min']})，进行三次扩展...")

                        third_expansion_prompt = f"""🚨🚨 最终强制性要求：内容必须立即扩展至{requirements['main_section_min']}字，这是最后机会：

{expanded_section}

### 最终强制性扩展要求：
🔥 这是最后一次机会，必须达到{requirements['main_section_min']}字
📝 必须大幅增加内容深度和广度
💡 必须添加更多段落、更多分析、更多案例
🎓 必须达到学术标准，不能再有任何妥协
📊 必须包含详尽的论述和分析

请立即生成扩展后的完整内容："""

                        third_response = await expand_llm.ainvoke(third_expansion_prompt)
                        expanded_section = third_response.content.strip()

                # 替换原章节
                section_pattern = re.escape(section['header']) + r'(.*?)(?=##\s+|\Z)'
                expanded_content = re.sub(section_pattern, f"{section['header']}\n\n{expanded_section}\n\n", expanded_content, flags=re.DOTALL)

            except Exception as e:
                print(f"❌ 扩展章节失败: {e}")

    return expanded_content

async def advanced_iterative_expansion(
    llm: ChatOpenAI,
    report_content: str,
    target_chars: int,
    max_iterations: int = 5,
    language: str = "zh"
) -> str:
    """优化的迭代扩展算法，通过分段扩展确保达到目标字数"""

    current_content = report_content

    for iteration in range(max_iterations):
        current_chars = count_chinese_and_english_chars(current_content)
        print(f"🔄 迭代 {iteration + 1}/{max_iterations}: 当前字数 {current_chars}")

        if current_chars >= target_chars:
            print(f"✅ 已达到目标字数: {current_chars} >= {target_chars}")
            return current_content

        needed_chars = target_chars - current_chars
        completion_ratio = current_chars / target_chars

        print(f"📊 需要增加: {needed_chars} 字 (完成度: {completion_ratio:.1%})")

        # 构建简化的扩展提示
        expansion_prompt = f"""请将以下报告扩展到至少 {target_chars} 字。当前字数为 {current_chars} 字，需要增加 {needed_chars} 字。

扩展要求：
1. 保持原有结构和逻辑
2. 大幅扩展每个段落的内容深度
3. 添加更多详细的分析、例证和论述
4. 确保学术质量和连贯性
5. 每个主要章节至少2500字
6. 每个段落至少200字

当前报告内容：
{current_content}

请生成扩展后的完整报告，确保达到 {target_chars} 字的要求："""

        try:
            # 使用较高的max_tokens确保能生成足够内容
            expand_llm = llm.with_config({"max_tokens": 120000, "temperature": 0.5})
            response = await expand_llm.ainvoke(expansion_prompt)
            expanded_content = response.content.strip()

            # 验证扩展效果
            expanded_chars = count_chinese_and_english_chars(expanded_content)

            if expanded_chars > current_chars:
                improvement = expanded_chars - current_chars
                current_content = expanded_content
                print(f"✅ 扩展成功: +{improvement} 字")

                # 如果接近目标，可以提前结束
                if expanded_chars >= target_chars * 0.95:
                    print(f"🎯 接近目标字数，提前结束")
                    break
            else:
                print(f"⚠️ 扩展失败，字数未增加")
                # 如果连续失败，尝试不同的提示策略
                if iteration >= 2:
                    print(f"🔄 尝试强制扩展策略...")
                    force_prompt = f"""🚨 强制扩展要求：必须将以下报告扩展到至少 {target_chars} 字！

当前字数：{current_chars} 字
目标字数：{target_chars} 字
必须增加：{needed_chars} 字

强制要求：
- 每个现有段落必须扩展至少300字
- 每个章节必须添加2-3个新的子章节
- 必须包含大量具体案例和详细分析
- 绝对不能少于{target_chars}字

当前内容：
{current_content}

立即生成扩展后的完整报告："""

                    force_response = await expand_llm.ainvoke(force_prompt)
                    force_expanded = force_response.content.strip()
                    force_chars = count_chinese_and_english_chars(force_expanded)

                    if force_chars > current_chars:
                        current_content = force_expanded
                        print(f"✅ 强制扩展成功: +{force_chars - current_chars} 字")
                    else:
                        print(f"❌ 强制扩展也失败")
                        break

        except Exception as e:
            print(f"❌ 扩展过程出错: {e}")
            break

    final_chars = count_chinese_and_english_chars(current_content)
    print(f"📊 迭代扩展完成，最终字数: {final_chars}")
    return current_content



async def force_word_count_compliance(
    llm: ChatOpenAI,
    report_content: str,
    detail_level: str,
    language: str = "zh"
) -> str:
    """强制确保报告达到字数要求，使用优化的迭代扩展算法"""
    requirements = get_word_count_requirements(detail_level)
    current_word_count = count_chinese_and_english_chars(report_content)

    if current_word_count >= requirements['total_min']:
        print(f"✅ 报告字数已达标：{current_word_count} >= {requirements['total_min']}")
        return report_content

    print(f"🚨 报告字数严重不足：{current_word_count} < {requirements['total_min']}，启动优化迭代扩展...")

    # 使用优化的迭代扩展算法
    expanded_report = await advanced_iterative_expansion(
        llm=llm,
        report_content=report_content,
        target_chars=requirements['total_target'],
        max_iterations=8,
        language=language
    )

    final_word_count = count_chinese_and_english_chars(expanded_report)
    if final_word_count >= requirements['total_min']:
        print(f"✅ 优化迭代扩展成功：{final_word_count} >= {requirements['total_min']}")
        return expanded_report
    else:
        print(f"⚠️ 迭代扩展后仍不足：{final_word_count} < {requirements['total_min']}，返回最佳版本")
        return expanded_report

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

    # 【修复】移除3个章节的限制，处理所有重要章节以确保报告完整性和连贯性
    # 注释：原来只处理前3个章节导致报告不完整，现在处理所有重要章节

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

When expanding this section, rigorously apply the `report_style_instructions` ({report_style_instructions}) to maintain consistency in style, tone, and content focus for the report type.
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
            expand_llm = llm.with_config({"max_tokens": 40960, "temperature": 0.3})
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
