"""Configuration management for the research paper aggregator."""

from pathlib import Path
from typing import Any, Dict, List, Union

import yaml


class Config:
    """Manages configuration loading from YAML files."""

    def __init__(
        self,
        config_path: Union[str, Path] = "config/keywords.yaml",
        sources_path: Union[str, Path] = "config/sources.yaml",
        llm_path: Union[str, Path] = "config/llm.yaml",
    ):
        """Initialize configuration from files.

        Args:
            config_path: Path to the keywords configuration YAML file
            sources_path: Path to the sources configuration YAML file
            llm_path: Path to the LLM configuration YAML file
        """
        self.config_path = Path(config_path)
        self.sources_path = Path(sources_path)
        self.llm_path = Path(llm_path)
        self._config: Dict[str, Any] = {}
        self._sources: Dict[str, Any] = {}
        self._llm: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from YAML files."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path) as f:
            self._config = yaml.safe_load(f)

        # Load sources configuration if it exists
        if self.sources_path.exists():
            with open(self.sources_path) as f:
                self._sources = yaml.safe_load(f)
        else:
            self._sources = {}

        # Load LLM configuration if it exists
        if self.llm_path.exists():
            with open(self.llm_path) as f:
                self._llm = yaml.safe_load(f)
        else:
            self._llm = {}

    @property
    def arxiv_categories(self) -> List[str]:
        """Get ArXiv categories to search."""
        return self._config.get("arxiv", {}).get("categories", [])

    @property
    def primary_keywords(self) -> List[str]:
        """Get primary keywords for filtering."""
        return self._config.get("keywords", {}).get("primary", [])

    @property
    def secondary_keywords(self) -> List[str]:
        """Get secondary keywords for filtering."""
        return self._config.get("keywords", {}).get("secondary", [])

    @property
    def all_keywords(self) -> List[str]:
        """Get all keywords combined."""
        return self.primary_keywords + self.secondary_keywords

    @property
    def default_days(self) -> int:
        """Get default number of days to look back."""
        return self._config.get("search", {}).get("default_days", 7)

    @property
    def max_results(self) -> int:
        """Get maximum results per category."""
        return self._config.get("search", {}).get("max_results", 100)

    @property
    def sage_journals(self) -> Dict[str, Dict[str, str]]:
        """Get SAGE journal configurations."""
        return self._sources.get("sage_journals", {})

    @property
    def nature_journals(self) -> Dict[str, Dict[str, str]]:
        """Get Nature journal configurations."""
        return self._sources.get("nature_journals", {})

    @property
    def other_journals(self) -> Dict[str, Dict[str, str]]:
        """Get other journal configurations (PNAS, Science, etc.)."""
        return self._sources.get("other_journals", {})

    @property
    def crossref_journals(self) -> Dict[str, Dict[str, str]]:
        """Get CrossRef journal configurations."""
        return self._sources.get("crossref_journals", {})

    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self._llm

    @property
    def azure_endpoint(self) -> str:
        """Get Azure OpenAI endpoint."""
        return self._llm.get("azure_openai", {}).get("endpoint", "")

    @property
    def azure_api_key(self) -> str:
        """Get Azure OpenAI API key."""
        return self._llm.get("azure_openai", {}).get("api_key", "")

    @property
    def azure_deployment(self) -> str:
        """Get Azure OpenAI deployment name."""
        return self._llm.get("azure_openai", {}).get("deployment", "gpt-4o-mini")

    @property
    def research_interests(self) -> str:
        """Get research interests for LLM."""
        return self._llm.get("research_interests", "")

    @property
    def llm_min_score(self) -> int:
        """Get LLM minimum score."""
        return self._llm.get("scoring", {}).get("min_score", 50)

    @property
    def llm_provider(self) -> str:
        """Get LLM provider (dashscope or azure)."""
        return self._llm.get("provider", "dashscope")

    @property
    def dashscope_api_key(self) -> str:
        """Get DashScope API key."""
        return self._llm.get("dashscope", {}).get("api_key", "")

    @property
    def dashscope_model(self) -> str:
        """Get DashScope model name."""
        return self._llm.get("dashscope", {}).get("model", "qwen-plus")
