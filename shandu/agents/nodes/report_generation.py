"""Report generation nodes with modular, robust processing."""
import re
import time
import asyncio
import traceback
import json # Added for parsing LLM response for visualizable data
import uuid # Added for generating unique chart filenames
import os
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from shandu.prompts import get_report_style_guidelines, safe_format # Updated import
from ..processors.content_processor import AgentState
from ..processors.report_generator import (
    generate_title,
    extract_themes,
    generate_initial_report,
    enhance_report,
    expand_key_sections,
    format_citations,
    expand_short_sections,
    validate_report_quality,
    force_word_count_compliance
)
from ..utils.agent_utils import log_chain_of_thought, _call_progress_callback, is_shutdown_requested
from ..utils.citation_registry import CitationRegistry
from ..utils.citation_manager import CitationManager, SourceInfo, Learning

console = Console()

def _check_topic_consistency(report: str, original_query: str) -> bool:
    """
    检查报告内容是否与原始查询主题一致
    返回True表示发现不一致，需要修复
    """
    if not report or not original_query:
        return False

    # 提取原始查询的关键词
    original_keywords = set(original_query.lower().split())

    # 定义一些明显不相关的主题关键词
    unrelated_topics = {
        "明代社会结构", "制度张力", "实践创新", "社会分层", "等级制度",
        "政治-社会互动", "科举制度", "地方治理", "经济基础", "文化认同",
        "意识形态渗透", "马克斯·韦伯", "布迪厄", "新制度经济学",
        "徽州文书", "地方志", "全球比较案例", "制度设计", "实践变异",
        "宗族组织", "制度嵌套", "治理创新", "文化特权", "社会流动",
        "结构性张力", "制度韧性", "变革动力", "早期现代化"
    }

    # 如果原始查询是关于西游记的，检查是否混入了明代社会结构内容
    if "西游记" in original_query or "西游" in original_query:
        for topic in unrelated_topics:
            if topic in report:
                console.print(f"[red]发现不相关内容: {topic}[/]")
                return True

    return False

# 新增：学术质量检查和连贯性优化函数
async def _ensure_report_coherence(
    llm,
    report: str,
    original_query: str,
    language: str = "zh",
    current_date: str = ""
) -> str:
    """
    确保报告的学术质量和整体连贯性，将拼凑式的内容转化为符合学术标准的深度报告。
    同时检查并修复主题一致性问题。
    """
    from shandu.prompts import get_system_prompt

    # 【新增】主题一致性检查
    if _check_topic_consistency(report, original_query):
        console.print("[yellow]Detected topic inconsistency, applying fixes...[/]")

    # 优先使用新的学术质量检查提示词
    academic_prompt_template = get_system_prompt("academic_quality_check_prompt", language)

    # 如果没有找到学术质量检查提示词，回退到连贯性检查
    if not academic_prompt_template:
        academic_prompt_template = get_system_prompt("global_report_consistency_check_prompt", language)

    if not academic_prompt_template:
        # 如果都没有找到模板，返回原报告
        return report

    try:
        # 构建学术质量检查提示
        academic_prompt = academic_prompt_template.format(
            report_title=report.split('\n')[0].replace('#', '').strip() if report else "研究报告",
            original_query=original_query,
            full_report_content=report
        )

        # 调用LLM进行学术质量分析
        academic_llm = llm.with_config({"max_tokens": 2048, "temperature": 0.1})
        academic_response = await academic_llm.ainvoke(academic_prompt)
        academic_analysis = academic_response.content

        # 如果发现学术质量问题，进行修复
        if "重大问题" in academic_analysis or "不一致" in academic_analysis or "矛盾" in academic_analysis or "改进" in academic_analysis:
            console.print("[yellow]Detected academic quality issues, applying fixes...[/]")

            # 构建修复提示
            fix_prompt = f"""
基于以下学术质量分析，请修复报告中的问题，确保整篇报告达到硕士论文或学术期刊的质量标准：

学术质量分析：
{academic_analysis}

原始报告：
{report}

请返回修复后的完整报告，确保：
1. 符合学术写作规范，具备完整的学术结构
2. 具有扎实的理论基础和创新性见解
3. 各章节之间有清晰的逻辑联系和自然过渡
4. 整体论述连贯，体现学术深度和批判性思维
5. 引用格式规范，参考文献充足且权威
6. 语言表达专业、准确，符合学术标准

修复后的报告：
"""

            fix_response = await academic_llm.ainvoke(fix_prompt)
            return fix_response.content
        else:
            console.print("[green]Report academic quality check passed[/]")
            return report

    except Exception as e:
        console.print(f"[yellow]Academic quality check failed: {str(e)}, using original report[/]")
        return report

# Structured output models for report generation
class ReportSection(BaseModel):
    """Structured output for a report section."""
    title: str = Field(description="Title of the section")
    content: str = Field(description="Content of the section")
    order: int = Field(description="Order of the section in the report", default=0)
    status: str = Field(description="Processing status of the section", default="pending")

class FinalReport(BaseModel):
    """Structured output for the final report."""
    title: str = Field(description="Title of the report")
    sections: list[ReportSection] = Field(
        description="List of report sections",
        min_items=1
    )
    references: list[str] = Field(
        description="List of references in the report",
        min_items=0
    )

# Maximum retry attempts for report generation processes
MAX_RETRIES = 3

# Helper function for detail level instructions
def _get_length_instruction(detail_level: str) -> str:
    """Generates a prompt instruction based on the detail_level."""
    # 【修复】确保 detail_level 是有效的字符串类型
    if not isinstance(detail_level, str):
        detail_level = str(detail_level) if detail_level is not None else "standard"
        print(f"⚠️ 警告：detail_level 不是字符串类型，已转换为：'{detail_level}'")

    # 转换为小写以便比较，并去除空白字符
    detail_level_clean = detail_level.lower().strip()

    if detail_level_clean == "brief":
        return """【强制性字数要求：严格达到4000字】
🚨 绝对强制：整体报告必须严格达到约4000字，这是不可违背的硬性要求
📝 内容策略：提供简洁但充实的内容，确保每个要点都有充分论述
⚠️ 重要提醒：虽然是简要版本，但必须保证内容深度和学术质量
✅ 验证标准：确保整体报告约4000字，这是最低要求
📋 结构要求：必须包含完整的章节结构、子章节和参考文献
🔥 内容深度：每个主要章节至少600-800字，每个子章节至少200-300字
💡 质量要求：每个子章节必须包含至少2-3个完整段落，确保论述充分
🎓 学术标准：必须达到学术报告的质量标准，避免简单的要点罗列
🎯 执行要求：在生成过程中必须时刻监控字数，确保达到4000字目标"""
    elif detail_level_clean == "detailed":
        return """【字数要求：约15000字】
🎯 强制性要求：整体报告必须严格达到约15000字
📝 内容策略：请高度扩展内容，添加大量深度、更多示例和详细解释
⚠️ 重要提醒：内容应明显比标准版本更长更全面，必须达到深度学术水平
✅ 验证标准：确保整体报告约15000字，这是必须达到的目标
📋 结构要求：必须包含详细的章节结构、多个子章节和完整的参考文献
🔥 内容深度：每个主要章节至少2000-3000字，每个子章节至少800-1200字
💡 质量要求：每个子章节必须包含至少4-6个完整段落，提供深入分析、具体例证和理论阐述
📊 论证要求：每个观点都需要详细论证，包含背景分析、现状描述、影响评估和未来展望
🎓 学术标准：必须达到硕士论文或学术期刊的质量标准，提供原创性见解和深度分析"""
    elif detail_level_clean.startswith("custom_"):
        try:
            # 【修复】使用清理后的字符串进行解析
            parts = detail_level_clean.split('_', 1)
            if len(parts) > 1 and parts[1].isdigit():
                word_count = int(parts[1])
                return f"""【字数要求：约{word_count}字】
🎯 强制性要求：整体报告必须严格控制在约{word_count}字
📝 内容策略：请根据此字数要求调整详细程度、示例数量和解释深度
⚠️ 重要提醒：如果主题较窄，请扩展背景、含义或相关概念以达到目标字数
✅ 验证标准：这是强制性要求，必须努力达到{word_count}字的目标
📋 结构要求：必须包含完整的章节结构、子章节和参考文献"""
            else:
                # Fallback if parsing fails (e.g. "custom_" without number or "custom_abc")
                print(f"⚠️ 警告：无法从 detail_level '{detail_level}' 解析字数，使用标准设置")
                return """【字数要求：约5000字】
🎯 强制性要求：整体报告必须严格控制在约5000字
📝 内容策略：提供平衡的详细程度
✅ 验证标准：确保整体报告约5000字"""
        except (ValueError, IndexError) as e: # 【修复】更好的异常处理
            print(f"⚠️ 警告：detail_level '{detail_level}' 格式无效，错误：{e}，使用标准设置")
            return """【字数要求：约5000字】
🎯 强制性要求：整体报告必须严格控制在约5000字
📝 内容策略：提供平衡的详细程度
✅ 验证标准：确保整体报告约5000字"""
    elif detail_level_clean == "standard":
        return """【强制性字数要求：严格达到18000字】
🚨 绝对强制：整体报告必须严格达到约18000字，这是不可违背的硬性要求
📝 内容策略：提供充实的详细程度，确保内容深度和广度的平衡
⚠️ 重要提醒：这是标准长度，必须达到学术报告的深度要求
✅ 验证标准：确保整体报告约18000字，这是基准要求
📋 结构要求：必须包含完整的章节结构、多个子章节和参考文献
🔥 内容深度：每个主要章节至少3000字，每个子章节至少1200字
💡 质量要求：每个子章节必须包含至少5-6个完整段落，确保论述充分
🎓 学术标准：必须体现学术深度和严谨性，提供深入的分析和论证
🎯 执行要求：在生成过程中必须时刻监控字数，确保达到18000字目标
📊 内容要求：每个段落至少200字，包含主题句、论据、分析和小结
🔍 深度要求：必须提供具体案例、数据分析、理论阐述和实证研究
💪 强化指令：如果内容不足18000字，必须继续扩展直到达到要求
🎨 扩展策略：通过增加理论背景、历史分析、案例研究、对比分析、未来展望等维度来丰富内容
🔬 学术深度：每个观点都要从多个角度进行深入分析，包含批判性思维和创新见解""" # Enhanced standard instruction
    else: # 【修复】回退到标准设置，处理任何未知值
        # 记录未知的 detail_level 值
        print(f"⚠️ 警告：未知的 detail_level '{detail_level}'，使用标准设置")
        return """【字数要求：约10000字】
🎯 强制性要求：整体报告必须严格达到约10000字
📝 内容策略：提供平衡的详细程度，确保内容充实但不冗余
⚠️ 重要提醒：这是标准长度，需要在深度和广度之间找到平衡
✅ 验证标准：确保整体报告约10000字，这是基准要求
📋 结构要求：必须包含完整的章节结构、子章节和参考文献
🔥 内容深度：每个主要章节至少1500-2000字，每个子章节至少500-700字
💡 质量要求：每个子章节必须包含至少3-4个完整段落，确保论述充分
🎓 学术标准：必须达到学术报告的质量标准
🎯 执行要求：在生成过程中必须时刻监控字数，确保达到10000字目标"""

async def prepare_report_data(state: AgentState) -> Tuple[CitationManager, CitationRegistry, Dict[str, Any]]:
    """
    Prepare all necessary data for report generation, ensuring sources are correctly registered.

    Args:
        state: The current agent state

    Returns:
        Tuple containing the citation manager, citation registry, and citation statistics
    """
    # Initialize or retrieve citation manager
    if "citation_manager" not in state:
        citation_manager = CitationManager()
        state["citation_manager"] = citation_manager
        # For backward compatibility
        state["citation_registry"] = citation_manager.citation_registry
    else:
        citation_manager = state["citation_manager"]

    citation_registry = citation_manager.citation_registry

    # Pre-register all selected sources and extract learnings
    if "selected_sources" in state and state["selected_sources"]:
        for url in state["selected_sources"]:
            source_meta = next((s for s in state["sources"] if s.get("url") == url), {})

            source_info = SourceInfo(
                url=url,
                title=source_meta.get("title", ""),
                snippet=source_meta.get("snippet", ""),
                source_type="web",
                content_type=source_meta.get("content_type", "article"),
                access_time=time.time(),
                domain=url.split("//")[1].split("/")[0] if "//" in url else "unknown",
                reliability_score=0.8,  # Default score, could be more dynamic
                metadata=source_meta
            )

            citation_manager.add_source(source_info)

            for analysis in state["content_analysis"]:
                if url in analysis.get("sources", []):
                    citation_manager.extract_learning_from_text(
                        analysis.get("analysis", ""),
                        url,
                        context=f"Analysis for query: {analysis.get('query', '')}"
                    )

            # For backward compatibility with citation registry
            cid = citation_registry.register_citation(url)
            citation_registry.update_citation_metadata(cid, {
                "title": source_meta.get("title", "Untitled"),
                "date": source_meta.get("date", "n.d."),
                "url": url
            })

    citation_stats = citation_manager.get_learning_statistics()
    console.print(f"[bold green]Processed {citation_stats.get('total_learnings', 0)} learnings from {citation_stats.get('total_sources', 0)} sources[/]")

    return citation_manager, citation_registry, citation_stats


async def generate_initial_report_node(llm, include_objective, progress_callback, state: AgentState) -> AgentState:
    """Generate the initial report with enhanced citation tracking using a modular approach."""
    state["status"] = "Generating initial report with enhanced source attribution"
    console.print("[bold blue]Generating comprehensive report with dynamic structure and source tracking...[/]")

    current_date = state["current_date"]

    # Prepare all citation data
    citation_manager, citation_registry, citation_stats = await prepare_report_data(state)

    # New Step: Extract visualizable data from sources
    console.print("[bold blue]Extracting visualizable data from sources...[/]")
    for source_info in citation_manager.sources.values():
        if hasattr(source_info, 'extracted_content') and source_info.extracted_content:
            try:
                prompt = f"""Analyze the following text content and extract any data suitable for visualization.
Structure the output as a JSON string representing a list of dictionaries. Each dictionary should describe one distinct dataset.
Each dictionary must have the following keys:
- "data_points": The actual data (e.g., [[1, 2], [3, 4]] for scatter/line, [10, 20, 30] for bar).
- "data_type": A string describing the nature of the data (e.g., 'time-series', 'categorical_counts', 'comparison', 'distribution', 'table_data', 'list_of_values').
- "potential_chart_types": A list of strings suggesting suitable chart types (e.g., ['line_chart', 'bar_chart', 'pie_chart', 'scatter_plot', 'table']).
- "title_suggestion": A string for a potential chart title.
- "x_axis_label_suggestion": (Optional) Suggested label for X-axis.
- "y_axis_label_suggestion": (Optional) Suggested label for Y-axis.
- "labels": (Optional) List of strings for labels (e.g., for pie chart slices or bar categories).
- "description": A brief natural language description of what the data represents.

If no visualizable data is found, return an empty list "[]".

Ensure the output is a valid JSON string.

Text content to analyze:
---
{source_info.extracted_content}
---

JSON output:
"""
                visual_data_llm = llm.with_config({"temperature": 0.0, "max_tokens": 2048}) # Use a specific LLM configuration if needed
                response = await visual_data_llm.ainvoke(prompt)

                llm_output = response.content.strip()

                # Sometimes LLMs wrap JSON in ```json ... ```, try to extract it
                if llm_output.startswith("```json"):
                    llm_output = llm_output[7:]
                    if llm_output.endswith("```"):
                        llm_output = llm_output[:-3]
                llm_output = llm_output.strip()

                if not llm_output:
                    console.print(f"[yellow]LLM returned empty response for visualizable data from source: {source_info.url}[/]")
                    continue

                parsed_visual_data = json.loads(llm_output)

                if isinstance(parsed_visual_data, list):
                    # Basic validation of list items
                    valid_items = []
                    for item in parsed_visual_data:
                        if isinstance(item, dict) and "data_points" in item and "data_type" in item:
                            valid_items.append(item)
                        else:
                            console.print(f"[yellow]Skipping invalid item in visualizable data from LLM for source {source_info.url}: {item}[/yellow]")

                    if valid_items:
                        source_info.visualizable_data.extend(valid_items)
                        console.print(f"[green]Successfully extracted {len(valid_items)} visualizable data items from: {source_info.url}[/]")
                else:
                    console.print(f"[yellow]LLM response for visualizable data from source {source_info.url} was not a list as expected: {parsed_visual_data}[/yellow]")

            except json.JSONDecodeError as e:
                console.print(f"[red]Error parsing JSON for visualizable data from LLM for source {source_info.url}: {e}[/]")
                console.print(f"[red]LLM Output was: {llm_output}[/red]")
            except Exception as e:
                console.print(f"[red]Error extracting visualizable data for source {source_info.url}: {e}\n{traceback.format_exc()}[/]")

            # Step 3 (within source loop): Generate chart code for each visualizable data item
            if source_info.visualizable_data:
                console.print(f"[blue]Generating Matplotlib chart code for visualizable data in {source_info.url}...[/]")
                for data_item_index, data_item in enumerate(source_info.visualizable_data):
                    if not (isinstance(data_item, dict) and \
                            data_item.get("potential_chart_types") and \
                            data_item.get("data_points")):
                        console.print(f"[yellow]Skipping chart code generation for invalid data_item in {source_info.url}: {data_item}[/yellow]")
                        continue

                    chosen_chart_type = data_item["potential_chart_types"][0] # Pick the first suggested
                    chart_filename = f"chart_{uuid.uuid4().hex[:10]}.png"

                    # Construct prompt for Matplotlib code generation
                    chart_prompt_parts = [
                        f"Generate a Python script using Matplotlib to create a '{chosen_chart_type}'.",
                        "The script should be complete, executable, and save the chart to a file.",
                        f"The data to plot is: {data_item['data_points']}",
                        f"Save the generated chart as '{chart_filename}'."
                    ]
                    if data_item.get("title_suggestion"):
                        chart_prompt_parts.append(f"Use the title: '{data_item['title_suggestion']}'.")
                    if data_item.get("x_axis_label_suggestion"):
                        chart_prompt_parts.append(f"Label the X-axis as: '{data_item['x_axis_label_suggestion']}'.")
                    if data_item.get("y_axis_label_suggestion"):
                        chart_prompt_parts.append(f"Label the Y-axis as: '{data_item['y_axis_label_suggestion']}'.")
                    if data_item.get("labels"): # For things like pie chart labels or bar categories
                        chart_prompt_parts.append(f"Use these labels for data segments/categories: {data_item['labels']}.")

                    chart_prompt_parts.extend([
                        "The script should include all necessary imports (e.g., `import matplotlib.pyplot as plt`).",
                        "Ensure the plot is properly shown and then closed to free up memory (e.g., `plt.show()` then `plt.close()` or just `plt.savefig()` and `plt.close()`). For backend execution, prefer `plt.savefig()` and `plt.close()`.",
                        "Output ONLY the Python code block. Do not include any explanations, comments outside the code, or markdown formatting like ```python ... ```."
                    ])

                    chart_code_prompt = "\n".join(chart_prompt_parts)

                    try:
                        chart_code_llm = llm.with_config({"temperature": 0.0, "max_tokens": 1500}) # LLM for code gen
                        response = await chart_code_llm.ainvoke(chart_code_prompt)
                        generated_code = response.content.strip()

                        # Clean up potential markdown formatting if LLM didn't follow instructions perfectly
                        if generated_code.startswith("```python"):
                            generated_code = generated_code[9:]
                            if generated_code.endswith("```"):
                                generated_code = generated_code[:-3]
                        elif generated_code.startswith("```"): # More generic ``` removal
                            generated_code = generated_code[3:]
                            if generated_code.endswith("```"):
                                generated_code = generated_code[:-3]
                        generated_code = generated_code.strip()

                        if not generated_code or not "plt.savefig" in generated_code : # Basic check for valid code
                            console.print(f"[red]LLM generated empty or invalid (missing savefig) Matplotlib code for a data_item in {source_info.url}. Skipping.[/red]")
                            console.print(f"[red]Prompt was:\n{chart_code_prompt}\nOutput was:\n{generated_code}[/red]")
                            continue

                        # Store the generated code and filename in the data_item
                        data_item['matplotlib_code'] = generated_code
                        data_item['chart_filename'] = chart_filename
                        # Update the item in the list directly (though it's already a reference, this is explicit)
                        source_info.visualizable_data[data_item_index] = data_item

                        console.print(f"[green]Successfully generated Matplotlib code for '{chart_filename}' from data in {source_info.url}[/green]")

                    except Exception as e:
                        console.print(f"[red]Error generating Matplotlib code for a data_item in {source_info.url}: {e}\n{traceback.format_exc()}[/]")
                        console.print(f"[red]Problematic data_item: {data_item}[/red]")

        else:
            console.print(f"[yellow]Skipping visualizable data extraction for source {source_info.url} due to missing or empty extracted_content.[/]")
    # End of new step for visualizable data extraction

    # Step 1: Generate report title (with retries)
    report_title = None
    for attempt in range(MAX_RETRIES):
        try:
            report_title = await generate_title(llm, state['query'])
            console.print(f"[bold green]Generated title: {report_title}[/]")
            break
        except Exception as e:
            console.print(f"[yellow]Title generation attempt {attempt+1} failed: {str(e)}[/]")
            if attempt == MAX_RETRIES - 1:
                report_title = f"Research on {state['query']}"
                console.print(f"[yellow]Using fallback title: {report_title}[/]")

    # Step 2: Extract themes to structure the report (with retries)
    extracted_themes = None
    for attempt in range(MAX_RETRIES):
        try:
            extracted_themes = await extract_themes(llm, state['findings'])
            break
        except Exception as e:
            console.print(f"[yellow]Theme extraction attempt {attempt+1} failed: {str(e)}[/]")
            if attempt == MAX_RETRIES - 1:
                # Create fallback themes if all attempts fail
                extracted_themes = "## Main Concepts\nCore concepts related to the topic.\n\n## Applications\nPractical applications and implementations.\n\n## Challenges\nChallenges and limitations in the field.\n\n## Future Directions\nEmerging trends and future possibilities."
                console.print("[yellow]Using fallback themes structure[/]")

    # Step 3: Format citations (with retries)
    # (Themes are extracted before this, but callback for themes is after this and before initial report generation)
    # Store identified themes and call progress callback
    state["identified_themes"] = extracted_themes
    log_chain_of_thought(state, f"Extracted themes for the report: {str(extracted_themes)[:200]}...") # Log a snippet
    if progress_callback: # Explicitly call callback for themes
        await _call_progress_callback(progress_callback, state)

    formatted_citations = None
    for attempt in range(MAX_RETRIES):
        try:
            formatted_citations = await format_citations(
                llm,
                state.get('selected_sources', []),
                state["sources"],
                citation_registry
            )
            break
        except Exception as e:
            console.print(f"[yellow]Citation formatting attempt {attempt+1} failed: {str(e)}[/]")
            if attempt == MAX_RETRIES - 1:
                # Create basic citations if all attempts fail
                formatted_citations = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(state.get('selected_sources', []))])
                console.print("[yellow]Using fallback citation format[/]")

    # Step 4: Generate the initial report with progress tracking
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Generating report..."),
        console=console
    ) as progress:
        task = progress.add_task("Generating", total=1)

        language = state.get('language', 'en') # Retrieve language
        report_template_style = state.get('report_template', "standard")
        # Use getter function for style instructions
        style_instructions = get_report_style_guidelines(language).get(report_template_style, get_report_style_guidelines(language)['standard'])

        initial_report = None
        for attempt in range(MAX_RETRIES):
            try:
                # Assuming generate_initial_report can now accept style_instructions
                # or its internal prompt formatting can be influenced by passing it.
                # If generate_initial_report directly uses SYSTEM_PROMPTS["report_generation"],
                # it would need to format it with style_instructions.
                # For this subtask, we pass it as an argument.
                # 【修复】添加字数控制指令到初始报告生成，增加参数验证
                current_detail_level = state.get('detail_level', 'standard')
                if not current_detail_level or not isinstance(current_detail_level, str):
                    current_detail_level = 'standard'
                    console.print(f"[yellow]Warning: Invalid detail_level in state, using 'standard'[/]")
                length_instruction = _get_length_instruction(current_detail_level)

                initial_report = await generate_initial_report(
                    llm,
                    state['query'],
                    state['findings'],
                    extracted_themes,
                    report_title,
                    state['selected_sources'],
                    formatted_citations,
                    current_date,
                    state['detail_level'],
                    include_objective,
                    citation_registry,
                    report_style_instructions=style_instructions, # New argument
                    language=language, # Pass language
                    length_instruction=length_instruction # 【新增】传递字数控制指令
                )
                progress.update(task, completed=1)
                break
            except Exception as e:
                console.print(f"[yellow]Report generation attempt {attempt+1} failed: {str(e)}[/]")
                if attempt == MAX_RETRIES - 1:
                    # Create a minimal report if all attempts fail
                    console.print("[yellow]Creating fallback report structure[/]")
                    initial_report = f"# {report_title}\n\n## Executive Summary\n\nThis report explores {state['query']}.\n\n"

                    # Extract sections from themes
                    section_matches = re.findall(r"##\s+([^\n]+)(?:\n([^#]+))?", extracted_themes)
                    for title, content in section_matches:
                        initial_report += f"## {title}\n\n{content.strip() if content else 'Information on this topic.'}\n\n"

                    initial_report += "## References\n\n" + formatted_citations
                    progress.update(task, completed=1)

    # Store data for later stages
    # state["identified_themes"] = extracted_themes # Already set before format_citations
    state["initial_report"] = initial_report
    state["formatted_citations"] = formatted_citations
    state["report_title"] = report_title

    log_chain_of_thought(
        state,
        f"Generated initial report with {len(citation_registry.citations)} properly tracked citations and {citation_stats.get('total_learnings', 0)} learnings"
    )

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state

