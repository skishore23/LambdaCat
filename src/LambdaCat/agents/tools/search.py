from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.effect import Effect, with_trace
from ..core.instruments import get_observability
from .http import HTTPAdapter, HTTPConfig


@dataclass(frozen=True)
class SearchResult:
    """A search result with metadata."""

    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        }


@dataclass(frozen=True)
class SearchQuery:
    """A search query with parameters."""

    query: str
    num_results: int = 10
    language: str = "en"
    region: str = "us"
    safe_search: str = "moderate"  # "off", "moderate", "strict"
    date_range: Optional[str] = None  # "past_day", "past_week", "past_month", "past_year"
    site_filter: Optional[str] = None
    file_type: Optional[str] = None  # "pdf", "doc", "ppt", etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "num_results": self.num_results,
            "language": self.language,
            "region": self.region,
            "safe_search": self.safe_search,
            "date_range": self.date_range,
            "site_filter": self.site_filter,
            "file_type": self.file_type
        }


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform a search and return results."""
        pass

    @abstractmethod
    async def search_stream(self, query: SearchQuery) -> AsyncGenerator[SearchResult, None]:
        """Stream search results as they become available."""
        pass


class MockSearchProvider(SearchProvider):
    """Mock search provider for testing."""

    def __init__(self, results: Optional[List[SearchResult]] = None):
        self.results = results or [
            SearchResult(
                title="Mock Result 1",
                url="https://example.com/result1",
                snippet="This is a mock search result for testing purposes.",
                source="mock",
                relevance_score=0.9
            ),
            SearchResult(
                title="Mock Result 2",
                url="https://example.com/result2",
                snippet="Another mock result with different content.",
                source="mock",
                relevance_score=0.8
            )
        ]

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Return mock results."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return self.results[:query.num_results]

    async def search_stream(self, query: SearchQuery) -> AsyncGenerator[SearchResult, None]:
        """Stream mock results."""
        for result in self.results[:query.num_results]:
            await asyncio.sleep(0.05)  # Simulate streaming delay
            yield result


class GoogleSearchProvider(SearchProvider):
    """Google Custom Search provider."""

    def __init__(
        self,
        api_key: str,
        search_engine_id: str,
        http_config: Optional[HTTPConfig] = None
    ):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.http = HTTPAdapter(http_config)
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Google Custom Search API."""
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query.query,
            "num": min(query.num_results, 10),  # Google limits to 10 per request
            "lr": f"lang_{query.language}",
            "cr": f"country{query.region.upper()}",
            "safe": query.safe_search,
        }

        if query.date_range:
            params["dateRestrict"] = query.date_range

        if query.site_filter:
            params["siteSearch"] = query.site_filter

        if query.file_type:
            params["fileType"] = query.file_type

        try:
            response = await self.http.get(self.base_url, params=params)
            data = response.content

            # Parse JSON response
            import json
            search_data = json.loads(data)

            results = []
            for item in search_data.get("items", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google",
                    relevance_score=1.0,  # Google doesn't provide relevance scores
                    metadata={
                        "display_link": item.get("displayLink", ""),
                        "formatted_url": item.get("formattedUrl", ""),
                        "pagemap": item.get("pagemap", {})
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            raise Exception(f"Google search failed: {e}")

    async def search_stream(self, query: SearchQuery) -> AsyncGenerator[SearchResult, None]:
        """Stream search results (not supported by Google API, so just return search results)."""
        results = await self.search(query)
        for result in results:
            yield result


class FirecrawlSearchProvider(SearchProvider):
    """Firecrawl.dev search provider for web scraping and search."""

    def __init__(
        self,
        api_key: str,
        http_config: Optional[HTTPConfig] = None
    ):
        self.api_key = api_key
        self.http = HTTPAdapter(http_config)
        self.base_url = "https://api.firecrawl.dev/v1/search"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Firecrawl API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "query": query.query,
            "limit": min(query.num_results, 20),  # Firecrawl limit
            "pageOptions": {
                "onlyMainContent": True,
                "includeHtml": False
            },
            "searchOptions": {
                "language": query.language,
                "region": query.region,
                "safeSearch": query.safe_search
            }
        }

        if query.date_range:
            # Convert date range to Firecrawl format
            date_mapping = {
                "past_day": "1d",
                "past_week": "1w",
                "past_month": "1m",
                "past_year": "1y"
            }
            payload["searchOptions"]["timeRange"] = date_mapping.get(query.date_range, "1m")

        if query.site_filter:
            payload["searchOptions"]["site"] = query.site_filter

        try:
            response = await self.http.post(
                self.base_url,
                json=payload,
                headers=headers
            )
            data = response.content

            # Parse JSON response
            import json
            search_data = json.loads(data)

            results = []
            for item in search_data.get("data", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="firecrawl",
                    relevance_score=item.get("score", 0.0),
                    metadata={
                        "published_date": item.get("publishedDate", ""),
                        "author": item.get("author", ""),
                        "language": item.get("language", ""),
                        "word_count": item.get("wordCount", 0)
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            raise Exception(f"Firecrawl search failed: {e}")

    async def search_stream(self, query: SearchQuery) -> AsyncGenerator[SearchResult, None]:
        """Stream search results (Firecrawl doesn't support streaming, so return search results)."""
        results = await self.search(query)
        for result in results:
            yield result


class BingSearchProvider(SearchProvider):
    """Bing Search provider."""

    def __init__(
        self,
        api_key: str,
        http_config: Optional[HTTPConfig] = None
    ):
        self.api_key = api_key
        self.http = HTTPAdapter(http_config)
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Bing Search API."""
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }

        params = {
            "q": query.query,
            "count": min(query.num_results, 50),  # Bing allows up to 50
            "mkt": f"{query.language}-{query.region.upper()}",
            "safeSearch": query.safe_search.title(),
        }

        if query.date_range:
            # Convert date range to Bing format
            date_mapping = {
                "past_day": "1d",
                "past_week": "1w",
                "past_month": "1m",
                "past_year": "1y"
            }
            params["freshness"] = date_mapping.get(query.date_range, "1m")

        if query.site_filter:
            params["site"] = query.site_filter

        if query.file_type:
            params["fileType"] = query.file_type

        try:
            response = await self.http.get(self.base_url, params=params, headers=headers)
            data = response.content

            # Parse JSON response
            import json
            search_data = json.loads(data)

            results = []
            for item in search_data.get("webPages", {}).get("value", []):
                result = SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source="bing",
                    relevance_score=item.get("rankingScore", 0.0),
                    metadata={
                        "display_url": item.get("displayUrl", ""),
                        "date_published": item.get("datePublished", ""),
                        "is_family_friendly": item.get("isFamilyFriendly", True)
                    }
                )
                results.append(result)

            return results

        except Exception as e:
            raise Exception(f"Bing search failed: {e}")

    async def search_stream(self, query: SearchQuery) -> AsyncGenerator[SearchResult, None]:
        """Stream search results (not supported by Bing API, so just return search results)."""
        results = await self.search(query)
        for result in results:
            yield result


class WebSearchAdapter:
    """High-level web search adapter with multiple providers."""

    def __init__(
        self,
        providers: List[SearchProvider],
        primary_provider: Optional[SearchProvider] = None
    ):
        self.providers = providers
        self.primary_provider = primary_provider or providers[0] if providers else None
        self.obs = get_observability()

    async def search(
        self,
        query: str,
        num_results: int = 10,
        provider: Optional[SearchProvider] = None,
        **kwargs
    ) -> List[SearchResult]:
        """Search using the specified or primary provider."""
        search_query = SearchQuery(
            query=query,
            num_results=num_results,
            **kwargs
        )

        provider = provider or self.primary_provider
        if not provider:
            raise ValueError("No search provider available")

        # Record metrics
        self.obs.counter("search_requests_total", tags={"provider": provider.__class__.__name__})

        try:
            results = await provider.search(search_query)

            # Record success metrics
            self.obs.counter("search_results_total", len(results), tags={"provider": provider.__class__.__name__})
            self.obs.histogram("search_results_count", len(results), tags={"provider": provider.__class__.__name__})

            return results

        except Exception as e:
            # Record error metrics
            self.obs.counter("search_errors_total", tags={"provider": provider.__class__.__name__, "error": type(e).__name__})
            raise e

    async def search_multiple(
        self,
        query: str,
        num_results_per_provider: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """Search using multiple providers and combine results."""
        search_query = SearchQuery(
            query=query,
            num_results=num_results_per_provider,
            **kwargs
        )

        # Search with all providers in parallel
        tasks = [provider.search(search_query) for provider in self.providers]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_results = []
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                self.obs.counter("search_provider_errors_total", tags={"provider": self.providers[i].__class__.__name__})
                continue

            all_results.extend(results)

        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        # Sort by relevance score
        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)

        return unique_results

    async def search_stream(
        self,
        query: str,
        num_results: int = 10,
        provider: Optional[SearchProvider] = None,
        **kwargs
    ) -> AsyncGenerator[SearchResult, None]:
        """Stream search results."""
        search_query = SearchQuery(
            query=query,
            num_results=num_results,
            **kwargs
        )

        provider = provider or self.primary_provider
        if not provider:
            raise ValueError("No search provider available")

        async for result in provider.search_stream(search_query):
            yield result

    def create_search_effect(
        self,
        query_key: str = "query",
        results_key: str = "search_results",
        num_results: int = 10
    ) -> Effect[Dict[str, Any], Dict[str, Any]]:
        """Create an Effect for web search."""

        async def search_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
            try:
                query = state.get(query_key, "")
                if not query:
                    return (state, [], {"error": "No query provided"})

                results = await self.search(query, num_results=num_results)

                # Convert results to dictionaries
                results_dict = [result.to_dict() for result in results]

                new_state = dict(state)
                new_state[results_key] = results_dict

                return (new_state, [], {"success": True, "results": results_dict})

            except Exception as e:
                return (state, [{"span": "web_search_error", "error": str(e)}], {"error": str(e)})

        return with_trace("web_search", Effect(search_effect))


# Factory functions
def create_mock_search_adapter() -> WebSearchAdapter:
    """Create a mock search adapter for testing."""
    provider = MockSearchProvider()
    return WebSearchAdapter([provider], provider)


def create_google_search_adapter(
    api_key: str,
    search_engine_id: str,
    http_config: Optional[HTTPConfig] = None
) -> WebSearchAdapter:
    """Create a Google search adapter."""
    provider = GoogleSearchProvider(api_key, search_engine_id, http_config)
    return WebSearchAdapter([provider], provider)


def create_firecrawl_search_adapter(
    api_key: str,
    http_config: Optional[HTTPConfig] = None
) -> WebSearchAdapter:
    """Create a Firecrawl search adapter."""
    provider = FirecrawlSearchProvider(api_key, http_config)
    return WebSearchAdapter([provider], provider)


def create_bing_search_adapter(
    api_key: str,
    http_config: Optional[HTTPConfig] = None
) -> WebSearchAdapter:
    """Create a Bing search adapter."""
    provider = BingSearchProvider(api_key, http_config)
    return WebSearchAdapter([provider], provider)


def create_multi_provider_search_adapter(
    providers: List[SearchProvider],
    primary_provider: Optional[SearchProvider] = None
) -> WebSearchAdapter:
    """Create a multi-provider search adapter."""
    return WebSearchAdapter(providers, primary_provider)


# Convenience functions
def search_web(
    query: str,
    adapter: WebSearchAdapter,
    num_results: int = 10
) -> Effect[Dict[str, Any], List[SearchResult]]:
    """Create an Effect that searches the web."""

    async def search_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
        try:
            results = await adapter.search(query, num_results=num_results)
            return (state, [], {"success": True, "results": results})
        except Exception as e:
            return (state, [{"span": "search_web_error", "error": str(e)}], {"error": str(e)})

    return with_trace("search_web", Effect(search_effect))
