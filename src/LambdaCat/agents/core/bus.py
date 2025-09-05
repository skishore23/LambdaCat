from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

T = TypeVar("T")  # Message type


@dataclass(frozen=True)
class Message(Generic[T]):
    """A message with metadata."""

    id: str
    topic: str
    payload: T
    sender: str
    timestamp: float
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        topic: str,
        payload: T,
        sender: str,
        reply_to: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Message[T]:
        """Create a new message."""
        import time
        return cls(
            id=str(uuid4()),
            topic=topic,
            payload=payload,
            sender=sender,
            timestamp=time.time(),
            reply_to=reply_to,
            correlation_id=correlation_id
        )


class MessageHandler(ABC, Generic[T]):
    """Abstract message handler."""

    @abstractmethod
    async def handle(self, message: Message[T]) -> None:
        """Handle a message."""
        pass


class MessageBus:
    """Asynchronous message bus for multi-agent communication.
    
    Supports:
    - Topic-based pub/sub
    - Point-to-point messaging
    - Request/reply patterns
    - Message persistence
    - Backpressure handling
    """

    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.topics: Dict[str, List[asyncio.Queue[Message[Any]]]] = defaultdict(list)
        self.handlers: Dict[str, List[MessageHandler[Any]]] = defaultdict(list)
        self.agent_queues: Dict[str, asyncio.Queue[Message[Any]]] = {}
        self.running = False
        self._tasks: List[asyncio.Task[None]] = []

    async def start(self) -> None:
        """Start the message bus."""
        if self.running:
            return

        self.running = True
        # Start background tasks for message processing
        self._tasks = [
            asyncio.create_task(self._process_messages())
        ]

    async def stop(self) -> None:
        """Stop the message bus."""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def subscribe(self, topic: str) -> asyncio.Queue[Message[Any]]:
        """Subscribe to a topic and get a queue for messages."""
        queue = asyncio.Queue(maxsize=self.max_queue_size)
        self.topics[topic].append(queue)
        return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[Message[Any]]) -> None:
        """Unsubscribe from a topic."""
        if topic in self.topics and queue in self.topics[topic]:
            self.topics[topic].remove(queue)

    async def publish(self, topic: str, message: Message[Any]) -> None:
        """Publish a message to a topic."""
        if topic not in self.topics:
            return

        # Send to all subscribers
        for queue in self.topics[topic]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Handle backpressure by dropping oldest message
                try:
                    queue.get_nowait()
                    queue.put_nowait(message)
                except asyncio.QueueEmpty:
                    pass

    async def send(self, agent_id: str, message: Message[Any]) -> None:
        """Send a message directly to an agent."""
        if agent_id not in self.agent_queues:
            # Create queue for agent if it doesn't exist
            self.agent_queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)

        try:
            self.agent_queues[agent_id].put_nowait(message)
        except asyncio.QueueFull:
            # Handle backpressure
            try:
                self.agent_queues[agent_id].get_nowait()
                self.agent_queues[agent_id].put_nowait(message)
            except asyncio.QueueEmpty:
                pass

    async def get_agent_queue(self, agent_id: str) -> asyncio.Queue[Message[Any]]:
        """Get the message queue for an agent."""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)
        return self.agent_queues[agent_id]

    async def register_handler(self, topic: str, handler: MessageHandler[Any]) -> None:
        """Register a message handler for a topic."""
        self.handlers[topic].append(handler)

    async def unregister_handler(self, topic: str, handler: MessageHandler[Any]) -> None:
        """Unregister a message handler."""
        if topic in self.handlers and handler in self.handlers[topic]:
            self.handlers[topic].remove(handler)

    async def _process_messages(self) -> None:
        """Background task to process messages with handlers."""
        while self.running:
            try:
                # Process handlers for all topics
                for topic, handlers in self.handlers.items():
                    if not handlers:
                        continue

                    # Get messages from topic queues
                    for queue in self.topics.get(topic, []):
                        try:
                            message = queue.get_nowait()

                            # Send to all handlers
                            for handler in handlers:
                                try:
                                    await handler.handle(message)
                                except Exception as e:
                                    # Log error but continue processing
                                    print(f"Handler error for topic {topic}: {e}")

                        except asyncio.QueueEmpty:
                            continue

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"Message processing error: {e}")
                await asyncio.sleep(0.1)