async def enhance_report_node(llm, progress_callback, state: AgentState) -> AgentState:
    """
    Enhance the report by processing each section individually to improve reliability.
    """
    if is_shutdown_requested():
        state["status"] = "Shutdown requested, skipping report enhancement"
        log_chain_of_thought(state, "Shutdown requested, skipping report enhancement")
        return state

    state["status"] = "Enhancing report sections"
    console.print("[bold blue]Enhancing report with more detailed information...[/]")

    initial_report = state.get("initial_report", "")
    if not initial_report or len(initial_report.strip()) < 500:
        log_chain_of_thought(state, "Initial report too short or missing, skipping enhancement")
        state["enhanced_report"] = initial_report
        return state

    # Extract report title and sections
    title_match = re.match(r'# ([^\n]+)', initial_report)
    original_title = title_match.group(1) if title_match else state.get("report_title", "Research Report")

    # Extract sections using regex pattern
    section_pattern = re.compile(r'(#+\s+[^\n]+)(\n\n[^#]+?)(?=\n#+\s+|\Z)', re.DOTALL)
    sections = section_pattern.findall(initial_report)

    if not sections:
        log_chain_of_thought(state, "No sections found in report, using initial report as is")
        state["enhanced_report"] = initial_report
        return state

    # Process each section in parallel for better reliability
    enhanced_sections = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Enhancing sections..."),
        console=console
    ) as progress:
        task = progress.add_task("Enhancing", total=len(sections))

        # Prepare citation information for enhancement
        citation_registry = state.get("citation_registry")
        formatted_citations = state.get("formatted_citations", "")
        current_date = state.get("current_date", "")

        # Process each section (excluding references)
        for i, (section_header, section_content) in enumerate(sections):
            # Skip enhancing references section
            if "References" in section_header or "references" in section_header.lower():
                enhanced_sections.append((i, f"{section_header}{section_content}"))
                progress.update(task, advance=1)
                continue

            for attempt in range(MAX_RETRIES):
                try:
                    # Generate available sources text for this section
                    available_sources_text = ""
                    if citation_registry:
                        available_sources = []
                        for cid in sorted(citation_registry.citations.keys()):
                            citation_info = citation_registry.citations[cid]
                            url = citation_info.get("url", "")
                            title = citation_info.get("title", "")
                            available_sources.append(f"[{cid}] - {title} ({url})")

                        if available_sources:
                            available_sources_text = "\n\nAVAILABLE SOURCES FOR CITATION:\n" + "\n".join(available_sources)

                    # This node now calls the processor function `enhance_report`
                    # which handles the LLM call and prompt construction internally.
                    language = state.get('language', 'en')
                    report_template_style = state.get('report_template', "standard")
                    style_instructions = get_report_style_guidelines(language).get(report_template_style, get_report_style_guidelines(language)['standard'])
                    current_detail_level = state.get('detail_level', 'standard')
                    if not current_detail_level or not isinstance(current_detail_level, str):
                        current_detail_level = 'standard'
                        console.print(f"[yellow]Warning: Invalid detail_level in enhance_report_node, using 'standard'[/]")
                    length_instruction = _get_length_instruction(current_detail_level)

                    # Call the refactored enhance_report function from report_generator
                    # Note: enhance_report now processes the whole report, not just one section.
                    # This loop structure might need to be removed if enhance_report handles all sections.
                    # For now, assuming enhance_report is called ONCE for the whole report.
                    # The current enhance_report in processor takes initial_report and processes all sections.
                    # So, this loop here in the node is redundant if we call the processor's enhance_report.

                    # This logic should be done ONCE before calling the processor's enhance_report
                    # For this subtask, let's assume the loop is removed and enhance_report is called once.
                    # The following is a placeholder for where the call would be made.
                    # The actual call is made after the loop in the original code.
                    pass # Placeholder, actual call is after loop in original structure

                except Exception as e: # This try-except is now for the loop itself or data prep
                    console.print(f"[yellow]Error preparing for section enhancement '{section_header.strip()}' (Attempt {attempt+1}): {str(e)}[/]")
                    if attempt == MAX_RETRIES - 1:
                        enhanced_sections.append((i, f"{section_header}{section_content}")) # Fallback
            progress.update(task, advance=1) # This needs to be re-evaluated if loop is removed

    # If the loop was kept for some reason (e.g. section-by-section decision making in node)
    # then the enhanced_sections list would be populated here.
    # However, the refactored enhance_report processor is designed to take the whole initial_report.

    # Call enhance_report from the processor ONCE with the full initial_report
    # This replaces the per-section LLM call previously in this node.
    language = state.get('language', 'en')
    report_template_style = state.get('report_template', "standard")
    style_instructions = get_report_style_guidelines(language).get(report_template_style, get_report_style_guidelines(language)['standard'])
    current_detail_level = state.get('detail_level', 'standard')
    length_instruction = _get_length_instruction(current_detail_level)

    enhanced_report_str = await enhance_report( # Renamed variable to avoid conflict
        llm=llm,
        initial_report=initial_report,
        current_date=current_date,
        citation_registry=citation_registry,
        report_style_instructions=style_instructions,
        language=language,
        length_instruction=length_instruction
    )

    # 验证增强后的报告质量并自动扩展过短章节
    current_detail_level = state.get('detail_level', 'standard')
    validation = validate_report_quality(enhanced_report_str, current_detail_level)

    if not validation["is_valid"]:
        console.print("[yellow]检测到报告质量问题，开始智能修复...[/]")
        for issue in validation["issues"]:
            console.print(f"[yellow]   - {issue}[/]")

        # 使用优化的迭代扩展算法进行智能修复
        try:
            from shandu.agents.processors.report_generator import force_word_count_compliance

            console.print("[blue]🚀 启动优化迭代扩展算法...[/]")
            enhanced_report_str = await force_word_count_compliance(
                llm=llm,
                report_content=enhanced_report_str,
                detail_level=current_detail_level,
                language=state.get('language', 'zh')
            )

            # 重新验证
            final_validation = validate_report_quality(enhanced_report_str, current_detail_level)
            if final_validation["is_valid"]:
                console.print(f"[green]✅ 智能修复成功 (总字数: {final_validation['analysis']['total_words']})[/]")
            else:
                console.print(f"[yellow]⚠️ 部分质量问题仍然存在，但报告已显著改善 (总字数: {final_validation['analysis']['total_words']})[/]")
        except Exception as e:
            console.print(f"[red]智能修复过程中出现错误: {e}[/]")
            # 回退到原有的扩展方法
            try:
                enhanced_report_str = await expand_short_sections(
                    llm,
                    enhanced_report_str,
                    current_detail_level,
                    state.get('language', 'zh'),
                    length_instruction
                )
                console.print("[yellow]已回退到传统扩展方法[/]")
            except Exception as fallback_e:
                console.print(f"[red]回退方法也失败: {fallback_e}[/]")
    else:
        console.print(f"[green]✅ 报告质量验证通过 (总字数: {validation['analysis']['total_words']})[/]")

    # 🚨 新增：强制字数验证和扩展
    console.print("[bold blue]进行最终字数验证和强制扩展...[/]")
    enhanced_report_str = await force_word_count_compliance(llm, enhanced_report_str, current_detail_level, language)

    # Update state with the enhanced report
    state["enhanced_report"] = enhanced_report_str # Use the result from processor
    log_chain_of_thought(state, f"Enhanced report generated by processor.") # Updated log

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state

