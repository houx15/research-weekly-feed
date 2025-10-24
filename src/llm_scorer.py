"""LLM-based paper relevance scoring using Aliyun DashScope or Azure OpenAI."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class LLMPaperScorer:
    """Scores paper relevance using LLM instead of keyword matching."""

    def __init__(
        self,
        api_key: str,
        model: str,
        research_interests: str,
        provider: str = "dashscope",
        cache_dir: str = ".cache/llm_decisions",
    ):
        """Initialize LLM scorer.

        Args:
            api_key: API key for LLM service
            model: Model name (e.g., 'qwen-plus' for DashScope, 'gpt-4o-mini' for Azure)
            research_interests: Description of research interests
            provider: 'dashscope' or 'azure'
            cache_dir: Directory to cache LLM decisions
        """
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.research_interests = research_interests
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize client based on provider
        if provider == "dashscope":
            from openai import OpenAI
            # DashScope uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        elif provider == "azure":
            from openai import AzureOpenAI
            # For Azure, model contains endpoint and deployment info
            # Format: "endpoint|deployment"
            parts = model.split("|")
            self.azure_endpoint = parts[0] if len(parts) > 0 else ""
            self.azure_deployment = parts[1] if len(parts) > 1 else model
            self.client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=api_key,
                api_version="2024-08-01-preview",
            )

        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0

    def _get_cache_key(self, title: str, abstract: str) -> str:
        """Generate cache key from paper title and abstract.

        Args:
            title: Paper title
            abstract: Paper abstract

        Returns:
            MD5 hash as cache key
        """
        content = f"{title}|{abstract}"
        return hashlib.md5(content.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load decision from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached decision or None
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                self.cache_hits += 1
                return json.load(f)
        return None

    def _save_to_cache(self, cache_key: str, decision: Dict[str, Any]) -> None:
        """Save decision to cache with timestamp.

        Args:
            cache_key: Cache key
            decision: Decision to cache
        """
        from datetime import datetime

        cache_file = self.cache_dir / f"{cache_key}.json"

        # Add timestamp and compact format to save space
        cache_data = {
            **decision,
            "cached_at": datetime.now().isoformat(),
        }

        # Use compact JSON format (no indentation) to save disk space
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, separators=(',', ':'))

    def clean_old_cache(self, days: int = 90) -> int:
        """Remove cache entries older than specified days.

        Args:
            days: Number of days to keep (default: 90)

        Returns:
            Number of cache files removed
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        removed_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    if "cached_at" in data:
                        cached_time = datetime.fromisoformat(data["cached_at"])
                        if cached_time < cutoff_date:
                            cache_file.unlink()
                            removed_count += 1
            except Exception:
                # Skip problematic cache files
                pass

        return removed_count

    def _create_prompt(self, title: str, abstract: str, source: str) -> str:
        """Create prompt for LLM.

        Args:
            title: Paper title
            abstract: Paper abstract (may be empty)
            source: Paper source

        Returns:
            Formatted prompt
        """
        # Build paper info using whatever is available
        paper_info = f"Source: {source}\nTitle: {title}"
        if abstract and abstract.strip():
            paper_info += f"\nAbstract: {abstract}"
        else:
            paper_info += "\nAbstract: [Not available - please evaluate based on title only]"

        prompt = f"""You are an expert research assistant helping to filter academic papers.

Research Interests:
{self.research_interests}

Paper to Evaluate:
{paper_info}

Task: Determine if this paper is relevant to the research interests above.

Respond with a JSON object with the following fields:
- "relevant": boolean (true if relevant, false if not)
- "confidence": string ("high", "medium", "low")
- "score": integer (0-100, where 100 is highly relevant)
- "reasoning": string (brief explanation of why this paper is or isn't relevant)
- "topics": list of strings (key topics from the paper that relate to research interests)

Only respond with the JSON object, no additional text."""

        return prompt

    def _call_dashscope(self, prompt: str) -> Dict[str, Any]:
        """Call Aliyun DashScope API via OpenAI-compatible endpoint.

        Args:
            prompt: Prompt to send

        Returns:
            Parsed JSON response
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert research assistant. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        content = response.choices[0].message.content
        # Try to extract JSON from response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {content}")

    def _call_azure(self, prompt: str) -> Dict[str, Any]:
        """Call Azure OpenAI API.

        Args:
            prompt: Prompt to send

        Returns:
            Parsed JSON response
        """
        response = self.client.chat.completions.create(
            model=self.azure_deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert research assistant. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def score_paper(self, paper: Any) -> Tuple[bool, int, Dict[str, Any]]:
        """Score a paper using LLM.

        Args:
            paper: Paper object with title, abstract, source

        Returns:
            Tuple of (is_relevant, score, metadata)
        """
        # Generate cache key
        cache_key = self._get_cache_key(paper.title, paper.abstract or "")

        # Check cache first
        cached = self._load_from_cache(cache_key)
        if cached:
            return (
                cached["relevant"],
                cached["score"],
                {
                    "confidence": cached["confidence"],
                    "reasoning": cached["reasoning"],
                    "topics": cached.get("topics", []),
                    "cached": True,
                },
            )

        self.cache_misses += 1

        # Call LLM - even if abstract is short/missing, use title
        try:
            prompt = self._create_prompt(
                paper.title,
                paper.abstract or "",
                paper.source
            )

            self.api_calls += 1

            if self.provider == "dashscope":
                decision = self._call_dashscope(prompt)
            elif self.provider == "azure":
                decision = self._call_azure(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            # Save to cache
            self._save_to_cache(cache_key, decision)

            return (
                decision["relevant"],
                decision["score"],
                {
                    "confidence": decision["confidence"],
                    "reasoning": decision["reasoning"],
                    "topics": decision.get("topics", []),
                    "cached": False,
                },
            )

        except Exception as e:
            print(f"  Warning: LLM API error for paper '{paper.title[:50]}...': {e}")
            # Return neutral score on error
            return False, 0, {"error": str(e), "cached": False}

    def score_papers_batch(
        self,
        papers: List[Any],
        min_score: int = 50,
    ) -> List[Any]:
        """Score multiple papers and filter by minimum score.

        Args:
            papers: List of Paper objects
            min_score: Minimum score to include (0-100)

        Returns:
            Filtered list of papers with LLM scores
        """
        filtered_papers = []

        print(f"Scoring {len(papers)} papers with LLM ({self.model} via {self.provider})...")
        print(f"Cache location: {self.cache_dir}")

        for i, paper in enumerate(papers, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(papers)} papers scored")

            relevant, score, metadata = self.score_paper(paper)

            if score >= min_score:
                # Store LLM metadata in paper
                paper.relevance_score = score
                paper.llm_metadata = metadata
                paper.matched_keywords = metadata.get("topics", [])
                filtered_papers.append(paper)

        # Sort by relevance score (highest first)
        filtered_papers.sort(key=lambda p: p.relevance_score, reverse=True)

        print(f"\nLLM Scoring Statistics:")
        print(f"  API calls: {self.api_calls}")
        print(f"  Cache hits: {self.cache_hits}")
        print(f"  Cache misses: {self.cache_misses}")
        if self.cache_hits + self.cache_misses > 0:
            print(f"  Cache hit rate: {self.cache_hits / (self.cache_hits + self.cache_misses) * 100:.1f}%")

        return filtered_papers

    def group_papers_by_relevance(
        self,
        papers: List[Any],
    ) -> Dict[str, List[Any]]:
        """Group papers by LLM relevance score.

        Args:
            papers: List of paper objects with relevance_score

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

            if score >= 75:
                groups["high"].append(paper)
            elif score >= 50:
                groups["medium"].append(paper)
            else:
                groups["low"].append(paper)

        return groups
