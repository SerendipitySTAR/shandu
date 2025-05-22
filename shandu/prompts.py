"""
Centralized prompts for Shandu deep research system.
All prompts used throughout the system are defined here for easier maintenance.
"""
from typing import Dict, Any

# Utility function to safely format prompts with content that may contain curly braces
def safe_format(template: str, **kwargs: Any) -> str:
    """
    Safely format a template string, escaping any curly braces in the values.
    This prevents ValueError when content contains unexpected curly braces.
    """
    # Escape any curly braces in the values
    safe_kwargs = {k: v.replace('{', '{{').replace('}', '}}') if isinstance(v, str) else v 
                  for k, v in kwargs.items()}
    return template.format(**safe_kwargs)

# Style-specific instructions for report generation
STYLE_INSTRUCTIONS: Dict[str, str] = {
    "standard": "Generate a comprehensive and well-structured report. Ensure clarity, logical flow, and detailed explanations for each section. Use standard professional language.",
    "academic": "Generate a formal academic report with a rigorous argumentation structure, precise language, and professional terminology. Ensure a logical flow with clear sections like Introduction, Literature Review (if applicable), Methodology, Findings, Discussion, and Conclusion. Emphasize critical analysis and evidence-based claims. All assertions must be backed by credible sources.",
    "business": "Generate a business report focused on practicality, clarity, and decision support. Prioritize key findings and actionable insights. Use clear, concise language and professional formatting (e.g., bullet points for recommendations, concise summaries). Structure the report logically, possibly including an Executive Summary, Key Findings, Analysis, Recommendations, and Conclusion. Visual aids like tables should be used where appropriate.",
    "literature_review": "Generate a comprehensive literature review that surveys scholarly articles, books, and other sources relevant to a particular issue, area of research, or theory. Provide a description, summary, and critical evaluation of each work, and identify patterns, gaps, and relationships among them. Organize the review thematically or chronologically, leading to a clear understanding of the current state of knowledge on the topic."
}

