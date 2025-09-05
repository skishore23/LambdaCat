from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Span:
    """A tracing span with timing and metadata."""

    id: str
    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    parent_id: str | None = None
    trace_id: str | None = None

    def finish(self) -> Span:
        """Finish the span and calculate duration."""
        end_time = time.perf_counter()
        duration_ms = (end_time - self.start_time) * 1000

        return Span(
            id=self.id,
            name=self.name,
            start_time=self.start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            tags=self.tags,
            logs=self.logs,
            parent_id=self.parent_id,
            trace_id=self.trace_id
        )

    def add_log(self, message: str, **kwargs: Any) -> Span:
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": time.perf_counter(),
            "message": message,
            **kwargs
        }
        new_logs = list(self.logs) + [log_entry]

        return Span(
            id=self.id,
            name=self.name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=self.duration_ms,
            tags=self.tags,
            logs=new_logs,
            parent_id=self.parent_id,
            trace_id=self.trace_id
        )

    def add_tag(self, key: str, value: Any) -> Span:
        """Add a tag to the span."""
        new_tags = dict(self.tags)
        new_tags[key] = value

        return Span(
            id=self.id,
            name=self.name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=self.duration_ms,
            tags=new_tags,
            logs=self.logs,
            parent_id=self.parent_id,
            trace_id=self.trace_id
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "parent_id": self.parent_id,
            "trace_id": self.trace_id
        }


@dataclass(frozen=True)
class Metric:
    """A metric measurement."""

    name: str
    value: float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)
    unit: str = "count"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "unit": self.unit
        }


