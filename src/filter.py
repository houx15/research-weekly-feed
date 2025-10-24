"""Paper filtering and relevance scoring."""

import re
from typing import Any, Dict, List, Optional, Tuple


class PaperFilter:
    """Filters and scores papers based on keyword relevance."""

    def __init__(
        self,
        primary_keywords: List[str],
        secondary_keywords: Optional[List[str]] = None,
    ):
        """Initialize filter with keywords.

        Args:
            primary_keywords: Primary keywords for matching (weighted higher)
            secondary_keywords: Secondary keywords for matching (weighted lower)
        """
        self.primary_keywords = [kw.lower() for kw in primary_keywords]
        self.secondary_keywords = (
            [kw.lower() for kw in secondary_keywords] if secondary_keywords else []
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching.

        Args:
            text: Text to normalize

        Returns:
            Normalized lowercase text
        """
        return text.lower()

    def _count_keyword_matches(self, text: str, keywords: List[str]) -> Dict[str, int]:
        """Count how many times each keyword appears in text.

        Args:
            text: Text to search
            keywords: List of keywords to find

        Returns:
            Dictionary mapping keyword to count
        """
        normalized_text = self._normalize_text(text)
        matches: Dict[str, int] = {}

        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            count = len(re.findall(pattern, normalized_text))
            if count > 0:
                matches[keyword] = count

        return matches

    def score_paper(self, paper: Any) -> Tuple[int, List[str]]:
        """Score a paper based on keyword relevance.

        Args:
            paper: Paper object with title and abstract attributes

        Returns:
            Tuple of (score, matched_keywords)
        """
        # Combine title and abstract for searching
        searchable_text = f"{paper.title} {paper.abstract}"

        # Find matches
        primary_matches = self._count_keyword_matches(searchable_text, self.primary_keywords)
        secondary_matches = self._count_keyword_matches(
            searchable_text, self.secondary_keywords
        )

        # Calculate score
        # Primary keywords worth 10 points each
        # Secondary keywords worth 3 points each
        score = 0
        matched_keywords: List[str] = []

        for keyword, count in primary_matches.items():
            score += count * 10
            matched_keywords.append(keyword)

        for keyword, count in secondary_matches.items():
            score += count * 3
            matched_keywords.append(keyword)

        return score, matched_keywords

    def filter_papers(
        self,
        papers: List[Any],
        min_score: int = 1,
    ) -> List[Any]:
        """Filter papers by minimum relevance score.

        Args:
            papers: List of paper objects
            min_score: Minimum score to include paper

        Returns:
            Filtered list of papers with scores and matched keywords
        """
        filtered_papers = []

        for paper in papers:
            score, matched_keywords = self.score_paper(paper)

            if score >= min_score:
                paper.relevance_score = score
                paper.matched_keywords = matched_keywords
                filtered_papers.append(paper)

        # Sort by relevance score (highest first)
        filtered_papers.sort(key=lambda p: p.relevance_score, reverse=True)

        return filtered_papers

    def group_papers_by_relevance(
        self,
        papers: List[Any],
    ) -> Dict[str, List[Any]]:
        """Group papers by relevance level.

        Args:
            papers: List of paper objects with relevance_score attribute

        Returns:
            Dictionary with 'high', 'medium', 'low' relevance groups
        """
        groups: Dict[str, List[Any]] = {
            "high": [],
            "medium": [],
            "low": [],
        }

        for paper in papers:
            score = paper.relevance_score

            if score >= 20:
                groups["high"].append(paper)
            elif score >= 10:
                groups["medium"].append(paper)
            else:
                groups["low"].append(paper)

        return groups
