"""Markdown report generation for research papers."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union


class MarkdownReportGenerator:
    """Generates markdown reports for filtered research papers."""

    def __init__(self, output_dir: Union[str, Path] = "outputs"):
        """Initialize report generator.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _format_authors(self, authors: List[str], max_authors: int = 3) -> str:
        """Format author list for display.

        Args:
            authors: List of author names
            max_authors: Maximum authors to show before using 'et al.'

        Returns:
            Formatted author string
        """
        if len(authors) <= max_authors:
            return ", ".join(authors)
        else:
            return f"{', '.join(authors[:max_authors])}, et al."

    def _format_paper(self, paper: Any) -> str:
        """Format a single paper as markdown.

        Args:
            paper: Paper object with metadata

        Returns:
            Markdown formatted paper entry
        """
        # Format date
        pub_date = paper.published.strftime("%Y-%m-%d")

        # Format keywords
        keywords_str = ", ".join(paper.matched_keywords)

        # Build markdown
        md = f"### {paper.title}\n\n"
        md += f"**Source:** {paper.source}\n\n"
        md += f"**Authors:** {self._format_authors(paper.authors)}\n\n"
        md += f"**Published:** {pub_date}\n\n"
        md += f"**Relevance Score:** {paper.relevance_score}\n\n"

        # Show LLM metadata if available
        if hasattr(paper, 'llm_metadata') and paper.llm_metadata:
            md += f"**LLM Confidence:** {paper.llm_metadata.get('confidence', 'N/A')}\n\n"
            if paper.llm_metadata.get('reasoning'):
                md += f"**LLM Reasoning:** {paper.llm_metadata['reasoning']}\n\n"
            if paper.llm_metadata.get('topics'):
                topics_str = ", ".join(paper.llm_metadata['topics'])
                md += f"**Relevant Topics:** {topics_str}\n\n"
        else:
            md += f"**Matched Keywords:** {keywords_str}\n\n"

        if hasattr(paper, 'doi') and paper.doi:
            md += f"**DOI:** {paper.doi}\n\n"
        md += f"**Link:** {paper.url}\n\n"
        if paper.abstract:
            md += f"**Abstract:**\n\n{paper.abstract}\n\n"
        md += "---\n\n"

        return md

    def _format_group(
        self,
        papers: List[Any],
        group_name: str,
        group_description: str,
    ) -> str:
        """Format a group of papers.

        Args:
            papers: List of papers
            group_name: Name of the group
            group_description: Description of the group

        Returns:
            Markdown formatted group section
        """
        if not papers:
            return ""

        md = f"## {group_name} ({len(papers)} papers)\n\n"
        md += f"_{group_description}_\n\n"

        for paper in papers:
            md += self._format_paper(paper)

        return md

    def generate_report(
        self,
        papers: List[Any],
        grouped_papers: Dict[str, List[Any]],
        days: int,
        sources: List[str],
    ) -> str:
        """Generate complete markdown report.

        Args:
            papers: All filtered papers
            grouped_papers: Papers grouped by relevance
            days: Number of days covered
            sources: List of sources searched

        Returns:
            Path to generated report file
        """
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_papers_{timestamp}.md"
        filepath = self.output_dir / filename

        # Build report header
        report = "# Research Paper Weekly Feed\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += f"**Time Range:** Last {days} days\n\n"
        report += f"**Sources:** {', '.join(sorted(sources))}\n\n"
        report += f"**Total Papers Found:** {len(papers)}\n\n"
        report += "---\n\n"

        # Add summary statistics
        report += "## Summary\n\n"
        report += f"- **High Relevance:** {len(grouped_papers['high'])} papers\n"
        report += f"- **Medium Relevance:** {len(grouped_papers['medium'])} papers\n"
        report += f"- **Low Relevance:** {len(grouped_papers['low'])} papers\n\n"
        report += "---\n\n"

        # Add grouped papers
        report += self._format_group(
            grouped_papers["high"],
            "High Relevance Papers",
            "Papers with strong matches to primary research keywords (score ≥ 20)",
        )

        report += self._format_group(
            grouped_papers["medium"],
            "Medium Relevance Papers",
            "Papers with moderate matches to research keywords (score 10-19)",
        )

        report += self._format_group(
            grouped_papers["low"],
            "Low Relevance Papers",
            "Papers with some matches to research keywords (score 1-9)",
        )

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return str(filepath)

    def generate_summary_report(
        self,
        papers: List[Any],
        grouped_papers: Dict[str, List[Any]],
        days: int,
    ) -> str:
        """Generate a brief summary report (no full abstracts).

        Args:
            papers: All filtered papers
            grouped_papers: Papers grouped by relevance
            days: Number of days covered

        Returns:
            Path to generated summary report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_summary_{timestamp}.md"
        filepath = self.output_dir / filename

        report = "# Research Paper Summary\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += f"**Time Range:** Last {days} days\n\n"
        report += f"**Total Papers:** {len(papers)}\n\n"
        report += "---\n\n"

        for group_name, group_papers in [
            ("High Relevance", grouped_papers["high"]),
            ("Medium Relevance", grouped_papers["medium"]),
            ("Low Relevance", grouped_papers["low"]),
        ]:
            if group_papers:
                report += f"## {group_name} ({len(group_papers)} papers)\n\n"
                for paper in group_papers:
                    report += f"- **{paper.title}**\n"
                    report += f"  - Score: {paper.relevance_score}\n"
                    report += f"  - Keywords: {', '.join(paper.matched_keywords)}\n"
                    report += f"  - Link: {paper.url}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return str(filepath)