class Tracer:
    """Tracing system for observability."""

    def __init__(self):
        self.spans: list[Span] = []
        self.active_spans: dict[str, Span] = {}
        self.trace_id: str | None = None

    def start_trace(self, trace_id: str | None = None) -> str:
        """Start a new trace."""
        self.trace_id = trace_id or str(uuid4())
        return self.trace_id

    def start_span(
        self,
        name: str,
        parent_id: str | None = None,
        tags: dict[str, Any] | None = None
    ) -> Span:
        """Start a new span."""
        span_id = str(uuid4())
        self.active_spans.get(parent_id) if parent_id else None

        span = Span(
            id=span_id,
            name=name,
            start_time=time.perf_counter(),
            tags=tags or {},
            parent_id=parent_id,
            trace_id=self.trace_id
        )

        self.active_spans[span_id] = span
        return span

    def finish_span(self, span: Span) -> Span:
        """Finish a span and add it to the trace."""
        finished_span = span.finish()
        self.spans.append(finished_span)

        # Remove from active spans
        if span.id in self.active_spans:
            del self.active_spans[span.id]

        return finished_span

    def get_trace(self) -> list[Span]:
        """Get all spans in the current trace."""
        return list(self.spans)

    def clear_trace(self) -> None:
        """Clear the current trace."""
        self.spans.clear()
        self.active_spans.clear()
        self.trace_id = None

    def export_trace(self, format: str = "json") -> str:
        """Export the trace in the specified format."""
        if format == "json":
            return json.dumps([span.to_dict() for span in self.spans], indent=2)
        elif format == "text":
            lines = []
            for span in self.spans:
                lines.append(f"Span: {span.name} ({span.duration_ms:.2f}ms)")
                for key, value in span.tags.items():
                    lines.append(f"  {key}: {value}")
                for log in span.logs:
                    lines.append(f"  Log: {log['message']}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


class MetricsCollector:
    """Metrics collection system."""

    def __init__(self):
        self.metrics: list[Metric] = []
        self.counters: dict[str, float] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = {}

    def counter(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Record a counter metric."""
        self.counters[name] = self.counters.get(name, 0.0) + value

        metric = Metric(
            name=name,
            value=value,
            timestamp=time.perf_counter(),
            tags=tags or {},
            unit="count"
        )
        self.metrics.append(metric)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a gauge metric."""
        self.gauges[name] = value

        metric = Metric(
            name=name,
            value=value,
            timestamp=time.perf_counter(),
            tags=tags or {},
            unit="gauge"
        )
        self.metrics.append(metric)

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a histogram metric."""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

        metric = Metric(
            name=name,
            value=value,
            timestamp=time.perf_counter(),
            tags=tags or {},
            unit="histogram"
        )
        self.metrics.append(metric)

    def timer(self, name: str, tags: dict[str, str] | None = None) -> Timer:
        """Create a timer metric."""
        return Timer(self, name, tags)

    def get_metrics(self) -> list[Metric]:
        """Get all recorded metrics."""
        return list(self.metrics)

    def get_counters(self) -> dict[str, float]:
        """Get current counter values."""
        return dict(self.counters)

    def get_gauges(self) -> dict[str, float]:
        """Get current gauge values."""
        return dict(self.gauges)

    def get_histogram_stats(self, name: str) -> dict[str, float] | None:
        """Get histogram statistics."""
        if name not in self.histograms or not self.histograms[name]:
            return None

        values = self.histograms[name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "sum": sum(values)
        }

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in the specified format."""
        if format == "json":
            return json.dumps([metric.to_dict() for metric in self.metrics], indent=2)
        elif format == "prometheus":
            lines = []
            for metric in self.metrics:
                tags_str = ",".join(f"{k}={v}" for k, v in metric.tags.items())
                if tags_str:
                    tags_str = "{" + tags_str + "}"
                lines.append(f"{metric.name}{tags_str} {metric.value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


class Timer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str, tags: dict[str, str] | None = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time: float | None = None

    def __enter__(self) -> Timer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.collector.histogram(f"{self.name}_duration_ms", duration_ms, self.tags)

    async def __aenter__(self) -> Timer:
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.collector.histogram(f"{self.name}_duration_ms", duration_ms, self.tags)


class ObservabilityManager:
    """Central observability manager."""

    def __init__(self):
        self.tracer = Tracer()
        self.metrics = MetricsCollector()
        self.enabled = True

    def start_trace(self, trace_id: str | None = None) -> str:
        """Start a new trace."""
        return self.tracer.start_trace(trace_id)

    def start_span(
        self,
        name: str,
        parent_id: str | None = None,
        tags: dict[str, Any] | None = None
    ) -> Span:
        """Start a new span."""
        return self.tracer.start_span(name, parent_id, tags)

    def finish_span(self, span: Span) -> Span:
        """Finish a span."""
        return self.tracer.finish_span(span)

    def counter(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Record a counter metric."""
        if self.enabled:
            self.metrics.counter(name, value, tags)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a gauge metric."""
        if self.enabled:
            self.metrics.gauge(name, value, tags)

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a histogram metric."""
        if self.enabled:
            self.metrics.histogram(name, value, tags)

    def timer(self, name: str, tags: dict[str, str] | None = None) -> Timer:
        """Create a timer metric."""
        return self.metrics.timer(name, tags)

    def get_trace(self) -> list[Span]:
        """Get the current trace."""
        return self.tracer.get_trace()

    def get_metrics(self) -> list[Metric]:
        """Get all metrics."""
        return self.metrics.get_metrics()

    def export_trace(self, format: str = "json") -> str:
        """Export the trace."""
        return self.tracer.export_trace(format)

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics."""
        return self.metrics.export_metrics(format)

    def clear_all(self) -> None:
        """Clear all observability data."""
        self.tracer.clear_trace()
        self.metrics.clear_metrics()

    def disable(self) -> None:
        """Disable observability collection."""
        self.enabled = False

    def enable(self) -> None:
        """Enable observability collection."""
        self.enabled = True


# Global observability manager
_global_obs = ObservabilityManager()


def get_observability() -> ObservabilityManager:
    """Get the global observability manager."""
    return _global_obs


# Context managers for easy usage
@contextmanager
def span(name: str, tags: dict[str, Any] | None = None):
    """Context manager for creating a span."""
    obs = get_observability()
    span_obj = obs.start_span(name, tags=tags)
    try:
        yield span_obj
    finally:
        obs.finish_span(span_obj)


@asynccontextmanager
async def async_span(name: str, tags: dict[str, Any] | None = None) -> AsyncGenerator[Span, None]:
    """Async context manager for creating a span."""
    obs = get_observability()
    span_obj = obs.start_span(name, tags=tags)
    try:
        yield span_obj
    finally:
        obs.finish_span(span_obj)


@contextmanager
def timer(name: str, tags: dict[str, str] | None = None):
    """Context manager for timing operations."""
    obs = get_observability()
    with obs.timer(name, tags) as timer_obj:
        yield timer_obj


@asynccontextmanager
async def async_timer(name: str, tags: dict[str, str] | None = None) -> AsyncGenerator[Timer, None]:
    """Async context manager for timing operations."""
    obs = get_observability()
    async with obs.timer(name, tags) as timer_obj:
        yield timer_obj


# Convenience functions
def trace(name: str, tags: dict[str, Any] | None = None):
    """Decorator for tracing functions."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with span(name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with span(name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def measure(name: str, tags: dict[str, str] | None = None):
    """Decorator for measuring function execution time."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with timer(name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with timer(name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator
