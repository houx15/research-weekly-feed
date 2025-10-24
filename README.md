# Research Weekly Feed

A research paper aggregator for computational methods, gender inequality, and social media studies. Fetches papers from ArXiv, major journals (Nature, Science, PNAS), sociology journals (via RSS and CrossRef API), and generates filtered reports based on your research keywords.

## Features

**Phase 2 (Current):**
- ✅ Fetches papers from ArXiv API across multiple categories (cs.CY, cs.SI, stat.AP, econ.GN)
- ✅ Fetches from major journals via RSS (Nature, Nature Human Behaviour, Science, PNAS)
- ✅ Fetches from sociology journals via RSS (Social Forces, Demography)
- ✅ Fetches from journals without RSS via CrossRef API (RSSM, Chinese Sociological Review, Social Science Research)
- ✅ SAGE journals support (ASR, AJS, Gender & Society, SMR, Chinese Journal of Sociology)
- ✅ Filters papers by configurable keywords with relevance scoring
- ✅ **NEW: LLM-based semantic relevance scoring** using Aliyun DashScope or Azure OpenAI
- ✅ Generates detailed Markdown reports with paper metadata
- ✅ Source filtering: fetch from specific sources or all sources
- ✅ Journal filtering: fetch from specific journals
- ✅ Configurable date ranges and filtering thresholds

## Installation

1. Clone the repository:
```bash
git clone https://github.com/houx15/research-weekly-feed.git
cd research-weekly-feed
```

2. Create a conda environment and install dependencies:
```bash
conda create -n research-feed python=3.10 -y
conda activate research-feed
pip install -e .
```

## Usage

### Basic Usage

Fetch papers from all sources (last 7 days):
```bash
python main.py
```

Specify number of days to look back:
```bash
python main.py --days 14
```

### Source Filtering

Fetch from specific source only:
```bash
python main.py --source arxiv      # ArXiv only
python main.py --source sage       # SAGE journals only
python main.py --source nature     # Nature journals only
python main.py --source other      # PNAS, Science, etc.
python main.py --source crossref   # CrossRef API journals
python main.py --source all        # All sources (default)
```

### Journal Filtering

Fetch from specific journal:
```bash
python main.py --journal asr       # American Sociological Review
python main.py --journal nature    # Nature
python main.py --journal pnas      # PNAS
```

### LLM Scoring (NEW)

Use LLM for semantic relevance scoring instead of keyword matching:
```bash
python main.py --use-llm
```

Configure LLM settings:
```bash
python main.py --use-llm --llm-config config/llm.yaml --min-score 50
```

### Report Options

Generate summary report (titles only, no abstracts):
```bash
python main.py --summary
```

Adjust minimum relevance score:
```bash
python main.py --min-score 10
```

All options:
```bash
python main.py --help
```

## Configuration

### Keywords Configuration

Edit `config/keywords.yaml` to customize:
- ArXiv categories to search
- Primary keywords (weighted higher in relevance scoring)
- Secondary keywords (weighted lower)
- Default search parameters

### Sources Configuration

Edit `config/sources.yaml` to:
- Add/remove RSS feed URLs for journals
- Configure CrossRef API journals by ISSN
- Organize journals by category (SAGE, Nature, Other, CrossRef)

### LLM Configuration (NEW)

Edit `config/llm.yaml` to configure LLM-based scoring:
- Choose provider: DashScope (Aliyun) or Azure OpenAI
- Set API credentials and model
- Define research interests for semantic evaluation
- Configure scoring thresholds and caching

Copy the template:
```bash
cp config/llm.yaml.template config/llm.yaml
```

Then edit `config/llm.yaml` with your credentials.

## Available Sources

**ArXiv Categories:**
- cs.CY (Computers and Society)
- cs.SI (Social and Information Networks)
- stat.AP (Statistics - Applications)
- econ.GN (Economics - General Economics)

**SAGE Journals (RSS):**
- American Sociological Review (ASR)
- American Journal of Sociology (AJS)
- Gender & Society
- Sociological Methods & Research
- Chinese Journal of Sociology