class RequestReplyBus(MessageBus):
    """Message bus with request/reply support."""

    def __init__(self, max_queue_size: int = 1000, reply_timeout: float = 30.0):
        super().__init__(max_queue_size)
        self.reply_timeout = reply_timeout
        self.pending_replies: Dict[str, asyncio.Future[Message[Any]]] = {}

    async def request(
        self,
        topic: str,
        payload: Any,
        sender: str,
        timeout: Optional[float] = None
    ) -> Message[Any]:
        """Send a request and wait for a reply."""
        correlation_id = str(uuid4())
        message = Message.create(
            topic=topic,
            payload=payload,
            sender=sender,
            correlation_id=correlation_id
        )

        # Create future for reply
        future: asyncio.Future[Message[Any]] = asyncio.Future()
        self.pending_replies[correlation_id] = future

        try:
            # Publish the request
            await self.publish(topic, message)

            # Wait for reply
            timeout = timeout or self.reply_timeout
            return await asyncio.wait_for(future, timeout=timeout)

        finally:
            # Clean up
            self.pending_replies.pop(correlation_id, None)

    async def reply(
        self,
        original_message: Message[Any],
        payload: Any,
        sender: str
    ) -> None:
        """Send a reply to a request."""
        if not original_message.correlation_id:
            return

        reply_message = Message.create(
            topic=original_message.reply_to or original_message.topic,
            payload=payload,
            sender=sender,
            correlation_id=original_message.correlation_id
        )

        # Send reply to original sender
        await self.send(original_message.sender, reply_message)

    async def _process_messages(self) -> None:
        """Process messages and handle replies."""
        while self.running:
            try:
                # Process all agent queues for replies
                for agent_id, queue in self.agent_queues.items():
                    try:
                        message = queue.get_nowait()

                        # Check if this is a reply
                        if message.correlation_id and message.correlation_id in self.pending_replies:
                            future = self.pending_replies[message.correlation_id]
                            if not future.done():
                                future.set_result(message)

                        # Process with handlers
                        for handler in self.handlers.get(message.topic, []):
                            try:
                                await handler.handle(message)
                            except Exception as e:
                                print(f"Handler error: {e}")

                    except asyncio.QueueEmpty:
                        continue

                # Process topic queues
                await super()._process_messages()

                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"Request-reply processing error: {e}")
                await asyncio.sleep(0.1)


# Agent communication helpers
class AgentCommunicator:
    """Helper class for agent communication."""

    def __init__(self, agent_id: str, bus: MessageBus):
        self.agent_id = agent_id
        self.bus = bus
        self._queue: Optional[asyncio.Queue[Message[Any]]] = None

    async def get_inbox(self) -> asyncio.Queue[Message[Any]]:
        """Get the agent's inbox queue."""
        if self._queue is None:
            self._queue = await self.bus.get_agent_queue(self.agent_id)
        return self._queue

    async def send_message(
        self,
        topic: str,
        payload: Any,
        reply_to: Optional[str] = None
    ) -> None:
        """Send a message to a topic."""
        message = Message.create(
            topic=topic,
            payload=payload,
            sender=self.agent_id,
            reply_to=reply_to
        )
        await self.bus.publish(topic, message)

    async def send_direct(
        self,
        target_agent: str,
        payload: Any,
        reply_to: Optional[str] = None
    ) -> None:
        """Send a message directly to another agent."""
        message = Message.create(
            topic="direct",
            payload=payload,
            sender=self.agent_id,
            reply_to=reply_to
        )
        await self.bus.send(target_agent, message)

    async def request(
        self,
        topic: str,
        payload: Any,
        timeout: Optional[float] = None
    ) -> Message[Any]:
        """Send a request and wait for reply."""
        if not isinstance(self.bus, RequestReplyBus):
            raise TypeError("Request-reply requires RequestReplyBus")

        return await self.bus.request(topic, payload, self.agent_id, timeout)

    async def reply(
        self,
        original_message: Message[Any],
        payload: Any
    ) -> None:
        """Reply to a message."""
        if not isinstance(self.bus, RequestReplyBus):
            raise TypeError("Request-reply requires RequestReplyBus")

        await self.bus.reply(original_message, payload, self.agent_id)


# Convenience functions
async def create_bus(
    bus_type: str = "basic",
    **kwargs
) -> MessageBus:
    """Create a message bus."""
    if bus_type == "basic":
        return MessageBus(**kwargs)
    elif bus_type == "request_reply":
        return RequestReplyBus(**kwargs)
    else:
        raise ValueError(f"Unknown bus type: {bus_type}")


async def create_agent_communicator(
    agent_id: str,
    bus: MessageBus
) -> AgentCommunicator:
    """Create an agent communicator."""
    return AgentCommunicator(agent_id, bus)
