from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import aiohttp
from aiohttp import ClientError, ClientTimeout

from ..core.effect import Effect, with_trace
from ..core.instruments import get_observability


@dataclass(frozen=True)
class HTTPConfig:
    """Configuration for HTTP adapter."""

    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_jitter: float = 0.1
    backoff_factor: float = 2.0
    max_redirects: int = 10
    headers: Optional[Dict[str, str]] = None
    verify_ssl: bool = True
    max_connections: int = 100
    max_keepalive_connections: int = 30
    keepalive_timeout: float = 30.0


@dataclass(frozen=True)
class HTTPResponse:
    """HTTP response wrapper."""

    status: int
    headers: Dict[str, str]
    content: str
    url: str
    response_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "headers": self.headers,
            "content": self.content,
            "url": self.url,
            "response_time_ms": self.response_time_ms
        }


class HTTPAdapter:
    """HTTP adapter with retries, rate limiting, and connection pooling."""

    def __init__(
        self,
        config: Optional[HTTPConfig] = None,
        session: Optional[aiohttp.ClientSession] = None
    ):
        self.config = config or HTTPConfig()
        self.session = session
        self.obs = get_observability()
        self._session_created = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_keepalive_connections,
                keepalive_timeout=self.config.keepalive_timeout,
                verify_ssl=self.config.verify_ssl
            )

            timeout = ClientTimeout(total=self.config.timeout)

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.config.headers
            )
            self._session_created = True

        return self.session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session and self._session_created:
            await self.session.close()
            self.session = None

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HTTPResponse:
        """Make a GET request."""
        return await self._request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HTTPResponse:
        """Make a POST request."""
        return await self._request("POST", url, data=data, json=json, headers=headers)

    async def put(
        self,
        url: str,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HTTPResponse:
        """Make a PUT request."""
        return await self._request("PUT", url, data=data, json=json, headers=headers)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> HTTPResponse:
        """Make a DELETE request."""
        return await self._request("DELETE", url, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HTTPResponse:
        """Make an HTTP request with retries."""

        async def _make_request() -> HTTPResponse:
            session = await self._get_session()
            start_time = time.perf_counter()

            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    allow_redirects=True,
                    max_redirects=self.config.max_redirects
                ) as response:
                    content = await response.text()
                    response_time_ms = (time.perf_counter() - start_time) * 1000

                    return HTTPResponse(
                        status=response.status,
                        headers=dict(response.headers),
                        content=content,
                        url=str(response.url),
                        response_time_ms=response_time_ms
                    )

            except ClientError as e:
                response_time_ms = (time.perf_counter() - start_time) * 1000
                raise Exception(f"HTTP {method} {url} failed: {e}")

        # Retry logic with exponential backoff
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                response = await _make_request()

                # Record metrics
                self.obs.counter("http_requests_total", tags={"method": method, "status": str(response.status)})
                self.obs.histogram("http_response_time_ms", response.response_time_ms, tags={"method": method})

                return response

            except Exception as e:
                last_exception = e

                if attempt == self.config.max_retries - 1:
                    self.obs.counter("http_errors_total", tags={"method": method, "error": type(e).__name__})
                    raise e

                # Exponential backoff with jitter
                delay = self.config.retry_delay * (self.config.backoff_factor ** attempt)
                jitter = random.uniform(0, self.config.retry_jitter)
                await asyncio.sleep(delay + jitter)

        raise last_exception

    def create_effect(
        self,
        method: str,
        url_key: str = "url",
        response_key: str = "response",
        params_key: Optional[str] = None,
        data_key: Optional[str] = None,
        json_key: Optional[str] = None,
        headers_key: Optional[str] = None
    ) -> Effect[Dict[str, Any], Dict[str, Any]]:
        """Create an Effect for HTTP requests."""

        async def http_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
            try:
                url = state.get(url_key, "")
                if not url:
                    return (state, [], {"error": "No URL provided"})

                # Extract request parameters
                params = state.get(params_key) if params_key else None
                data = state.get(data_key) if data_key else None
                json_data = state.get(json_key) if json_key else None
                headers = state.get(headers_key) if headers_key else None

                # Make request
                if method.upper() == "GET":
                    response = await self.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await self.post(url, data=data, json=json_data, headers=headers)
                elif method.upper() == "PUT":
                    response = await self.put(url, data=data, json=json_data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await self.delete(url, headers=headers)
                else:
                    return (state, [], {"error": f"Unsupported HTTP method: {method}"})

                # Update state with response
                new_state = dict(state)
                new_state[response_key] = response.content
                new_state[f"{response_key}_metadata"] = response.to_dict()

                return (new_state, [], {"success": True, "status": response.status})

            except Exception as e:
                return (state, [{"span": "http_error", "error": str(e)}], {"error": str(e)})

        return with_trace(f"http_{method.lower()}", Effect(http_effect))


# Convenience functions for common HTTP operations
def fetch_url(
    url: str,
    adapter: HTTPAdapter,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Effect[Dict[str, Any], str]:
    """Create an Effect that fetches a URL."""

    async def fetch_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
        try:
            response = await adapter.get(url, params=params, headers=headers)
            return (state, [], {"success": True, "content": response.content})
        except Exception as e:
            return (state, [{"span": "fetch_url_error", "error": str(e)}], {"error": str(e)})

    return with_trace("fetch_url", Effect(fetch_effect))


def post_data(
    url: str,
    data: Union[str, Dict[str, Any]],
    adapter: HTTPAdapter,
    headers: Optional[Dict[str, str]] = None
) -> Effect[Dict[str, Any], str]:
    """Create an Effect that posts data to a URL."""

    async def post_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
        try:
            response = await adapter.post(url, data=data, headers=headers)
            return (state, [], {"success": True, "content": response.content})
        except Exception as e:
            return (state, [{"span": "post_data_error", "error": str(e)}], {"error": str(e)})

    return with_trace("post_data", Effect(post_effect))


def post_json(
    url: str,
    json_data: Dict[str, Any],
    adapter: HTTPAdapter,
    headers: Optional[Dict[str, str]] = None
) -> Effect[Dict[str, Any], str]:
    """Create an Effect that posts JSON to a URL."""

    async def post_json_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
        try:
            response = await adapter.post(url, json=json_data, headers=headers)
            return (state, [], {"success": True, "content": response.content})
        except Exception as e:
            return (state, [{"span": "post_json_error", "error": str(e)}], {"error": str(e)})

    return with_trace("post_json", Effect(post_json_effect))


# Web search abstraction
class WebSearchAdapter:
    """Web search adapter using HTTP."""

    def __init__(
        self,
        search_url: str,
        api_key: Optional[str] = None,
        http_config: Optional[HTTPConfig] = None
    ):
        self.search_url = search_url
        self.api_key = api_key
        self.http = HTTPAdapter(http_config)

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Search the web."""
        params = {
            "q": query,
            "num": num_results,
            **kwargs
        }

        if self.api_key:
            params["key"] = self.api_key

        response = await self.http.get(self.search_url, params=params)

        # Parse response (this would be implementation-specific)
        # For now, return a mock structure
        return [
            {
                "title": f"Result {i}",
                "url": f"https://example.com/result{i}",
                "snippet": f"Snippet for result {i}"
            }
            for i in range(num_results)
        ]

    def create_search_effect(
        self,
        query_key: str = "query",
        results_key: str = "search_results"
    ) -> Effect[Dict[str, Any], Dict[str, Any]]:
        """Create an Effect for web search."""

        async def search_effect(state: Dict[str, Any], ctx: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]], Any]:
            try:
                query = state.get(query_key, "")
                if not query:
                    return (state, [], {"error": "No query provided"})

                results = await self.search(query)

                new_state = dict(state)
                new_state[results_key] = results

                return (new_state, [], {"success": True, "results": results})

            except Exception as e:
                return (state, [{"span": "web_search_error", "error": str(e)}], {"error": str(e)})

        return with_trace("web_search", Effect(search_effect))


# Factory functions
def create_http_adapter(
    config: Optional[HTTPConfig] = None,
    session: Optional[aiohttp.ClientSession] = None
) -> HTTPAdapter:
    """Create an HTTP adapter."""
    return HTTPAdapter(config, session)


def create_web_search_adapter(
    search_url: str,
    api_key: Optional[str] = None,
    http_config: Optional[HTTPConfig] = None
) -> WebSearchAdapter:
    """Create a web search adapter."""
    return WebSearchAdapter(search_url, api_key, http_config)
