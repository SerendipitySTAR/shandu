"""Research module implementation."""
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import os

@dataclass
class ResearchResult:
    """Container for research results with enhanced citation tracking."""
    query: str
    summary: str
    sources: List[Dict[str, Any]]
    subqueries: List[str]
    depth: int
    content_analysis: Optional[List[Dict[str, Any]]] = None
    chain_of_thought: Optional[List[str]] = None
    research_stats: Optional[Dict[str, Any]] = None
    citation_stats: Optional[Dict[str, Any]] = None  # New field for tracking citation statistics
    timestamp: datetime = field(default_factory=datetime.now)

    def to_markdown(self, include_chain_of_thought: bool = False, include_objective: bool = False, language: str = "en") -> str:
        """Convert research results to markdown format including citation statistics."""
        stats = self.research_stats or {}
        elapsed_time = stats.get("elapsed_time_formatted", "Unknown")
        sources_count = stats.get("sources_count", len(self.sources))
        subqueries_count = stats.get("subqueries_count", len(self.subqueries))

        citation_stats = self.citation_stats or {}
        total_sources = citation_stats.get("total_sources", sources_count)
        total_learnings = citation_stats.get("total_learnings", 0)

        summary = self.summary

        lines = summary.split("\n")

        # Remove specific artifacts that can appear in the output
        cleaned_lines = []
        for line in lines:
            # Skip lines with these patterns
            if (line.strip().startswith("*Generated on:") or
                line.strip().startswith("Completed:") or
                "Here are" in line and ("search queries" in line or "queries to investigate" in line) or
                line.strip() == "Research Framework:" or
                "Key Findings:" in line or
                "Key aspects to focus on:" in line):
                continue
            cleaned_lines.append(line)

        summary = "\n".join(cleaned_lines)

        # Fix the "Research Report: **Objective:**" formatting issue
        if summary.startswith("# Research Report: **Objective:**"):
            summary = summary.replace("# Research Report: **Objective:**", "# Research Report")

        # Remove objective section if not requested
        if not include_objective and "**Objective:**" in summary:
            # Split by sections
            parts = summary.split("## ")
            filtered_parts = []

            for part in parts:
                # Keep executive summary or empty parts
                if part.startswith("Executive Summary") or not part.strip():
                    filtered_parts.append(part)
                    continue

                # Skip objective section
                if "**Objective:**" in part and "**Key Aspects to Focus On:**" in part:
                    continue

                # Keep other sections
                filtered_parts.append(part)

            # Reconstruct the summary
            if filtered_parts:
                if not filtered_parts[0].startswith("Executive Summary"):
                    summary = "## ".join(filtered_parts)
                else:
                    summary = filtered_parts[0] + "## " + "## ".join(filtered_parts[1:])

        md = [
            f"# {self.query}\n",
            f"{summary}\n"
        ]

        # Localize Research Process section
        if language.lower() == 'zh':
            md.append("## 研究过程\n")
            md.append(f"- **深度**: {self.depth}")
            md.append(f"- **广度**: {stats.get('breadth', '未指定')}")
            md.append(f"- **耗时**: {elapsed_time}")
            md.append(f"- **子查询探索数**: {subqueries_count}")
            md.append(f"- **来源分析数**: {sources_count}")

            if total_learnings > 0:
                md.append(f"- **提取的总学习点**: {total_learnings}")
                md.append(f"- **来源覆盖**: {total_sources} 个来源，包含 {total_learnings} 个跟踪信息点")

                source_reliability = citation_stats.get("source_reliability", {})
                if source_reliability:
                    md.append(f"- **来源质量**: {len(source_reliability)} 个域名的可靠性评估\n")
                else:
                    md.append("")
            else:
                md.append("")

            if include_chain_of_thought and self.chain_of_thought:
                md.append("## 研究过程：思维链\n")
                significant_thoughts = []

                for thought in self.chain_of_thought:
                    # Skip generic or repetitive thoughts and output artifacts
                    if any(x in thought.lower() for x in [
                        "searching for", "selected relevant url", "completed",
                        "here are", "generated search queries", "queries to investigate"
                    ]):
                        continue
                    significant_thoughts.append(thought)

                if len(significant_thoughts) > 20:
                    selected_thoughts = (
                        significant_thoughts[:5] +
                        significant_thoughts[len(significant_thoughts)//2-2:len(significant_thoughts)//2+3] +
                        significant_thoughts[-5:]
                    )
                else:
                    selected_thoughts = significant_thoughts

                for thought in selected_thoughts:
                    md.append(f"- {thought}")
                md.append("")
        else:
            md.append("## Research Process\n")
            md.append(f"- **Depth**: {self.depth}")
            md.append(f"- **Breadth**: {stats.get('breadth', 'Not specified')}")
            md.append(f"- **Time Taken**: {elapsed_time}")
            md.append(f"- **Subqueries Explored**: {subqueries_count}")
            md.append(f"- **Sources Analyzed**: {sources_count}")

            if total_learnings > 0:
                md.append(f"- **Total Learnings Extracted**: {total_learnings}")
                md.append(f"- **Source Coverage**: {total_sources} sources with {total_learnings} tracked information points")

                source_reliability = citation_stats.get("source_reliability", {})
                if source_reliability:
                    md.append(f"- **Source Quality**: {len(source_reliability)} domains assessed for reliability\n")
                else:
                    md.append("")
            else:
                md.append("")

            if include_chain_of_thought and self.chain_of_thought:
                md.append("## Research Process: Chain of Thought\n")
                significant_thoughts = []

                for thought in self.chain_of_thought:
                    # Skip generic or repetitive thoughts and output artifacts
                    if any(x in thought.lower() for x in [
                        "searching for", "selected relevant url", "completed",
                        "here are", "generated search queries", "queries to investigate"
                    ]):
                        continue
                    significant_thoughts.append(thought)

                if len(significant_thoughts) > 20:
                    selected_thoughts = (
                        significant_thoughts[:5] +
                        significant_thoughts[len(significant_thoughts)//2-2:len(significant_thoughts)//2+3] +
                        significant_thoughts[-5:]
                    )
                else:
                    selected_thoughts = significant_thoughts

                for thought in selected_thoughts:
                    md.append(f"- {thought}")
                md.append("")

        return "\n".join(md)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "query": self.query,
            "summary": self.summary,
            "sources": self.sources,
            "subqueries": self.subqueries,
            "depth": self.depth,
            "content_analysis": self.content_analysis,
            "chain_of_thought": self.chain_of_thought,
            "research_stats": self.research_stats,
            "timestamp": self.timestamp.isoformat()
        }

        if self.citation_stats:
            result["citation_stats"] = self.citation_stats

        return result

    def save_to_file(self, filepath: str, include_chain_of_thought: bool = False, include_objective: bool = False, language: str = "en") -> None:
        """Save research results to a file."""
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        if ext == '.md':
            # Save as markdown
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.to_markdown(include_chain_of_thought, include_objective, language))
        elif ext == '.json':
            # Save as JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
        else:
            # Default to markdown
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.to_markdown(include_chain_of_thought, include_objective, language))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchResult':
        """Create a ResearchResult from a dictionary."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        return cls(**data)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'ResearchResult':
        """Load research results from a file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls.from_dict(data)

