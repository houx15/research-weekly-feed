"""Base fetcher class for all paper sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union


@dataclass
class Paper:
    """Unified paper representation across all sources."""

    title: str
    authors: List[str]
    abstract: str
    url: str
    published: datetime
    source: str  # e.g., "ArXiv", "Nature", "American Sociological Review"
    categories: Optional[List[str]] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None

    # Filtering metadata
    relevance_score: int = 0
    matched_keywords: List[str] = None

    def __post_init__(self):
        """Initialize matched_keywords if None."""
        if self.matched_keywords is None:
            self.matched_keywords = []

    def __repr__(self) -> str:
        return f"Paper(title={self.title!r}, source={self.source!r}, published={self.published})"


class BaseFetcher(ABC):
    """Abstract base class for all paper fetchers."""

    def __init__(self, source_name: str):
        """Initialize fetcher.

        Args:
            source_name: Name of the source (e.g., "ArXiv", "SAGE", "Nature")
        """
        self.source_name = source_name

    @abstractmethod
    def fetch_papers(self, days: int = 7) -> List[Paper]:
        """Fetch papers from the source.

        Args:
            days: Number of days to look back

        Returns:
            List of Paper objects
        """
        pass

    def _normalize_authors(self, authors: Union[str, List[str]]) -> List[str]:
        """Normalize author names to list format.

        Args:
            authors: Author names as string or list

        Returns:
            List of author names
        """
        if isinstance(authors, str):
            # Split by common separators
            if ',' in authors:
                return [a.strip() for a in authors.split(',')]
            elif ';' in authors:
                return [a.strip() for a in authors.split(';')]
            elif ' and ' in authors.lower():
                return [a.strip() for a in authors.replace(' and ', ',').split(',')]
            else:
                return [authors.strip()]
        return authors
