# Phase 2: Journal Integration Specification

## Overview
Add support for fetching papers from top social science journals using RSS feeds and APIs.

## Research Focus
- Computational methods
- Gender inequality  
- Social media
- Quantitative sociology

## Implementation Priority

### Tier 1: SAGE Journals (Implement First - Has RSS)
1. American Sociological Review (ASR)
2. American Journal of Sociology (AJS)
3. Gender & Society
4. Sociological Methods & Research
5. Chinese Journal of Sociology

**RSS Pattern**: `https://journals.sagepub.com/feed/{code}`

**Journal Codes**:
```python
SAGE_JOURNALS = {
    'asr': 'American Sociological Review',
    'ajs': 'American Journal of Sociology',
    'gso': 'Gender & Society',
    'smr': 'Sociological Methods & Research',
    'chn': 'Chinese Journal of Sociology'
}
```

### Tier 2: High-Impact Journals (Has RSS)
1. Nature: `https://www.nature.com/nature.rss`
2. Nature Human Behaviour: `https://www.nature.com/nathumbehav/rss/current`
3. Science: `https://www.science.org/rss/news_current.xml`
4. PNAS: `https://www.pnas.org/rss/current.xml`

### Tier 3: Other Sociology Journals (Has RSS)
1. Social Forces (Oxford): `https://academic.oup.com/rss/site_sf/current.xml`
2. Demography (Springer): `https://link.springer.com/search.rss?facet-journal-id=13524`

### Tier 4: Journals Without RSS (Use CrossRef API)
1. Research on Social Stratification and Mobility (RSSM) - ISSN: 0276-5624
2. Chinese Sociological Review - ISSN: 2162-0555
3. Social Science Research - ISSN: 0049-089X

**CrossRef API**: `https://api.crossref.org/works`

## Technical Implementation

### RSS Feed Parsing
Use `feedparser` library to parse RSS feeds.

**Example code**:
```python
import feedparser
from datetime import datetime, timedelta

def fetch_rss_feed(url, days=7):
    feed = feedparser.parse(url)
    cutoff_date = datetime.now() - timedelta(days=days)
    
    papers = []
    for entry in feed.entries:
        pub_date = entry.get('published_parsed')
        if pub_date:
            pub_datetime = datetime(*pub_date[:6])
            if pub_datetime < cutoff_date:
                continue
        
        papers.append({
            'title': entry.get('title', ''),
            'authors': entry.get('author', ''),
            'abstract': entry.get('summary', ''),
            'link': entry.get('link', ''),
            'published': pub_datetime.strftime('%Y-%m-%d'),
            'source': feed.feed.get('title', '')
        })
    
    return papers
```

### CrossRef API for Journals Without RSS

**Example code**:
```python
import requests

def fetch_crossref(issn, days=7):
    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    url = 'https://api.crossref.org/works'
    params = {
        'filter': f'issn:{issn},from-pub-date:{from_date}',
        'rows': 100,
        'sort': 'published',
        'order': 'desc'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    papers = []
    for item in data['message']['items']:
        authors = ', '.join([
            f"{a.get('given', '')} {a.get('family', '')}" 
            for a in item.get('author', [])
        ])
        
        papers.append({
            'title': item.get('title', [''])[0],
            'authors': authors,
            'doi': item.get('DOI', ''),
            'link': f"https://doi.org/{item.get('DOI', '')}",
            'published': str(item.get('published-print', {}).get('date-parts', [['']])[0]),
            'source': item.get('container-title', [''])[0]
        })
    
    return papers
```

## Project Structure Changes

Add to existing structure:
```
src/
├── fetchers/
│   ├── arxiv_fetcher.py (existing)
│   ├── sage_fetcher.py (new)
│   ├── nature_fetcher.py (new)
│   ├── crossref_fetcher.py (new)
│   └── base_fetcher.py (refactor)
```

## Configuration File

Add to `config/sources.yaml`:
```yaml
sage_journals:
  asr:
    name: "American Sociological Review"
    rss: "https://journals.sagepub.com/feed/asr"
  ajs:
    name: "American Journal of Sociology"
    rss: "https://journals.sagepub.com/feed/ajs"
  gso:
    name: "Gender & Society"
    rss: "https://journals.sagepub.com/feed/gso"
  smr:
    name: "Sociological Methods & Research"
    rss: "https://journals.sagepub.com/feed/smr"
  chn:
    name: "Chinese Journal of Sociology"
    rss: "https://journals.sagepub.com/feed/chn"

nature_journals:
  nature:
    name: "Nature"
    rss: "https://www.nature.com/nature.rss"
  nature_human_behaviour:
    name: "Nature Human Behaviour"
    rss: "https://www.nature.com/nathumbehav/rss/current"

other_journals:
  pnas:
    name: "PNAS"
    rss: "https://www.pnas.org/rss/current.xml"
  science:
    name: "Science"
    rss: "https://www.science.org/rss/news_current.xml"
  social_forces:
    name: "Social Forces"
    rss: "https://academic.oup.com/rss/site_sf/current.xml"

crossref_journals:
  rssm:
    name: "Research on Social Stratification and Mobility"
    issn: "0276-5624"
  chinese_soc_review:
    name: "Chinese Sociological Review"
    issn: "2162-0555"
```

## Implementation Steps

1. **Create base fetcher class** that all fetchers inherit from
2. **Implement SAGE fetcher** (Tier 1) - test thoroughly
3. **Implement Nature/Science/PNAS fetcher** (Tier 2)
4. **Implement CrossRef fetcher** (Tier 4) for journals without RSS
5. **Update main.py** to include all sources
6. **Update report generator** to handle multiple sources
7. **Add error handling** for rate limits and failed requests

## Testing Requirements

- Test each fetcher independently
- Handle rate limiting (CrossRef: 50 requests/second)
- Handle network errors gracefully
- Test with different date ranges
- Verify keyword filtering works across all sources

## Dependencies to Add
```txt
feedparser>=6.0.0
requests>=2.31.0
```

## CLI Updates
```bash
# Fetch from all sources
python main.py --days 7

# Fetch from specific source only
python main.py --days 7 --source sage
python main.py --days 7 --source nature
python main.py --days 7 --source arxiv

# Fetch from specific journal
python main.py --days 7 --journal asr
```

## Notes

- SAGE journals use standard RSS 2.0 format
- Nature journals use RSS 1.0 with RDF namespace (feedparser handles both)
- CrossRef API is free but rate-limited
- Some abstracts may not be available in RSS feeds
- Consider caching responses to avoid repeated API calls