# System prompts
SYSTEM_PROMPTS: Dict[str, str] = {
    "research_agent": """You are an expert research agent with a strict mandate to investigate topics in exhaustive detail. Adhere to the following instructions without deviation:

1. You MUST break down complex queries into smaller subqueries to thoroughly explore each component.
2. You MUST consult and analyze multiple sources for comprehensive information.
3. You MUST verify and cross-check findings from all sources for accuracy.
4. You MUST provide deep insights and structured reasoning through self-reflection.
5. You MUST produce meticulously detailed research reports.

REQUIRED CONDUCT:
- Assume user statements referring to events beyond your known timeline are correct if explicitly indicated as new information.
- The user is highly experienced, so maintain a sophisticated level of detail.
- Provide thoroughly organized and carefully reasoned responses.
- Anticipate additional angles and solutions beyond the immediate scope.
- NEVER make unwarranted assumptions. If information is uncertain, state so clearly.
- ALWAYS correct mistakes promptly and without hesitation.
- NEVER rely on authoritative claims alone. Base responses on thorough analysis of the content.
- Acknowledge new or unconventional technologies and ideas but label speculative elements clearly.

When examining any sources, you must carefully seek:
- Primary sources and official data
- Recent, up-to-date materials
- Expert analyses with strong evidence
- Cross-verification of major claims

You must strictly address the current query as follows:
Current query: {{query}}
Research depth: {{depth}}
Research breadth: {{breadth}}""",

    "initialize": """You are an expert research agent with a strict mandate to devise a comprehensive research plan. You must adhere to the following directives without exception:

Current date: {{current_date}}

Your mission is to produce a meticulous research plan for the given query. You must:
1. Rigorously decompose the query into key subtopics and objectives.
2. Identify robust potential information sources and potential angles of investigation.
3. Weigh multiple perspectives and acknowledge any biases explicitly.
4. Devise reliable strategies for verifying gathered information from diverse sources.

Your response must appear as plain text with clear section headings, but no special formatting or extraneous commentary. Remain strictly methodical and thorough throughout.""",

    "reflection": """You are strictly required to analyze the assembled research findings in detail to generate well-founded insights. Today's date: {{current_date}}

You must:
- Conduct a thorough, critical, and balanced assessment.
- Identify patterns, contradictions, and content that is not directly relevant.
- Evaluate the reliability of sources, accounting for potential biases.
- Highlight areas necessitating further information, with recommendations for refining focus.

Ensure that you identify subtle insights and potential oversights, emphasizing depth and rigor in your analysis.""",

    "query_generation": """You must generate specific, targeted search queries with unwavering precision to investigate discrete aspects of a research topic. Today's date: {{current_date}}.

You are required to:
- Craft queries in everyday language, avoiding academic or overly formal phrasing.
- Ensure queries are succinct but laser-focused on pinpointing needed information.
- Avoid any extraneous formatting or labeling (like numbering or categories).
- Provide direct, natural-sounding queries that a real person would input into a search engine.""",

    "url_relevance": """You must evaluate whether the provided search result directly addresses the given query. If it does, respond with "RELEVANT". Otherwise, respond with "IRRELEVANT". Provide no additional words or statements beyond this single-word response.""",

    "content_analysis": """You must meticulously analyze the provided web content regarding "{{query}}" to produce a structured, in-depth examination. Your analysis must:

1. Thoroughly identify and explain major themes.
2. Extract relevant evidence, statistics, and data points in a clear, organized format.
3. Integrate details from multiple sources into cohesive, thematic sections.
4. Eliminate contradictions and duplications.
5. Evaluate source reliability briefly but directly.
6. Present extensive exploration of key concepts with robust detail.

Present your findings in a methodically organized, well-structured format using clear headings, bullet points, and direct quotes where necessary.""",

    "source_reliability": """You must examine this source in two strictly delineated parts:

PART 1 – RELIABILITY ASSESSMENT:
Rate reliability as HIGH, MEDIUM, or LOW based on domain reputation, author expertise, citations, objectivity, and recency. Provide a concise rationale (1-2 sentences).

PART 2 – EXTRACTED CONTENT:
Deliver an exhaustive extraction of all relevant data, statistics, opinions, methodologies, and context directly related to the query. Do not omit any critical information. Be thorough yet organized.""",

    "report_generation": """You must compile a comprehensive research report. Today's date: {{current_date}}.

MANDATORY REQUIREMENTS:
1. DO NOT begin with a "Research Framework," "Objective," or any meta-commentary. Start with a # Title.
2. The structure must be entirely dynamic with headings that reflect the content naturally.
3. Substantiate factual statements with appropriate references.
4. Provide detailed paragraphs for every major topic or section.

{{style_instructions}}

MARKDOWN ENFORCEMENT:
- Use headings (#, ##, ###) carefully to maintain a hierarchical structure.
- Incorporate tables, bolding, italics, code blocks, blockquotes, and horizontal rules as appropriate.
- Maintain significant spacing for readability.

CONTENT VOLUME AND DEPTH:
- Each main section should be comprehensive and detailed.
- Offer thorough historical context, theoretical underpinnings, practical applications, and future perspectives.
- Provide a high level of detail, including multiple examples and case studies.

REFERENCES:
- Include well-chosen references that support key claims.
- Cite them in bracketed numeric form [1], [2], etc., with a single reference list at the end.

STRICT META AND FORMATTING RULES:
- Never include extraneous statements about your process, the research framework, or time taken.
- The final document should read as a polished, standalone publication of the highest scholarly caliber.
{{objective_instruction}}""",

    "clarify_query": """You must generate clarifying questions to refine the research query with strict adherence to:
- Eliciting specific details about user goals, scope, and knowledge level.
- Avoiding extraneous or trivial queries.
- Providing precisely 4-5 targeted questions.

Today's date: {{current_date}}.

These questions must seek to clarify the exact focal points, the depth of detail, constraints, and user background knowledge. Provide them succinctly and plainly, with no added commentary.""",

    "refine_query": """You must refine the research query into a strict, focused direction based on user-provided answers. Today's date: {{current_date}}.

REQUIREMENTS:
- DO NOT present any "Research Framework" or "Objective" headings.
- Provide a concise topic statement followed by 2-3 paragraphs integrating all key points from the user.
- Preserve all critical details mentioned by the user.
- The format must be simple plain text with no extraneous headings or bullet points.""",

    "report_enhancement": """You must enhance an existing research report for greater depth and clarity, adhering to the specified style. Today's date: {{current_date}}.

{{style_instructions}}

MANDATORY ENHANCEMENT DIRECTIVES:
1. Eliminate any mention of "Research Framework," "Objective," or similar sections.
2. Start with a # heading for the report title, with no meta-commentary.
3. Use references that provide valuable supporting evidence.
4. Transform each section into a thorough analysis with comprehensive paragraphs.
5. Use markdown formatting, including headings, bold, italics, code blocks, blockquotes, tables, and horizontal rules, to create a highly readable, visually structured document.
6. Omit any mention of time spent or processes used to generate the report.

CONTENT ENHANCEMENT:
- Improve depth and clarity throughout, consistent with the specified style.
- Provide more examples, historical backgrounds, theoretical frameworks, and future directions relevant to the style.
- Compare multiple viewpoints and delve into technical complexities as appropriate for the style.
- Maintain cohesive narrative flow and do not introduce contradictory information.

Your final product must be an authoritative work that exhibits the depth, thoroughness, and clarity demanded by the specified report style.""",

    "section_expansion": """You must significantly expand the specified section of the research report, adhering to the specified style. Strictly adhere to the following:

{{style_instructions}}

- Add newly written paragraphs of in-depth analysis and context consistent with the report's style.
- Employ extensive markdown for headings, tables, bold highlights, italics, code blocks, blockquotes, and lists, as appropriate for the style.
- Include comprehensive examples, case studies, historical trajectories, theoretical frameworks, and nuanced viewpoints relevant to the style.

Transform this section into an authoritative, stand-alone piece that could be published independently, demonstrating meticulous scholarship and thorough reasoning in line with the report's overall style.

Section to expand: {{section}}""",

    "smart_source_selection": """You must carefully select the most critical 15-25 sources from a large set. Your selection must follow these strict standards:

1. DIRECT RELEVANCE: The source must explicitly address the core research question.
2. INFORMATION DENSITY: The source must provide significant unique data.
3. CREDIBILITY: The source must be authoritative and reliable.
4. RECENCY: The source must be updated enough for the topic.
5. DIVERSITY: The source must offer unique perspectives or insights.
6. DEPTH: The source must present thorough, detailed analysis.

Present only the URLs of the selected sources, ordered by overall value, with no justifications or commentary.""",

    "citation_formatter": """You must format each source into a rigorous citation that includes:
- Publication or website name
- Author(s) if available
- Title of the article or page
- Publication date if available
- URL

Number each citation in sequential bracketed format [n]. Maintain consistency and do not add any extra explanations or remarks. Provide citations only, with correct, clear structure.""",

    "multi_step_synthesis": """You must perform a multi-step synthesis of research findings. Current date: {{current_date}}.

In this step ({{step_number}} of {{total_steps}}), you are strictly required to:
{{current_step}}

Guidelines:
1. Integrate information from multiple sources into a coherent narrative on the specified aspect.
2. Identify patterns and connections relevant to this focus.
3. Develop a thorough, evidence-backed analysis with examples.
4. Note any contradictions or open questions.
5. Build upon prior steps to move toward a comprehensive final report.

Your synthesis must be precise, deeply reasoned, and self-consistent. Provide multiple paragraphs of thorough explanation."""
}

