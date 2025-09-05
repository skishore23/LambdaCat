from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from ..core.effect import Effect, with_trace
from ..core.instruments import get_observability


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for LLM adapter."""

    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_jitter: float = 0.1
    # Budget tracking
    max_tokens_budget: int | None = None
    max_cost_budget: float | None = None
    cost_per_token: float = 0.0001  # Default cost per token


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str
    response_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "response_time_ms": self.response_time_ms
        }


class RateLimiter:
    """Token bucket rate limiter for LLM calls."""

    def __init__(self, rate_per_second: float, burst_size: int | None = None):
        self.rate = rate_per_second
        self.burst_size = burst_size or int(rate_per_second * 2)
        self.tokens = self.burst_size
        self.last_update = time.perf_counter()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the rate limiter."""
        async with self._lock:
            now = time.perf_counter()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Wait if not enough tokens
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens


class CircuitBreaker:
    """Circuit breaker for LLM calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func, *args, **kwargs):
        """Call function through circuit breaker."""
        if self.state == "open":
            if time.perf_counter() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.perf_counter()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        config: LLMConfig
    ) -> LLMResponse:
        """Complete a prompt."""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Stream completion."""
        pass

    @abstractmethod
    async def batch_complete(
        self,
        prompts: list[str],
        config: LLMConfig
    ) -> list[LLMResponse]:
        """Complete multiple prompts in batch."""
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or ["This is a mock response."]
        self.call_count = 0

    async def complete(
        self,
        prompt: str,
        config: LLMConfig
    ) -> LLMResponse:
        """Mock completion."""
        await asyncio.sleep(0.1)  # Simulate network delay

        self.call_count += 1
        response_text = self.responses[self.call_count % len(self.responses)]

        return LLMResponse(
            content=response_text,
            model=config.model,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": len(response_text.split())},
            finish_reason="stop",
            response_time_ms=100.0
        )

    async def stream(
        self,
        prompt: str,
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Mock streaming."""
        response_text = self.responses[self.call_count % len(self.responses)]
        words = response_text.split()

        for word in words:
            await asyncio.sleep(0.01)  # Simulate streaming delay
            yield word + " "

    async def batch_complete(
        self,
        prompts: list[str],
        config: LLMConfig
    ) -> list[LLMResponse]:
        """Mock batch completion."""
        responses = []
        for prompt in prompts:
            response = await self.complete(prompt, config)
            responses.append(response)
        return responses


class OpenAILLMClient(LLMClient):
    """OpenAI LLM client."""

    def __init__(self, api_key: str, base_url: str | None = None):
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
        except ImportError as e:
            raise ImportError("OpenAI client requires openai package: pip install openai") from e

    async def complete(
        self,
        prompt: str,
        config: LLMConfig
    ) -> LLMResponse:
        """Complete using OpenAI API."""
        start_time = time.perf_counter()

        try:
            response = await self.client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop
            )

            response_time_ms = (time.perf_counter() - start_time) * 1000

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason or "stop",
                response_time_ms=response_time_ms
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}") from e

    async def stream(
        self,
        prompt: str,
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Stream using OpenAI API."""
        try:
            stream = await self.client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stop=config.stop,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {e}") from e

    async def batch_complete(
        self,
        prompts: list[str],
        config: LLMConfig
    ) -> list[LLMResponse]:
        """Complete multiple prompts in batch using OpenAI API."""
        start_time = time.perf_counter()

        try:
            # Create batch requests
            batch_requests = []
            for prompt in prompts:
                batch_requests.append({
                    "custom_id": f"batch_{len(batch_requests)}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                        "top_p": config.top_p,
                        "frequency_penalty": config.frequency_penalty,
                        "presence_penalty": config.presence_penalty,
                        "stop": config.stop
                    }
                })

            # Submit batch request
            batch_response = await self.client.batches.create(
                requests=batch_requests,
                completion_window="24h"
            )

            # Wait for batch completion (simplified - in practice you'd poll)
            await asyncio.sleep(1.0)  # Simulate batch processing time

            # Retrieve batch results
            _batch_result = await self.client.batches.retrieve(batch_response.id)

            responses = []
            for _i, prompt in enumerate(prompts):
                # For simplicity, create individual responses
                # In practice, you'd parse the batch result
                response = await self.complete(prompt, config)
                responses.append(response)

            return responses

        except Exception:
            # Fallback to individual requests if batch fails
            responses = []
            for prompt in prompts:
                try:
                    response = await self.complete(prompt, config)
                    responses.append(response)
                except Exception as individual_error:
                    # Create error response
                    error_response = LLMResponse(
                        content=f"Error: {individual_error}",
                        model=config.model,
                        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        finish_reason="error",
                        response_time_ms=(time.perf_counter() - start_time) * 1000
                    )
                    responses.append(error_response)

            return responses