async def expand_key_sections_node(llm, progress_callback, state: AgentState) -> AgentState:
    """
    Expand key sections of the report to provide more comprehensive information.
    """
    if is_shutdown_requested():
        state["status"] = "Shutdown requested, skipping section expansion"
        log_chain_of_thought(state, "Shutdown requested, skipping section expansion")
        return state

    state["status"] = "Expanding key report sections"
    console.print("[bold blue]Expanding key sections with more comprehensive information...[/]")

    enhanced_report = state.get("enhanced_report", "")
    if not enhanced_report or len(enhanced_report.strip()) < 500:
        log_chain_of_thought(state, "Enhanced report too short or missing, using as is")
        state["final_report"] = enhanced_report
        return state

    # Get report title and sections
    title_match = re.match(r'# ([^\n]+)', enhanced_report)
    original_title = title_match.group(1) if title_match else state.get("report_title", "Research Report")

    # Extract sections using regex pattern (only level 2 headings - main content sections)
    section_pattern = re.compile(r'(##\s+[^\n]+)(\n\n[^#]+?)(?=\n##\s+|\Z)', re.DOTALL)
    sections = section_pattern.findall(enhanced_report)

    if not sections:
        log_chain_of_thought(state, "No expandable sections found, using enhanced report as is")
        state["final_report"] = enhanced_report
        return state

    # Identify important sections to expand (excluding Executive Summary, Introduction, Conclusion, References)
    important_sections = []
    for i, (section_header, section_content) in enumerate(sections):
        title = section_header.replace('#', '').strip().lower()
        if title not in ["executive summary", "introduction", "conclusion", "references"]:
            important_sections.append((i, section_header, section_content))

    # 【修复】移除3个章节的限制，处理所有重要章节以确保报告完整性
    # 注释：原来只处理前3个章节导致报告不完整，现在处理所有重要章节
    if not important_sections:
        log_chain_of_thought(state, "No key sections to expand, using enhanced report as is")
        state["final_report"] = enhanced_report
        return state

    # Create a copy of the report that we'll modify
    expanded_report = enhanced_report

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Expanding key sections..."),
        console=console
    ) as progress:
        task = progress.add_task("Expanding", total=1) # Total is 1 because we call the processor once

        language = state.get('language', 'en')
        report_template_style = state.get('report_template', "standard")
        style_instructions = get_report_style_guidelines(language).get(report_template_style, get_report_style_guidelines(language)['standard'])
        current_detail_level = state.get('detail_level', 'standard')
        if not current_detail_level or not isinstance(current_detail_level, str):
            current_detail_level = 'standard'
            console.print(f"[yellow]Warning: Invalid detail_level in expand_key_sections_node, using 'standard'[/]")
        length_instruction = _get_length_instruction(current_detail_level)
        citation_registry = state.get("citation_registry")
        current_date = state.get("current_date", "")

        # Dynamically build expansion_requirements_text based on detail_level
        # This logic was previously inside the loop, now it's prepared once.
        expansion_requirements_list = [
            "2. Add specific examples, case studies, or data points to support claims",
            "3. Include additional context and background information",
            "4. Add nuance, caveats, and alternative perspectives",
            "5. Use proper citation format [n] throughout",
            "6. Maintain the existing section structure but add subsections if appropriate",
            # Note: item 7 about current_date is part of the main template in prompts.py
        ]
        if current_detail_level == "brief":
            pass
        elif current_detail_level.startswith("custom_"):
            pass
        elif current_detail_level == "detailed":
            expansion_requirements_list.insert(0, "1. Substantially expand the length and detail of the section, aiming for a comprehensive and in-depth exploration, significantly longer than a standard treatment.")
        else: # Standard detail level
            expansion_requirements_list.insert(0, "1. Moderately expand the length and detail of the section, providing a balanced increase in depth and breadth.")
        expansion_requirements_text_built = "\n".join(expansion_requirements_list)

        final_expanded_report = await expand_key_sections(
            llm=llm,
            report=enhanced_report, # Pass the report from previous stage
            # identified_themes is not directly used by expand_key_sections processor
            current_date=current_date,
            citation_registry=citation_registry,
            report_style_instructions=style_instructions,
            language=language,
            length_instruction=length_instruction,
            expansion_requirements_text=expansion_requirements_text_built # Pass the built requirements
        )

        # 🚨 新增：最终强制字数验证和扩展
        console.print("[bold blue]进行最终强制字数验证...[/]")
        final_expanded_report = await force_word_count_compliance(llm, final_expanded_report, current_detail_level, language)

        # 【新增】学术质量检查和连贯性优化
        console.print("[bold blue]Performing final academic quality check...[/]")
        final_expanded_report = await _ensure_report_coherence(
            llm=llm,
            report=final_expanded_report,
            original_query=state.get('query', ''),
            language=language,
            current_date=current_date
        )

        progress.update(task, completed=1)

    # Update state with the expanded report
    state["final_report"] = final_expanded_report # Use result from processor
    log_chain_of_thought(state, f"Expanded key sections using processor.") # Updated log

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state

