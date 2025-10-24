# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research paper aggregator for computational methods, gender inequality, and social media studies. Fetches papers from ArXiv, major journals (Nature, Science, PNAS), sociology journals via RSS/CrossRef API, filters by keywords, scores by relevance, and generates Markdown reports.

## Environment Setup

This project uses conda for environment management (Python 3.10+):

```bash
conda create -n research-feed python=3.10 -y
conda activate research-feed
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Common Commands

### Fetch from all sources (default):
```bash
python main.py
```

### Source-specific fetching:
```bash
python main.py --source arxiv      # ArXiv only
python main.py --source sage       # SAGE journals
python main.py --source nature     # Nature journals
python main.py --source other      # PNAS, Science, etc.
python main.py --source crossref   # CrossRef API
python main.py --source all        # All sources (default)
```

### Journal-specific fetching:
```bash
python main.py --journal asr       # American Sociological Review
python main.py --journal nature    # Nature
python main.py --journal pnas      # PNAS
```

### Report options:
```bash
python main.py --days 14           # Look back 14 days
python main.py --min-score 20      # High relevance only
python main.py --summary           # Summary report (no abstracts)
```

### Development:
```bash
ruff check .                       # Run linting
```

## Architecture

**Phase 2 (Current - Multi-source integration):**

**Fetcher System:**
- `src/fetchers/base_fetcher.py` - Base class defining fetcher interface and unified Paper dataclass
- `src/fetchers/arxiv_fetcher.py` - ArXiv API integration with rate limiting (3s delay)
- `src/fetchers/rss_fetcher.py` - Generic RSS feed parser for SAGE, Nature, PNAS, Science, Social Forces, Demography
- `src/fetchers/crossref_fetcher.py` - CrossRef API integration for journals without RSS (RSSM, Chinese Soc Review, Social Science Research)

**Configuration:**
- `src/config.py` - Loads both keywords.yaml and sources.yaml
- `config/keywords.yaml` - Research keywords and ArXiv categories
- `config/sources.yaml` - Journal RSS feeds and CrossRef ISSNs

**Filtering & Reporting:**
- `src/filter.py` - Keyword filtering and relevance scoring (works with unified Paper objects)
- `src/report_generator.py` - Markdown report generation with source attribution
- `main.py` - CLI entry point with source/journal filtering options

## Key Design Decisions

**Unified Paper Model:**
All fetchers return `Paper` dataclass with standardized fields (title, authors, abstract, url, published, source, doi). This allows:
- Single filtering pipeline for all sources
- Consistent report generation
- Easy addition of new sources

**Fetcher Inheritance:**
All fetchers inherit from `BaseFetcher` abstract class:
- `fetch_papers(days)` - Required method
- `_normalize_authors()` - Helper for author name parsing
- Each fetcher handles source-specific parsing

**Relevance Scoring:**
- Primary keywords: 10 points per match
- Secondary keywords: 3 points per match
- Papers grouped as High (≥20), Medium (10-19), Low (1-9) relevance
- Word boundary matching prevents partial matches

**Source Integration:**
- **ArXiv**: Direct API via `arxiv` library, searches by category
- **RSS Journals**: `feedparser` library, handles RSS 1.0/2.0, extracts dublin core metadata
- **CrossRef**: REST API with ISSN filtering, returns JSON with DOI metadata

**Rate Limiting:**
- ArXiv: 3 second delay between category requests
- RSS feeds: 2 second delay between journals
- CrossRef: 0.5 second delay (API limit is 50 req/s)

**Configuration:**
Two separate YAML files:
- `keywords.yaml` - Research-specific (keywords, ArXiv categories)
- `sources.yaml` - Journal configurations organized by type (sage_journals, nature_journals, other_journals, crossref_journals)

**CLI Design:**
- `--source`: Filter by source group (arxiv, sage, nature, other, crossref, all)
- `--journal`: Filter by specific journal code within a source
- `--days`: Lookback window
- `--min-score`: Relevance threshold
- `--summary`: Compact report without abstracts

**Output:**
Reports saved to `outputs/` with timestamp filenames. Two formats:
- Full report: includes abstracts, DOIs, source attribution
- Summary report: titles, links, and scores only

## Development Notes

- **Python 3.9+ compatible**: Uses `Union[...]` instead of `|` for type hints
- **Error handling**: Each source has try/except to prevent single source failure from breaking entire run
- **RSS parsing**: Some feeds have XML errors (SAGE, Social Forces) - logged but don't crash
- **Date handling**: All datetimes converted to timezone-aware UTC for consistent comparison
- **Deduplication**: ArXiv papers can appear in multiple categories, deduplicated by URL
- **Author parsing**: Handles various formats (comma-separated, semicolon, "and", single author)
- **Abstract cleaning**: Removes HTML/XML tags from RSS abstracts

## Adding New Sources

To add a new journal:

**For RSS feeds:**
1. Add to `config/sources.yaml` under appropriate section
2. No code changes needed - `RSSFetcher` handles automatically

**For non-RSS journals:**
1. Add to `config/sources.yaml` under `crossref_journals` with ISSN
2. Or create new fetcher inheriting from `BaseFetcher`

**For new APIs:**
1. Create new fetcher class in `src/fetchers/`
2. Inherit from `BaseFetcher`
3. Implement `fetch_papers(days)` returning `List[Paper]`
4. Add to `main.py` source selection logic

## Common Issues

- **SAGE RSS feeds**: Often have XML parsing errors (logged, returns 0 papers)
- **Missing abstracts**: Some RSS feeds (Nature, Science) don't include full abstracts
- **Date filtering**: Some journals have delayed RSS updates, may miss very recent papers
- **CrossRef rate limits**: Using conservative 0.5s delay, can be reduced if needed
- **Timezone issues**: Fixed by using `datetime.now(timezone.utc)` everywhere

## Testing

Test individual sources:
```bash
python main.py --source arxiv --days 3
python main.py --source nature --days 7
python main.py --source crossref --days 14
```

Test all sources:
```bash
python main.py --source all --days 7 --min-score 10
```

Verify report generation:
```bash
ls -lh outputs/
head -100 outputs/research_papers_*.md
```
