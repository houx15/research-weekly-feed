"""RSS feed fetcher for journals with RSS support."""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from xml.etree.ElementTree import ParseError

import feedparser

from src.fetchers.base_fetcher import BaseFetcher, Paper


class RSSFetcher(BaseFetcher):
    """Fetches papers from RSS feeds (SAGE, Nature, PNAS, etc.)."""

    def __init__(self, journals: Dict[str, Dict[str, str]], source_group: str = "RSS"):
        """Initialize RSS fetcher.

        Args:
            journals: Dictionary of journal configs {code: {name, rss}}
            source_group: Source group name (e.g., "SAGE", "Nature", "Other")
        """
        super().__init__(source_group)
        self.journals = journals

    def fetch_papers(
        self,
        days: int = 7,
        rate_limit_delay: float = 2.0,
        specific_journal: Optional[str] = None,
    ) -> List[Paper]:
        """Fetch papers from RSS feeds.

        Args:
            days: Number of days to look back
            rate_limit_delay: Delay between requests in seconds
            specific_journal: Optional specific journal code to fetch

        Returns:
            List of Paper objects
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        all_papers: List[Paper] = []

        # Filter to specific journal if requested
        journals_to_fetch = self.journals
        if specific_journal:
            if specific_journal in self.journals:
                journals_to_fetch = {specific_journal: self.journals[specific_journal]}
            else:
                print(f"Warning: Journal '{specific_journal}' not found in configuration")
                return []

        for journal_code, journal_info in journals_to_fetch.items():
            journal_name = journal_info['name']
            rss_url = journal_info['rss']

            print(f"Fetching from {journal_name}...")

            try:
                papers = self._parse_rss_feed(rss_url, journal_name, cutoff_date)
                all_papers.extend(papers)
                print(f"  Found {len(papers)} recent papers")

                # Rate limiting
                time.sleep(rate_limit_delay)

            except Exception as e:
                print(f"  Error fetching from {journal_name}: {e}")
                continue

        print(f"Total papers fetched from {self.source_name}: {len(all_papers)}")
        return all_papers

    def _parse_rss_feed(
        self,
        rss_url: str,
        journal_name: str,
        cutoff_date: datetime,
    ) -> List[Paper]:
        """Parse an RSS feed and extract papers.

        Args:
            rss_url: URL of the RSS feed
            journal_name: Name of the journal
            cutoff_date: Only include papers after this date

        Returns:
            List of Paper objects
        """
        papers: List[Paper] = []

        try:
            feed = feedparser.parse(rss_url)

            # Check if feed was parsed successfully
            if feed.bozo and not feed.entries:
                print(f"  Warning: Feed may have errors: {feed.get('bozo_exception', 'Unknown error')}")
                return papers

            for entry in feed.entries:
                try:
                    # Extract publication date
                    pub_date = self._extract_date(entry)
                    if not pub_date:
                        # If no date, skip date filtering
                        pub_date = datetime.now(timezone.utc)
                    elif pub_date < cutoff_date:
                        continue

                    # Extract title
                    title = entry.get('title', '').strip()
                    if not title:
                        continue

                    # Extract authors
                    authors = self._extract_authors(entry)

                    # Extract abstract/summary
                    abstract = entry.get('summary', entry.get('description', '')).strip()
                    # Remove HTML tags if present
                    if abstract:
                        import re
                        abstract = re.sub(r'<[^>]+>', '', abstract)

                    # Extract link
                    link = entry.get('link', entry.get('id', ''))

                    # Extract DOI if available
                    doi = self._extract_doi(entry)

                    paper = Paper(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=link,
                        published=pub_date,
                        source=journal_name,
                        doi=doi,
                    )
                    papers.append(paper)

                except Exception as e:
                    print(f"  Warning: Error parsing entry: {e}")
                    continue

        except ParseError as e:
            print(f"  XML parse error: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")

        return papers

    def _extract_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Extract publication date from RSS entry.

        Args:
            entry: RSS feed entry

        Returns:
            Datetime object or None
        """
        # Try different date fields
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            date_tuple = entry.get(date_field)
            if date_tuple:
                try:
                    # Convert time tuple to datetime
                    dt = datetime(*date_tuple[:6])
                    # Make timezone-aware (assume UTC)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    continue

        # Try parsing date strings
        for date_field in ['published', 'updated', 'created']:
            date_str = entry.get(date_field)
            if date_str:
                try:
                    # feedparser usually handles this, but just in case
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(date_str)
                except Exception:
                    continue

        return None

    def _extract_authors(self, entry: feedparser.FeedParserDict) -> List[str]:
        """Extract author names from RSS entry.

        Args:
            entry: RSS feed entry

        Returns:
            List of author names
        """
        authors = []

        # Try 'authors' field (list of dicts)
        if 'authors' in entry and entry.authors:
            for author_dict in entry.authors:
                name = author_dict.get('name', '')
                if name:
                    authors.append(name)

        # Try 'author' field (string)
        if not authors and 'author' in entry:
            author_str = entry.author.strip()
            if author_str:
                authors = self._normalize_authors(author_str)

        # Try 'dc:creator' field (Dublin Core)
        if not authors and 'dc_creator' in entry:
            authors = self._normalize_authors(entry.dc_creator)

        # If still no authors, return empty list
        if not authors:
            authors = ["Unknown"]

        return authors

    def _extract_doi(self, entry: feedparser.FeedParserDict) -> Optional[str]:
        """Extract DOI from RSS entry.

        Args:
            entry: RSS feed entry

        Returns:
            DOI string or None
        """
        # Try prism:doi (common in academic RSS feeds)
        doi = entry.get('prism_doi')
        if doi:
            return doi

        # Try dc:identifier
        identifier = entry.get('dc_identifier')
        if identifier and 'doi' in identifier.lower():
            return identifier

        # Try extracting from link
        link = entry.get('link', '')
        if 'doi.org/' in link:
            return link.split('doi.org/')[-1]

        return None
