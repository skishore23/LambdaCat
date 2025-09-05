"""Simple message bus for agent communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from ..core.bus import Message


class SimpleBus:
    """Simple in-process pub/sub bus for agent communication."""

    def __init__(self) -> None:
        self.topics: dict[str, list[asyncio.Queue[Message[Any]]]] = defaultdict(list)

    async def subscribe(self, topic: str) -> asyncio.Queue[Message[Any]]:
        """Subscribe to a topic and get a queue for messages."""
        queue: asyncio.Queue[Message[Any]] = asyncio.Queue()
        self.topics[topic].append(queue)
        return queue

    async def publish(self, topic: str, message: Message[Any]) -> None:
        """Publish a message to a topic."""
        if topic not in self.topics:
            return

        # Send to all subscribers
        for queue in self.topics[topic]:
            try:
                await queue.put(message)
            except Exception:
                # Skip failed deliveries
                pass

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[Message[Any]]) -> None:
        """Unsubscribe from a topic."""
        if topic in self.topics and queue in self.topics[topic]:
            self.topics[topic].remove(queue)
