#!/usr/bin/env python3
"""Main CLI for research paper aggregator."""

import argparse
import sys
from pathlib import Path
from typing import List

from src.config import Config
from src.fetchers.arxiv_fetcher import ArXivFetcher
from src.fetchers.base_fetcher import Paper
from src.fetchers.crossref_fetcher import CrossRefFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.filter import PaperFilter
from src.llm_scorer import LLMPaperScorer
from src.report_generator import MarkdownReportGenerator


def main():
    """Main entry point for the research paper aggregator."""
    parser = argparse.ArgumentParser(
        description="Fetch and filter research papers from multiple sources"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days to look back (default: from config)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/keywords.yaml",
        help="Path to keywords configuration file",
    )
    parser.add_argument(
        "--sources-config",
        type=str,
        default="config/sources.yaml",
        help="Path to sources configuration file",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=1,
        help="Minimum relevance score to include paper (default: 1)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate summary report instead of full report",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Output directory for reports (default: outputs)",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["all", "arxiv", "sage", "nature", "other", "crossref"],
        default="all",
        help="Source to fetch from (default: all)",
    )
    parser.add_argument(
        "--journal",
        type=str,
        help="Specific journal code to fetch (e.g., 'asr', 'nature', 'pnas')",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM (GPT-4o-mini) for semantic relevance scoring instead of keyword matching",
    )
    parser.add_argument(
        "--llm-config",
        type=str,
        default="config/llm.yaml",
        help="Path to LLM configuration file",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(args.config, args.sources_config, args.llm_config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Check LLM configuration if using LLM
    if args.use_llm:
        provider = config.llm_provider
        if provider == "dashscope":
            if not config.dashscope_api_key:
                print("Error: LLM mode requires DashScope API key in config/llm.yaml")
                print("Copy config/llm.yaml.template to config/llm.yaml and fill in your credentials")
                sys.exit(1)
        elif provider == "azure":
            if not config.azure_endpoint or not config.azure_api_key:
                print("Error: LLM mode requires Azure OpenAI configuration in config/llm.yaml")
                print("Copy config/llm.yaml.template to config/llm.yaml and fill in your credentials")
                sys.exit(1)
        else:
            print(f"Error: Unknown LLM provider '{provider}'. Use 'dashscope' or 'azure'")
            sys.exit(1)

    # Use default days from config if not specified
    days = args.days if args.days is not None else config.default_days

    print("=" * 80)
    print("Research Paper Aggregator - Phase 2")
    print("=" * 80)
    print(f"Configuration: {args.config}")
    print(f"Sources config: {args.sources_config}")
    print(f"Looking back: {days} days")
    print(f"Source filter: {args.source}")
    if args.journal:
        print(f"Journal filter: {args.journal}")
    print(f"Primary keywords: {len(config.primary_keywords)}")
    print(f"Secondary keywords: {len(config.secondary_keywords)}")
    print(f"Minimum score: {args.min_score}")
    print("=" * 80)

    # Step 1: Fetch papers from selected sources
    all_papers: List[Paper] = []

    if args.source in ["all", "arxiv"]:
        print("\n[Fetching from ArXiv...]")
        try:
            arxiv_fetcher = ArXivFetcher(
                categories=config.arxiv_categories,
                max_results=config.max_results,
            )
            arxiv_papers = arxiv_fetcher.fetch_papers(days=days)
            all_papers.extend(arxiv_papers)
            print(f"✓ ArXiv: {len(arxiv_papers)} papers")
        except Exception as e:
            print(f"✗ ArXiv error: {e}")

    if args.source in ["all", "sage"]:
        print("\n[Fetching from SAGE Journals...]")
        try:
            sage_fetcher = RSSFetcher(config.sage_journals, "SAGE")
            sage_papers = sage_fetcher.fetch_papers(days=days, specific_journal=args.journal)
            all_papers.extend(sage_papers)
            print(f"✓ SAGE: {len(sage_papers)} papers")
        except Exception as e:
            print(f"✗ SAGE error: {e}")

    if args.source in ["all", "nature"]:
        print("\n[Fetching from Nature Journals...]")
        try:
            nature_fetcher = RSSFetcher(config.nature_journals, "Nature")
            nature_papers = nature_fetcher.fetch_papers(days=days, specific_journal=args.journal)
            all_papers.extend(nature_papers)
            print(f"✓ Nature: {len(nature_papers)} papers")
        except Exception as e:
            print(f"✗ Nature error: {e}")

    if args.source in ["all", "other"]:
        print("\n[Fetching from Other Journals...]")
        try:
            other_fetcher = RSSFetcher(config.other_journals, "Other")
            other_papers = other_fetcher.fetch_papers(days=days, specific_journal=args.journal)
            all_papers.extend(other_papers)
            print(f"✓ Other journals: {len(other_papers)} papers")
        except Exception as e:
            print(f"✗ Other journals error: {e}")

    if args.source in ["all", "crossref"]:
        print("\n[Fetching from CrossRef API...]")
        try:
            crossref_fetcher = CrossRefFetcher(config.crossref_journals)
            crossref_papers = crossref_fetcher.fetch_papers(days=days, specific_journal=args.journal)
            all_papers.extend(crossref_papers)
            print(f"✓ CrossRef: {len(crossref_papers)} papers")
        except Exception as e:
            print(f"✗ CrossRef error: {e}")

    print(f"\n{'='*80}")
    print(f"Total papers fetched: {len(all_papers)}")
    print(f"{'='*80}")

    if not all_papers:
        print("\nNo papers found in the specified time range.")
        sys.exit(0)

    # Step 2: Filter and score papers
    if args.use_llm:
        provider = config.llm_provider
        if provider == "dashscope":
            print(f"\n[Scoring papers with LLM ({config.dashscope_model} via DashScope)...]")
            llm_scorer = LLMPaperScorer(
                api_key=config.dashscope_api_key,
                model=config.dashscope_model,
                research_interests=config.research_interests,
                provider="dashscope",
            )
        else:  # azure
            print(f"\n[Scoring papers with LLM ({config.azure_deployment} via Azure)...]")
            llm_scorer = LLMPaperScorer(
                api_key=config.azure_api_key,
                model=f"{config.azure_endpoint}|{config.azure_deployment}",
                research_interests=config.research_interests,
                provider="azure",
            )

        min_score = args.min_score if args.min_score > 1 else config.llm_min_score
        filtered_papers = llm_scorer.score_papers_batch(all_papers, min_score=min_score)
        print(f"✓ Found {len(filtered_papers)} relevant papers")

        if not filtered_papers:
            print("\nNo papers matched the LLM relevance criteria.")
            sys.exit(0)

        # Step 3: Group papers by LLM relevance
        print("\n[Grouping papers by LLM relevance...]")
        grouped_papers = llm_scorer.group_papers_by_relevance(filtered_papers)
        print(f"✓ High relevance (≥75): {len(grouped_papers['high'])} papers")
        print(f"✓ Medium relevance (50-74): {len(grouped_papers['medium'])} papers")
        print(f"✓ Low relevance (<50): {len(grouped_papers['low'])} papers")
    else:
        print("\n[Filtering papers by keywords...]")
        paper_filter = PaperFilter(
            primary_keywords=config.primary_keywords,
            secondary_keywords=config.secondary_keywords,
        )

        filtered_papers = paper_filter.filter_papers(all_papers, min_score=args.min_score)
        print(f"✓ Found {len(filtered_papers)} relevant papers")

        if not filtered_papers:
            print("\nNo papers matched the keyword criteria.")
            sys.exit(0)

        # Step 3: Group papers by relevance
        print("\n[Grouping papers by relevance...]")
        grouped_papers = paper_filter.group_papers_by_relevance(filtered_papers)
        print(f"✓ High relevance: {len(grouped_papers['high'])} papers")
        print(f"✓ Medium relevance: {len(grouped_papers['medium'])} papers")
        print(f"✓ Low relevance: {len(grouped_papers['low'])} papers")

    # Step 4: Generate report
    print("\n[Generating markdown report...]")
    generator = MarkdownReportGenerator(output_dir=args.output_dir)

    try:
        # Collect all source names
        sources = set(paper.source for paper in filtered_papers)

        if args.summary:
            report_path = generator.generate_summary_report(
                papers=filtered_papers,
                grouped_papers=grouped_papers,
                days=days,
            )
        else:
            report_path = generator.generate_report(
                papers=filtered_papers,
                grouped_papers=grouped_papers,
                days=days,
                sources=list(sources),
            )
        print(f"✓ Report saved to: {report_path}")
    except Exception as e:
        print(f"✗ Error generating report: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✓ Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