class DeepResearcher:
    """Research orchestrator."""
    def __init__(
        self,
        output_dir: Optional[str] = None,
        save_results: bool = True,
        auto_save_interval: Optional[int] = None
    ):
        """Initialize the researcher."""
        self.output_dir = output_dir or os.path.expanduser("~/shandu_research")
        self.save_results = save_results
        self.auto_save_interval = auto_save_interval

        if self.save_results:
            os.makedirs(self.output_dir, exist_ok=True)

    def get_output_path(self, query: str, format: str = 'md') -> str:
        """Get output path for research results."""
        sanitized = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)
        sanitized = sanitized[:50]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{sanitized}_{timestamp}.{format}"

        return os.path.join(self.output_dir, filename)

    async def research(
        self,
        query: str,
        strategy: str = 'langgraph',
        **kwargs
    ) -> ResearchResult:
        """Perform research using the specified strategy."""
        from ..agents.langgraph_agent import ResearchGraph
        from ..agents.agent import ResearchAgent

        result = None

        if strategy == 'langgraph':
            graph = ResearchGraph()
            result = await graph.research(query, **kwargs)
        elif strategy == 'agent':
            agent = ResearchAgent()
            result = await agent.research(query, **kwargs)
        else:
            raise ValueError(f"Unknown research strategy: {strategy}")

        if self.save_results and result:
            md_path = self.get_output_path(query, 'md')
            result.save_to_file(md_path)

            json_path = self.get_output_path(query, 'json')
            result.save_to_file(json_path)

        return result

    def research_sync(
        self,
        query: str,
        strategy: str = 'langgraph',
        **kwargs
    ) -> ResearchResult:
        """Synchronous research wrapper."""
        import asyncio
        return asyncio.run(self.research(query, strategy, **kwargs))