class LLMAdapter:
    """LLM adapter with retries, rate limiting, circuit breaking, and budget tracking."""

    def __init__(
        self,
        client: LLMClient,
        config: LLMConfig,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None
    ):
        self.client = client
        self.config = config
        self.rate_limiter = rate_limiter or RateLimiter(rate_per_second=3.0)
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.obs = get_observability()
        # Budget tracking
        self.total_tokens_used = 0
        self.total_cost = 0.0

    async def complete(
        self,
        prompt: str,
        config_override: LLMConfig | None = None
    ) -> LLMResponse:
        """Complete a prompt with retries, rate limiting, and budget tracking."""
        config = config_override or self.config

        # Check budget constraints
        if config.max_tokens_budget and self.total_tokens_used >= config.max_tokens_budget:
            raise Exception(f"Token budget exceeded: {self.total_tokens_used}/{config.max_tokens_budget}")

        if config.max_cost_budget and self.total_cost >= config.max_cost_budget:
            raise Exception(f"Cost budget exceeded: ${self.total_cost:.4f}/${config.max_cost_budget:.4f}")

        async def _complete_with_retries() -> LLMResponse:
            for attempt in range(config.max_retries):
                try:
                    # Rate limiting
                    await self.rate_limiter.acquire()

                    # Circuit breaker
                    response = await self.circuit_breaker.call(
                        self.client.complete,
                        prompt,
                        config
                    )

                    # Record metrics
                    self.obs.counter("llm_completions_total", tags={"model": config.model})
                    self.obs.histogram("llm_response_time_ms", response.response_time_ms, tags={"model": config.model})
                    self.obs.histogram("llm_tokens_used", response.usage.get("total_tokens", 0), tags={"model": config.model})

                    # Update budget tracking
                    tokens_used = response.usage.get("total_tokens", 0)
                    self.total_tokens_used += tokens_used
                    self.total_cost += tokens_used * config.cost_per_token

                    return response

                except Exception as e:
                    if attempt == config.max_retries - 1:
                        self.obs.counter("llm_errors_total", tags={"model": config.model, "error": type(e).__name__})
                        raise e

                    # Exponential backoff with jitter
                    delay = config.retry_delay * (2 ** attempt) * (1 + random.uniform(0, config.retry_jitter))
                    await asyncio.sleep(delay)

            raise Exception("Max retries exceeded")

        return await _complete_with_retries()

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status."""
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "max_tokens_budget": self.config.max_tokens_budget,
            "max_cost_budget": self.config.max_cost_budget,
            "tokens_remaining": (
                self.config.max_tokens_budget - self.total_tokens_used
                if self.config.max_tokens_budget else None
            ),
            "cost_remaining": (
                self.config.max_cost_budget - self.total_cost
                if self.config.max_cost_budget else None
            )
        }

    async def stream(
        self,
        prompt: str,
        config_override: LLMConfig | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream completion with rate limiting."""
        config = config_override or self.config

        # Rate limiting
        await self.rate_limiter.acquire()

        try:
            async for chunk in self.client.stream(prompt, config):
                yield chunk
        except Exception as e:
            self.obs.counter("llm_streaming_errors_total", tags={"model": config.model, "error": type(e).__name__})
            raise e

    async def batch_complete(
        self,
        prompts: list[str],
        config_override: LLMConfig | None = None
    ) -> list[LLMResponse]:
        """Complete multiple prompts in batch with rate limiting."""
        config = config_override or self.config

        # Check budget before batch processing
        if config.max_tokens_budget and self.total_tokens_used >= config.max_tokens_budget:
            raise Exception("Token budget exceeded")
        if config.max_cost_budget and self.total_cost >= config.max_cost_budget:
            raise Exception("Cost budget exceeded")

        # Rate limiting for batch
        await self.rate_limiter.acquire(len(prompts))

        async def _batch_with_retries():
            for attempt in range(config.max_retries + 1):
                try:
                    responses = await self.circuit_breaker.call(
                        self.client.batch_complete, prompts, config
                    )

                    # Record metrics
                    self.obs.counter("llm_batch_completions_total", len(prompts), tags={"model": config.model})

                    # Update budget tracking
                    for response in responses:
                        tokens_used = response.usage.get("total_tokens", 0)
                        self.total_tokens_used += tokens_used
                        self.total_cost += tokens_used * config.cost_per_token
                        self.obs.histogram("llm_response_time_ms", response.response_time_ms, tags={"model": config.model})
                        self.obs.histogram("llm_tokens_used", tokens_used, tags={"model": config.model})

                    return responses

                except Exception as e:
                    if attempt == config.max_retries - 1:
                        self.obs.counter("llm_batch_errors_total", tags={"model": config.model, "error": type(e).__name__})
                        raise e

                    # Exponential backoff with jitter
                    delay = config.retry_delay * (2 ** attempt) * (1 + random.uniform(0, config.retry_jitter))
                    await asyncio.sleep(delay)

            raise Exception("Max retries exceeded")

        return await _batch_with_retries()

    def create_effect(
        self,
        prompt_key: str = "prompt",
        response_key: str = "response",
        config_override: LLMConfig | None = None
    ) -> Effect[dict[str, Any], dict[str, Any]]:
        """Create an Effect for LLM completion."""

        async def llm_effect(state: dict[str, Any], ctx: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
            try:
                prompt = state.get(prompt_key, "")
                if not prompt:
                    return (state, [], {"error": "No prompt provided"})

                response = await self.complete(prompt, config_override)

                # Update state with response
                new_state = dict(state)
                new_state[response_key] = response.content
                new_state[f"{response_key}_metadata"] = response.to_dict()

                return (new_state, [], {"success": True, "response": response.content})

            except Exception as e:
                return (state, [{"span": "llm_error", "error": str(e)}], {"error": str(e)})

        return with_trace("llm_complete", Effect(llm_effect))


# Factory functions
def create_mock_llm(
    responses: list[str] | None = None,
    config: LLMConfig | None = None
) -> LLMAdapter:
    """Create a mock LLM adapter for testing."""
    client = MockLLMClient(responses)
    config = config or LLMConfig()
    return LLMAdapter(client, config)


def create_openai_llm(
    api_key: str,
    config: LLMConfig | None = None,
    rate_per_second: float = 3.0
) -> LLMAdapter:
    """Create an OpenAI LLM adapter."""
    client = OpenAILLMClient(api_key)
    config = config or LLMConfig()
    rate_limiter = RateLimiter(rate_per_second)
    return LLMAdapter(client, config, rate_limiter)


# Convenience functions for common patterns
def ask_llm(
    prompt: str,
    llm: LLMAdapter,
    config_override: LLMConfig | None = None
    ) -> Effect[dict[str, Any], str]:
    """Create an Effect that asks the LLM a question."""

    async def ask_effect(state: dict[str, Any], ctx: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
        try:
            response = await llm.complete(prompt, config_override)
            return (state, [], {"success": True, "answer": response.content})
        except Exception as e:
            return (state, [{"span": "ask_llm_error", "error": str(e)}], {"error": str(e)})

    return with_trace("ask_llm", Effect(ask_effect))


def stream_llm(
    prompt: str,
    llm: LLMAdapter,
    config_override: LLMConfig | None = None
    ) -> Effect[dict[str, Any], list[str]]:
    """Create an Effect that streams from the LLM."""

    async def stream_effect(state: dict[str, Any], ctx: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
        try:
            chunks = []
            async for chunk in llm.stream(prompt, config_override):
                chunks.append(chunk)

            return (state, [], {"success": True, "chunks": chunks})
        except Exception as e:
            return (state, [{"span": "stream_llm_error", "error": str(e)}], {"error": str(e)})

    return with_trace("stream_llm", Effect(stream_effect))
