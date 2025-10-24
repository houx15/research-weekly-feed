"""CrossRef API fetcher for journals without RSS feeds."""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

from src.fetchers.base_fetcher import BaseFetcher, Paper


class CrossRefFetcher(BaseFetcher):
    """Fetches papers from CrossRef API for journals without RSS."""

    def __init__(self, journals: Dict[str, Dict[str, str]]):
        """Initialize CrossRef fetcher.

        Args:
            journals: Dictionary of journal configs {code: {name, issn}}
        """
        super().__init__("CrossRef")
        self.journals = journals
        self.base_url = "https://api.crossref.org/works"
        self.rate_limit = 50  # CrossRef allows 50 requests per second

    def fetch_papers(
        self,
        days: int = 7,
        rate_limit_delay: float = 0.5,
        specific_journal: Optional[str] = None,
    ) -> List[Paper]:
        """Fetch papers from CrossRef API.

        Args:
            days: Number of days to look back
            rate_limit_delay: Delay between requests in seconds
            specific_journal: Optional specific journal code to fetch

        Returns:
            List of Paper objects
        """
        from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
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
            issn = journal_info['issn']

            print(f"Fetching from {journal_name} via CrossRef...")

            try:
                papers = self._fetch_by_issn(issn, journal_name, from_date)
                all_papers.extend(papers)
                print(f"  Found {len(papers)} recent papers")

                # Rate limiting
                time.sleep(rate_limit_delay)

            except Exception as e:
                print(f"  Error fetching from {journal_name}: {e}")
                continue

        print(f"Total papers fetched from CrossRef: {len(all_papers)}")
        return all_papers

    def _fetch_by_issn(
        self,
        issn: str,
        journal_name: str,
        from_date: str,
    ) -> List[Paper]:
        """Fetch papers by ISSN from CrossRef.

        Args:
            issn: Journal ISSN
            journal_name: Name of the journal
            from_date: Date in YYYY-MM-DD format

        Returns:
            List of Paper objects
        """
        papers: List[Paper] = []

        params = {
            'filter': f'issn:{issn},from-pub-date:{from_date}',
            'rows': 100,
            'sort': 'published',
            'order': 'desc',
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers={'User-Agent': 'ResearchWeeklyFeed/0.1 (mailto:research@example.com)'},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            if 'message' in data and 'items' in data['message']:
                for item in data['message']['items']:
                    try:
                        paper = self._parse_crossref_item(item, journal_name)
                        if paper:
                            papers.append(paper)
                    except Exception as e:
                        print(f"  Warning: Error parsing item: {e}")
                        continue

        except requests.exceptions.RequestException as e:
            print(f"  HTTP error: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")

        return papers

    def _parse_crossref_item(self, item: dict, journal_name: str) -> Optional[Paper]:
        """Parse a CrossRef item into a Paper object.

        Args:
            item: CrossRef API item
            journal_name: Name of the journal

        Returns:
            Paper object or None
        """
        # Extract title
        title_list = item.get('title', [])
        if not title_list:
            return None
        title = title_list[0].strip()

        # Extract authors
        authors = []
        for author_dict in item.get('author', []):
            given = author_dict.get('given', '')
            family = author_dict.get('family', '')
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        if not authors:
            authors = ["Unknown"]

        # Extract abstract
        abstract = item.get('abstract', '')
        if abstract:
            # Remove JATS XML tags if present
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)

        # Extract DOI
        doi = item.get('DOI', '')

        # Extract link
        link = f"https://doi.org/{doi}" if doi else item.get('URL', '')

        # Extract publication date
        pub_date = self._extract_crossref_date(item)
        if not pub_date:
            pub_date = datetime.now(timezone.utc)

        paper = Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            url=link,
            published=pub_date,
            source=journal_name,
            doi=doi,
        )

        return paper

    def _extract_crossref_date(self, item: dict) -> Optional[datetime]:
        """Extract publication date from CrossRef item.

        Args:
            item: CrossRef API item

        Returns:
            Datetime object or None
        """
        # Try different date fields
        for date_field in ['published-print', 'published-online', 'published', 'created']:
            date_parts = item.get(date_field, {}).get('date-parts', [[]])
            if date_parts and date_parts[0]:
                try:
                    year = date_parts[0][0]
                    month = date_parts[0][1] if len(date_parts[0]) > 1 else 1
                    day = date_parts[0][2] if len(date_parts[0]) > 2 else 1
                    dt = datetime(year, month, day, tzinfo=timezone.utc)
                    return dt
                except (ValueError, IndexError):
                    continue

        return None