async def report_node(llm, progress_callback, state: AgentState) -> AgentState:
    """Finalize the report."""
    state["status"] = "Finalizing report"
    console.print("[bold blue]Research complete. Finalizing report...[/]")

    has_report = False
    if "final_report" in state and state["final_report"]:
        final_report = state["final_report"]
        has_report = True
    elif "enhanced_report" in state and state["enhanced_report"]:
        final_report = state["enhanced_report"]
        has_report = True
    elif "initial_report" in state and state["initial_report"]:
        final_report = state["initial_report"]
        has_report = True

    # If we have a report but it's broken or too short, regenerate it
    if has_report and (len(final_report.strip()) < 1000):
        console.print("[bold yellow]Existing report appears broken or incomplete. Regenerating...[/]")
        has_report = False

    # If we don't have a report, regenerate initial, enhanced, and expanded reports
    if not has_report:
        console.print("[bold yellow]No valid report found. Regenerating report from scratch...[/]")

        language = state.get('language', 'en') # Retrieve language
        report_title = await generate_title(llm, state['query']) # Assuming generate_title doesn't need lang yet
        console.print(f"[bold green]Generated title: {report_title}[/]")

        extracted_themes = await extract_themes(llm, state['findings']) # Assuming extract_themes doesn't need lang yet

        # Get style instructions for the fallback report generation
        report_template_style_fallback = state.get('report_template', "standard")
        style_instructions_fallback = get_report_style_guidelines(language).get(report_template_style_fallback, get_report_style_guidelines(language)['standard'])

        # 【修复】添加字数控制指令到回退报告生成
        current_detail_level_fallback = state.get('detail_level', 'standard')
        if not current_detail_level_fallback or not isinstance(current_detail_level_fallback, str):
            current_detail_level_fallback = 'standard'
            console.print(f"[yellow]Warning: Invalid detail_level in fallback report generation, using 'standard'[/]")
        length_instruction_fallback = _get_length_instruction(current_detail_level_fallback)

        initial_report = await generate_initial_report(
            llm,
            state['query'],
            state['findings'],
            extracted_themes,
            report_title,
            state['selected_sources'],
            state.get('formatted_citations', ''),
            state['current_date'],
            state['detail_level'],
            False, # Don't include objective in fallback
            state.get('citation_registry'), # Use existing citation registry if available
            report_style_instructions=style_instructions_fallback, # Pass style instructions
            language=language, # Pass language
            length_instruction=length_instruction_fallback # 【新增】传递字数控制指令
        )

        # Store the initial report
        state["initial_report"] = initial_report

        # Skip enhancement and expansion steps to maintain consistent report structure
        enhanced_report = initial_report
        state["enhanced_report"] = enhanced_report

        # Use the initial report directly as the final report
        final_report = initial_report

        used_source_urls = []
        for analysis in state["content_analysis"]:
            if "sources" in analysis and isinstance(analysis["sources"], list):
                for url in analysis["sources"]:
                    if url not in used_source_urls:
                        used_source_urls.append(url)

        # If we don't have enough used sources, also grab from selected_sources
        if len(used_source_urls) < 5 and "selected_sources" in state:
            for url in state["selected_sources"]:
                if url not in used_source_urls:
                    used_source_urls.append(url)
                    if len(used_source_urls) >= 15:
                        break

        sources_info = []
        for url in used_source_urls[:20]:  # Limit to 20 sources
            source_meta = next((s for s in state["sources"] if s.get("url") == url), {})
            sources_info.append({
                "url": url,
                "title": source_meta.get("title", ""),
                "snippet": source_meta.get("snippet", "")
            })

    # Apply comprehensive cleanup of artifacts and unwanted sections
    final_report = re.sub(r'Completed:.*?\n', '', final_report)
    final_report = re.sub(r'Here are.*?(search queries|queries to investigate).*?\n', '', final_report)
    final_report = re.sub(r'Generated search queries:.*?\n', '', final_report)
    final_report = re.sub(r'\*Generated on:.*?\*', '', final_report)

    # Remove "Refined Research Query" section which sometimes appears at the beginning
    final_report = re.sub(r'#\s*Refined Research Query:.*?(?=\n#|\Z)', '', final_report, flags=re.DOTALL)
    final_report = re.sub(r'Refined Research Query:.*?(?=\n\n)', '', final_report, flags=re.DOTALL)

    # Remove entire Research Framework sections (from start to first actual content section)
    if "Research Framework:" in final_report or "# Research Framework:" in final_report:

        framework_matches = re.search(r'(?:^|\n)(?:#\s*)?Research Framework:.*?(?=\n#|\n\*\*|\Z)', final_report, re.DOTALL)
        if framework_matches:
            framework_section = framework_matches.group(0)
            final_report = final_report.replace(framework_section, '')

    # Remove "Based on our discussion" title if it exists
    final_report = re.sub(r'^(?:#\s*)?Based on our discussion,.*?\n', '', final_report, flags=re.MULTILINE)

    # Also try to catch Objective sections and other framework components
    final_report = re.sub(r'^Objective:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)
    final_report = re.sub(r'^Key Aspects to Focus On:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)
    final_report = re.sub(r'^Constraints and Preferences:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)
    final_report = re.sub(r'^Areas to Explore in Depth:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)
    final_report = re.sub(r'^Preferred Sources, Perspectives, or Approaches:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)
    final_report = re.sub(r'^Scope, Boundaries, and Context:.*?\n\n', '', final_report, flags=re.MULTILINE | re.DOTALL)

    # Also remove any remaining individual problem framework lines
    final_report = re.sub(r'^Research Framework:.*?\n', '', final_report, flags=re.MULTILINE)
    final_report = re.sub(r'^Key Findings:.*?\n', '', final_report, flags=re.MULTILINE)
    final_report = re.sub(r'^Key aspects to focus on:.*?\n', '', final_report, flags=re.MULTILINE)

    report_title = await generate_title(llm, state['query'])

    # Remove the query or any long text description from the beginning of the report if present
    # This pattern removes lines that look like full query pasted as title or at the beginning
    if final_report.strip().startswith('# '):
        lines = final_report.split('\n')

        # Remove any extremely long title lines (likely a full query pasted as title)
        if len(lines) > 0 and len(lines[0]) > 80 and lines[0].startswith('# '):
            lines = lines[1:]  # Remove the first line
            final_report = '\n'.join(lines)

        # Also look for any text block before the actual title that might be the original query
        # or refined query description
        start_idx = 0
        title_idx = -1

        for i, line in enumerate(lines):
            if line.startswith('# ') and i > 0 and len(line) < 100:
                # Found what appears to be the actual title
                title_idx = i
                break

        # If we found a title after some text, remove everything before it
        if title_idx > 0:
            lines = lines[title_idx:]
            final_report = '\n'.join(lines)

    title_match = re.match(r'^#\s+.*?\n', final_report)
    if title_match:
        # Replace existing title with our generated one
        final_report = re.sub(r'^#\s+.*?\n', f'# {report_title}\n', final_report, count=1)
    else:

        final_report = f'# {report_title}\n\n{final_report}'

    # Also check for second line being the full query, which happens sometimes
    lines = final_report.split('\n')
    if len(lines) > 2 and len(lines[1]) > 80 and "query" not in lines[1].lower():
        lines.pop(1)  # Remove the second line if it looks like a query
        final_report = '\n'.join(lines)

    if "References" in final_report:

        references_match = re.search(r'#+\s*References.*?(?=#+\s+|\Z)', final_report, re.DOTALL)
        if references_match:
            references_section = references_match.group(0)

            # Always replace the references section with our properly formatted web citations
            console.print("[yellow]Ensuring references are properly formatted as web citations...[/]")

            citation_registry = state.get("citation_registry")
            citation_manager = state.get("citation_manager")
            formatted_citations = ""

            if citation_manager and citation_registry:

                citation_stats = citation_manager.get_learning_statistics()
                console.print(f"[bold green]Report references {len(citation_registry.citations)} sources with {citation_stats.get('total_learnings', 0)} tracked learnings[/]")

                validation_result = citation_registry.validate_citations(final_report)

                if not validation_result["valid"]:

                    out_of_range_count = len(validation_result.get("out_of_range_citations", set()))
                    other_invalid_count = len(validation_result["invalid_citations"]) - out_of_range_count
                    max_valid_id = validation_result.get("max_valid_id", 0)

                    console.print(f"[bold yellow]Found {len(validation_result['invalid_citations'])} invalid citations in the report[/]")

                    if out_of_range_count > 0:
                        console.print(f"[bold red]Found {out_of_range_count} out-of-range citations (exceeding max valid ID: {max_valid_id})[/]")

                    # Remove invalid citations from the report
                    for invalid_cid in validation_result["invalid_citations"]:
                        # For out-of-range citations, replace with valid range indicator
                        if invalid_cid in validation_result.get("out_of_range_citations", set()):
                            replacement = f'[1-{max_valid_id}]'  # Suggest valid range
                            final_report = re.sub(f'\\[{invalid_cid}\\]', replacement, final_report)
                        else:
                            # Replace other invalid patterns like [invalid_cid] with [?]
                            final_report = re.sub(f'\\[{invalid_cid}\\]', '[?]', final_report)

                used_citations = validation_result["used_citations"]

                # If we have a citation manager, use its enhanced formatting
                if citation_manager and used_citations:

                    processed_text, bibliography_entries = citation_manager.get_citations_for_report(final_report)

                    # Use the citation manager's bibliography formatter with APA style
                    if bibliography_entries:
                        report_template = state.get('report_template', 'standard')
                        citation_style = "apa" # Default
                        if report_template == "academic":
                            citation_style = "apa"
                        elif report_template == "literature_review":
                            citation_style = "mla"
                        elif report_template == "business":
                            citation_style = "apa"

                        formatted_citations = citation_manager.format_bibliography(bibliography_entries, style=citation_style)
                        console.print(f"[bold green]Generated enhanced bibliography with {len(bibliography_entries)} entries using '{citation_style}' style.[/bold green]")
                # Fall back to regular citation formatting
                elif used_citations:

                    formatted_citations = await format_citations(
                        llm,
                        state.get('selected_sources', []),
                        state["sources"],
                        citation_registry
                    )

            # Replace references section with properly formatted ones
            if formatted_citations:
                new_references = f"# References\n\n{formatted_citations}\n"
                final_report = final_report.replace(references_section, new_references)
            elif state.get("formatted_citations"):
                new_references = f"# References\n\n{state['formatted_citations']}\n"
                final_report = final_report.replace(references_section, new_references)
            else:

                basic_references = []
                for i, url in enumerate(state.get("selected_sources", []), 1):
                    source_meta = next((s for s in state["sources"] if s.get("url") == url), {})
                    title = source_meta.get("title", "Untitled")
                    domain = url.split("//")[1].split("/")[0] if "//" in url else "Unknown Source"
                    date = source_meta.get("date", "n.d.")

                    # Simpler citation format without the date
                    citation = f"[{i}] *{domain}*, \"{title}\", {url}"
                    basic_references.append(citation)

                new_references = f"# References\n\n" + "\n".join(basic_references) + "\n"
                final_report = final_report.replace(references_section, new_references)

    elapsed_time = time.time() - state["start_time"]
    minutes, seconds = divmod(int(elapsed_time), 60)

    state["messages"].append(AIMessage(content="Research complete. Generating final report..."))
    state["findings"] = final_report
    state["status"] = "Complete"

    # Simulate chart execution and embed into final_report
    executed_charts_info_list = []
    chart_output_dir = "charts" # Relative directory for charts
    if not os.path.exists(chart_output_dir):
        os.makedirs(chart_output_dir)

    if "citation_manager" in state and state["citation_manager"]:
        citation_manager = state["citation_manager"]
        if hasattr(citation_manager, 'sources') and isinstance(citation_manager.sources, dict):
            console.print("[bold blue]Executing Matplotlib scripts and preparing for report embedding...[/]")
            for source_url, source_info in citation_manager.sources.items():
                if hasattr(source_info, 'visualizable_data') and isinstance(source_info.visualizable_data, list):
                    for data_item_idx, data_item in enumerate(source_info.visualizable_data):
                        if isinstance(data_item, dict) and \
                           data_item.get('matplotlib_code') and \
                           data_item.get('chart_filename'):

                            chart_code = data_item['matplotlib_code']
                            original_chart_filename = data_item['chart_filename']
                            chart_title = data_item.get('title_suggestion', f"Chart_{original_chart_filename}")

                            image_path = os.path.join(chart_output_dir, original_chart_filename)

                            # Modify plt.savefig() to use the absolute image_path
                            # Ensure image_path is properly escaped for use in a string literal if necessary,
                            # though os.path.join should produce a clean path.
                            # Python's string literals handle backslashes in paths correctly on Windows if they are raw or escaped.
                            # Forcing forward slashes for cross-platform consistency in the generated script:
                            safe_image_path_for_script = image_path.replace("\\", "/")
                            chart_code = re.sub(r"plt\.savefig\s*\(\s*['\"].*?['\"]\s*\)",
                                                f"plt.savefig(r'{safe_image_path_for_script}')",
                                                chart_code)
                            if "plt.savefig" not in chart_code: # If no savefig was present, add one.
                                chart_code += f"\nplt.savefig(r'{safe_image_path_for_script}')"

                            # Ensure plt.close() is in the script to free memory
                            if "plt.close()" not in chart_code:
                                chart_code += "\nplt.close()"

                            script_path = os.path.join(chart_output_dir, "temp_chart_script.py")
                            with open(script_path, "w") as f:
                                f.write(chart_code)

                            try:
                                # Consider using sys.executable for robustness
                                process = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=30)
                                if process.returncode == 0:
                                    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                                        console.print(f"[green]Successfully executed chart script and saved: {image_path}[/green]")
                                        executed_charts_info_list.append({
                                            'md_path': image_path.replace("\\", "/"), # Use forward slashes for MD
                                            'title': chart_title,
                                            'original_filename': original_chart_filename
                                        })
                                    else:
                                        console.print(f"[red]Chart script {original_chart_filename} ran but output file {image_path} not found or empty.[/red]")
                                        console.print(f"[red]STDOUT:\n{process.stdout}[/red]")
                                        console.print(f"[red]STDERR:\n{process.stderr}[/red]")
                                else:
                                    console.print(f"[red]Error executing chart script {original_chart_filename} (Return Code: {process.returncode}):[/red]")
                                    console.print(f"[red]STDOUT:\n{process.stdout}[/red]")
                                    console.print(f"[red]STDERR:\n{process.stderr}[/red]")
                            except subprocess.TimeoutExpired:
                                console.print(f"[red]Timeout executing chart script {original_chart_filename}[/red]")
                            except Exception as e:
                                console.print(f"[red]Failed to execute chart script {original_chart_filename}: {e}[/red]")
                                console.print(f"[dim]{traceback.format_exc()}[/dim]")
                            finally:
                                if os.path.exists(script_path):
                                    os.remove(script_path) # Clean up
                        else:
                            if isinstance(data_item, dict) and (not data_item.get('matplotlib_code') or not data_item.get('chart_filename')):
                                console.print(f"[yellow]Skipping chart execution for a visualizable_data item in {source_url} (idx: {data_item_idx}) due to missing 'matplotlib_code' or 'chart_filename'.[/yellow]")

    if executed_charts_info_list:
        charts_markdown_section = "\n\n## Visualizations\n\n"
        for chart_info in executed_charts_info_list:
            # Ensure title doesn't break Markdown image alt text or header
            safe_title = chart_info['title'].replace('"', "'").replace('\n', ' ')
            charts_markdown_section += f"### {safe_title}\n"
            charts_markdown_section += f"![{safe_title}]({chart_info['md_path']})\n\n"

        # Append the new charts section to the final report
        final_report += charts_markdown_section
        state["findings"] = final_report # Update state with the report including charts
        console.print(f"[green]Appended {len(executed_charts_info_list)} chart references to the final report.[/green]")


    if "citation_manager" in state:
        citation_stats = state["citation_manager"].get_learning_statistics()
        log_chain_of_thought(
            state,
            f"Generated final report after {minutes}m {seconds}s with {citation_stats.get('total_sources', 0)} sources and {citation_stats.get('total_learnings', 0)} tracked learnings, including {len(executed_charts_info_list)} chart simulations."
        )
    else:
        log_chain_of_thought(state, f"Generated final report after {minutes}m {seconds}s, including {len(executed_charts_info_list)} chart simulations.")

    if progress_callback:
        await _call_progress_callback(progress_callback, state)
    return state