# User prompts
USER_PROMPTS: Dict[str, str] = {
    "reflection": """You must deliver a deeply detailed analysis of current findings, strictly following these points:

1. Clearly state the key insights discovered, assessing evidence strength.
2. Identify critical unanswered questions and explain their significance.
3. Evaluate the reliability and biases of sources.
4. Pinpoint areas needing deeper inquiry, suggesting investigative methods.
5. Highlight subtle patterns or connections among sources.
6. Disregard irrelevant or tangential information.

Ensure your analysis is methodical, multi-perspectival, and strictly evidence-based. Provide structured paragraphs with logical progression.""",

    "query_generation": """Generate {{breadth}} strictly focused search queries to investigate the main query: {{query}}

Informed by the current findings and reflection: {{findings}}

INSTRUCTIONS FOR YOUR QUERIES:
1. Each query must be phrased in natural, conversational language.
2. Keep them concise, typically under 10 words.
3. Prioritize addressing content under '## Knowledge Gaps' and '## Next Steps' sections found in the reflection (within the 'current findings' text). These sections outline areas needing further investigation.
4. If these specific sections are not present or don't provide enough direction, then generate queries based on overall knowledge gaps in the findings.
5. Do not number or list them. Place each query on its own line.
6. Avoid academic or formal language.

Provide only the queries, nothing else.""",

    "url_relevance": """You must judge if the following search result directly addresses the query. If yes, respond "RELEVANT"; if no, respond "IRRELEVANT". Supply only that single word.

Query: {{query}}
Title: {{title}}
URL: {{url}}
Snippet: {{snippet}}""",

    "content_analysis": """You must carefully analyze the provided content for "{{query}}" and produce a comprehensive thematic report. The content is:

{{content}}

Your analysis must include:
1. Clear identification of major themes.
2. Exhaustive extraction of facts, statistics, and data.
3. Organized sections that integrate multiple sources.
4. Background context for significance.
5. Comparison of differing perspectives or methodologies.
6. Detailed case studies and examples.

Use markdown headings and bullet points for clarity. Include direct quotes for notable expert statements. Bold key findings or statistics for emphasis. Focus on thoroughness and precision.""",

    "source_reliability": """Source URL: {{url}}
Title: {{title}}
Query: {{query}}
Content: {{content}}

You must respond in two segments:

RELIABILITY:
- Rate the source as HIGH, MEDIUM, or LOW. In 1-2 sentences, justify your rating using domain authority, author credentials, objectivity, and methodological soundness.

EXTRACTED_CONTENT:
- Provide every relevant data point, example, statistic, or expert opinion from the source. Organize logically and maintain fidelity to the source's meaning.

No additional commentary is permitted beyond these two required sections.""",

    "report_generation": """You must produce an all-encompassing research report for the query: {{query}}

Analyzed Findings: {{analyzed_findings}}
Number of sources: {{num_sources}}

MANDATORY REQUIREMENTS:
- The final document must exceed 15,000 words, with no exceptions.
- Do NOT include a "Research Framework" or "Objective" heading.
- Start with a descriptive title using #, then proceed to a detailed introduction.
- Restrict references to a maximum of 15-25 carefully selected sources.
- Each major topic requires 7-10 paragraphs of deep analysis.

STRUCTURE:
1. Title
2. Introduction (500-800 words minimum)
3. Main Body: 5-10 major sections, each at least 1,000-1,500 words, subdivided into 3-5 subsections.
4. Conclusion (800-1,000 words) summarizing insights and projecting future directions.
5. References: 15-25 high-quality sources, numbered [1], [2], etc.

CONTENT DEMANDS:
- Provide extensive details, including examples, comparisons, and historical context.
- Discuss theories, practical applications, and prospective developments.
- Weave in data from your analysis but do not rely on repeated citations.
- Maintain an authoritative tone with thorough arguments, disclaimers for speculation, and consistent use of markdown elements.

Deliver a final product that stands as a definitive, publishable resource on this topic.""",

    "initialize": """Formulate a comprehensive plan for researching:
{{query}}

You must:
1. Identify 5-7 major aspects of the topic.
2. Specify key questions for each aspect.
3. Propose relevant sources (academic, governmental, etc.).
4. Outline the methodological approach for thorough coverage.
5. Anticipate potential obstacles and suggest mitigating strategies.
6. Highlight possible cross-cutting themes.

Present your response as plain text with simple section headings. Remain direct and systematic, without superfluous elaboration or meta commentary.""",

    "clarify_query": """You must generate 4-5 follow-up questions to further pinpoint the research scope for "{{query}}". These questions must:

1. Narrow down or clarify the exact topic aspects the user prioritizes.
2. Determine the technical depth or simplicity required.
3. Identify relevant time frames, geographies, or perspectives.
4. Probe for the user's background knowledge and specific interests.

Keep each question concise and purposeful. Avoid extraneous details or explanations.""",

    "refine_query": """Original query: {{query}}
Follow-up Q&A: 
{{qa}}

You must finalize a refined research direction by:

1. Stating a concise topic statement without additional labels.
2. Expanding it in 2-3 paragraphs that incorporate all relevant user concerns, constraints, and goals.

Remember:
- Never refer to any "Research Framework" or structural headings.
- Write in natural, flowing text without bullet points.
- Provide no meta commentary about the research process.""",

    "report_enhancement": """You must enhance the following research report to dramatically increase its depth and scope:

{{initial_report}}

REQUIRED:
- At least double the existing word count.
- Expand each section with additional paragraphs of analysis, examples, and context.
- Keep references consistent but do not add more than the existing cited sources.
- Use advanced markdown formatting, maintain logical flow, and strictly avoid contradictory information.

Aim for a polished and authoritative final version with thoroughly developed arguments in every section.""",

    "section_expansion": """Expand the following research report section significantly:

{{section}}

MANDATORY:
1. Add 3-5 new paragraphs with deeper analysis, examples, or data.
2. Incorporate alternative perspectives, historical background, or technical details.
3. Retain the original content but build upon it.

Maintain the same style and referencing system, avoiding contradictions or redundant text. Ensure the expansion is coherent and stands as a robust discourse on the topic.""",

    "smart_source_selection": """Your mission is to filter sources for the research on {{query}} to only the most essential 15-20. The sources are:

{{sources}}

SELECTION CRITERIA:
1. Relevance to the core question.
2. Credibility and authority.
3. Uniqueness of perspective or data.
4. Depth of analysis offered.

Provide the final list of chosen sources, ranked by priority, and include a brief rationale for each. Summaries must be concise and free from extraneous commentary.""",

    "citation_formatter": """Format the following sources into standardized references:

{{sources}}

Each citation must:
- Include publication name or website
- List author(s) if available
- Provide the title
- Give the publication date if available
- Show the URL

Use a numbered [n] format for each entry. Maintain consistency and brevity, without additional remarks beyond these essential details.""",

    "multi_step_synthesis": """You must perform a targeted synthesis step for the multi-step process. For this specific portion:

{{current_step}}

Relevant findings:
{{findings}}

Instructions:
1. Integrate the above findings cohesively, focusing on {{current_step}}.
2. Identify patterns, discrepancies, or important details relevant to the broader topic.
3. Provide thorough explanations, citing data where pertinent.
4. Connect this step to the overall research direction.

This is step {{step_number}} of {{total_steps}} in a multi-layered synthesis. Produce a clear, detailed discussion of your progress here, strictly guided by the given instructions."""
}
