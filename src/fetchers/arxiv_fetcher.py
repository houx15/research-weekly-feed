"""ArXiv paper fetcher with filtering capabilities."""

import time
from datetime import datetime, timedelta, timezone
from typing import List, Set

import arxiv

from src.fetchers.base_fetcher import BaseFetcher, Paper


class ArXivFetcher(BaseFetcher):
    """Fetches papers from ArXiv API with rate limiting and error handling."""

    def __init__(self, categories: List[str], max_results: int = 100):
        """Initialize fetcher.

        Args:
            categories: List of ArXiv category codes (e.g., 'cs.CY')
            max_results: Maximum results to fetch per category
        """
        super().__init__("ArXiv")
        self.categories = categories
        self.max_results = max_results
        self.client = arxiv.Client()

    def fetch_papers(
        self,
        days: int = 7,
        rate_limit_delay: float = 3.0,
    ) -> List[Paper]:
        """Fetch papers from ArXiv within date range.

        Args:
            days: Number of days to look back
            rate_limit_delay: Delay between requests in seconds

        Returns:
            List of Paper objects
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        all_papers: List[Paper] = []
        seen_urls: Set[str] = set()

        for category in self.categories:
            print(f"Fetching papers from category: {category}")

            # Build search query for this category
            query = f"cat:{category}"

            # Create search with sorting by submission date
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            try:
                results = self.client.results(search)

                for result in results:
                    # Check if paper is within date range
                    if result.published < cutoff_date:
                        # Since we're sorted by date, we can break early
                        break

                    # Avoid duplicates (papers can be in multiple categories)
                    if result.entry_id in seen_urls:
                        continue

                    seen_urls.add(result.entry_id)

                    # Convert to unified Paper format
                    paper = Paper(
                        title=result.title,
                        authors=[author.name for author in result.authors],
                        abstract=result.summary,
                        url=result.entry_id,
                        published=result.published,
                        source=self.source_name,
                        categories=result.categories,
                        pdf_url=result.pdf_url,
                    )
                    all_papers.append(paper)

                # Rate limiting to be respectful to ArXiv API
                time.sleep(rate_limit_delay)

            except Exception as e:
                print(f"Error fetching from category {category}: {e}")
                continue

        print(f"Fetched {len(all_papers)} unique papers total")
        return all_papers

    def fetch_by_keyword_search(
        self,
        keywords: List[str],
        days: int = 7,
        max_results: int = 50,
    ) -> List[Paper]:
        """Fetch papers by direct keyword search (alternative method).

        Args:
            keywords: List of keywords to search
            days: Number of days to look back
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        all_papers: List[Paper] = []
        seen_urls: Set[str] = set()

        # Build search query with keywords
        # Using OR logic between keywords
        keyword_query = " OR ".join([f'"{kw}"' for kw in keywords])

        # Combine with category filter if categories exist
        if self.categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in self.categories])
            query = f"({keyword_query}) AND ({cat_query})"
        else:
            query = keyword_query

        print(f"Searching ArXiv with query: {query[:100]}...")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        try:
            results = self.client.results(search)

            for result in results:
                if result.published < cutoff_date:
                    continue

                if result.entry_id not in seen_urls:
                    seen_urls.add(result.entry_id)
                    paper = Paper(
                        title=result.title,
                        authors=[author.name for author in result.authors],
                        abstract=result.summary,
                        url=result.entry_id,
                        published=result.published,
                        source=self.source_name,
                        categories=result.categories,
                        pdf_url=result.pdf_url,
                    )
                    all_papers.append(paper)

        except Exception as e:
            print(f"Error during keyword search: {e}")

        print(f"Found {len(all_papers)} papers via keyword search")
        return all_papers