**Nature Journals (RSS):**
- Nature
- Nature Human Behaviour

**Other Journals (RSS):**
- PNAS
- Science
- Social Forces
- Demography

**CrossRef API Journals:**
- Research on Social Stratification and Mobility (RSSM)
- Chinese Sociological Review
- Social Science Research

## Output

Reports are saved to `outputs/` directory with timestamps:
- `research_papers_YYYYMMDD_HHMMSS.md` - Full report with abstracts
- `research_summary_YYYYMMDD_HHMMSS.md` - Summary report (when using --summary)

Papers are grouped by relevance:

**Keyword-based scoring:**
- **High Relevance** (score ≥ 20): Strong matches to primary keywords
- **Medium Relevance** (score 10-19): Moderate keyword matches
- **Low Relevance** (score 1-9): Some keyword matches

**LLM-based scoring:**
- **High Relevance** (score ≥ 75): Highly relevant to research interests
- **Medium Relevance** (score 50-74): Moderately relevant
- **Low Relevance** (score < 50): Somewhat relevant

Each paper entry includes:
- Source journal/database
- Authors
- Publication date
- Relevance score and matched keywords
- DOI (when available)
- Link to full paper
- Abstract (in full reports)

## Project Structure

```
research-weekly-feed/
├── config/
│   ├── keywords.yaml          # Keywords and ArXiv categories
│   ├── sources.yaml           # Journal RSS/API configurations
│   ├── llm.yaml.template      # LLM configuration template
│   └── llm.yaml               # LLM configuration (create from template)
├── outputs/                   # Generated reports
├── .cache/llm_decisions/      # LLM scoring cache
├── src/
│   ├── fetchers/
│   │   ├── base_fetcher.py   # Base class for all fetchers
│   │   ├── arxiv_fetcher.py  # ArXiv API integration
│   │   ├── rss_fetcher.py    # RSS feed parser (SAGE, Nature, etc.)
│   │   └── crossref_fetcher.py # CrossRef API integration
│   ├── config.py             # Configuration management
│   ├── filter.py             # Keyword filtering & scoring
│   ├── llm_scorer.py         # LLM-based semantic scoring
│   └── report_generator.py   # Markdown report generation
└── main.py                    # CLI entry point
```

## Requirements

- Python 3.10+
- Dependencies: arxiv, feedparser, requests, pyyaml, openai
- For LLM scoring: Aliyun DashScope API key OR Azure OpenAI credentials

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run linting:
```bash
ruff check .
```

## Examples

Fetch high-relevance papers from all sources (last 14 days):
```bash
python main.py --days 14 --min-score 20
```

Generate weekly report from sociology journals only:
```bash
python main.py --days 7 --source sage --summary
```

Check Nature for recent papers on computational methods:
```bash
python main.py --days 3 --source nature --min-score 5
```

**NEW: Use LLM for semantic relevance scoring:**
```bash
# Use LLM scoring with DashScope
python main.py --use-llm --days 7 --min-score 50

# Use LLM scoring with Azure OpenAI
python main.py --use-llm --llm-config config/llm.yaml --days 7

# Generate LLM-scored summary report
python main.py --use-llm --summary --days 14
```

## Notes

- Some RSS feeds may have occasional parsing errors (SAGE journals, Social Forces)
- CrossRef API is rate-limited (50 requests/second, but we use 0.5s delay)
- ArXiv has 3-second delay between requests to respect API limits
- Not all journal RSS feeds include abstracts
- Date filtering may vary by source (some journals have delayed RSS updates)

**LLM Scoring Notes:**
- LLM decisions are cached to avoid re-scoring the same papers
- Cache is stored in `.cache/llm_decisions/` directory
- Use `--min-score 50` or higher for LLM scoring (0-100 scale)
- LLM scoring works even with papers that have no abstracts
- API costs apply for LLM calls (cached results are free)

## License

MIT License
