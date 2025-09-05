from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from ..cognition.memory import AgentState

S = TypeVar("S")  # State type


class PersistenceBackend(ABC, Generic[S]):
    """Abstract base class for persistence backends."""

    @abstractmethod
    async def save(self, key: str, state: S) -> None:
        """Save state with the given key."""
        pass

    @abstractmethod
    async def load(self, key: str, constructor: Callable[[dict[str, Any]], S]) -> S | None:
        """Load state with the given key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key."""
        pass

    @abstractmethod
    async def list_keys(self) -> list[str]:
        """List all available keys."""
        pass


class JSONFileBackend(PersistenceBackend[S]):
    """JSON file-based persistence backend."""

    def __init__(self, base_path: str | Path = "agent_states"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a key."""
        return self.base_path / f"{key}.json"

    async def save(self, key: str, state: S) -> None:
        """Save state to JSON file."""
        file_path = self._get_file_path(key)

        if isinstance(state, AgentState):
            data = state.to_dict()
        elif hasattr(state, "__dict__"):
            data = asdict(state)
        else:
            data = state

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def load(self, key: str, constructor: Callable[[dict[str, Any]], S]) -> S | None:
        """Load state from JSON file."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return constructor(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        return self._get_file_path(key).exists()

    async def delete(self, key: str) -> None:
        """Delete file."""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()

    async def list_keys(self) -> list[str]:
        """List all JSON files."""
        return [
            f.stem for f in self.base_path.glob("*.json")
        ]


class SQLiteBackend(PersistenceBackend[S]):
    """SQLite-based persistence backend."""

    def __init__(self, db_path: str | Path = "agent_states.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_timestamp
                AFTER UPDATE ON agent_states
                BEGIN
                    UPDATE agent_states SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
                END
            """)

    async def save(self, key: str, state: S) -> None:
        """Save state to SQLite."""
        if isinstance(state, AgentState):
            data = state.to_dict()
        elif hasattr(state, "__dict__"):
            data = asdict(state)
        else:
            data = state

        json_data = json.dumps(data, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_states (key, data)
                VALUES (?, ?)
            """, (key, json_data))

    async def load(self, key: str, constructor: Callable[[dict[str, Any]], S]) -> S | None:
        """Load state from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM agent_states WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row is None:
                return None

            try:
                data = json.loads(row[0])
                return constructor(data)
            except json.JSONDecodeError:
                return None

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM agent_states WHERE key = ?", (key,))
            return cursor.fetchone() is not None

    async def delete(self, key: str) -> None:
        """Delete key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM agent_states WHERE key = ?", (key,))

    async def list_keys(self) -> list[str]:
        """List all keys."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key FROM agent_states ORDER BY updated_at DESC")
            return [row[0] for row in cursor.fetchall()]


class RedisBackend(PersistenceBackend[S]):
    """Redis-based persistence backend (requires redis-py)."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, prefix: str = "agent:"):
        try:
            import redis.asyncio as redis
        except ImportError as e:
            raise ImportError("Redis backend requires redis-py: pip install redis") from e

        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.prefix = prefix

    def _get_key(self, key: str) -> str:
        """Get the full Redis key."""
        return f"{self.prefix}{key}"

    async def save(self, key: str, state: S) -> None:
        """Save state to Redis."""
        if isinstance(state, AgentState):
            data = state.to_dict()
        elif hasattr(state, "__dict__"):
            data = asdict(state)
        else:
            data = state

        json_data = json.dumps(data, ensure_ascii=False)
        await self.redis.set(self._get_key(key), json_data)

    async def load(self, key: str, constructor: Callable[[dict[str, Any]], S]) -> S | None:
        """Load state from Redis."""
        json_data = await self.redis.get(self._get_key(key))

        if json_data is None:
            return None

        try:
            data = json.loads(json_data)
            return constructor(data)
        except json.JSONDecodeError:
            return None

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.redis.exists(self._get_key(key)) > 0

    async def delete(self, key: str) -> None:
        """Delete key."""
        await self.redis.delete(self._get_key(key))

    async def list_keys(self) -> list[str]:
        """List all keys with our prefix."""
        pattern = f"{self.prefix}*"
        keys = await self.redis.keys(pattern)
        return [key[len(self.prefix):] for key in keys]


# Factory function for creating backends
def create_backend(
    backend_type: str = "json",
    **kwargs
) -> PersistenceBackend[S]:
    """Create a persistence backend.

    Args:
        backend_type: Type of backend ("json", "sqlite", "redis")
        **kwargs: Backend-specific configuration

    Returns:
        Configured persistence backend
    """
    if backend_type == "json":
        return JSONFileBackend(**kwargs)
    elif backend_type == "sqlite":
        return SQLiteBackend(**kwargs)
    elif backend_type == "redis":
        return RedisBackend(**kwargs)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")


# High-level persistence manager
class PersistenceManager(Generic[S]):
    """High-level persistence manager with automatic serialization."""

    def __init__(self, backend: PersistenceBackend[S]):
        self.backend = backend

    async def save_agent_state(self, agent_id: str, state: AgentState[S]) -> None:
        """Save an agent state."""
        await self.backend.save(f"agent:{agent_id}", state)

    async def load_agent_state(self, agent_id: str) -> AgentState[S] | None:
        """Load an agent state."""
        return await self.backend.load(f"agent:{agent_id}", AgentState.from_dict)

    async def save_checkpoint(self, checkpoint_id: str, state: S) -> None:
        """Save a checkpoint."""
        await self.backend.save(f"checkpoint:{checkpoint_id}", state)

    async def load_checkpoint(self, checkpoint_id: str, constructor: Callable[[dict[str, Any]], S]) -> S | None:
        """Load a checkpoint."""
        return await self.backend.load(f"checkpoint:{checkpoint_id}", constructor)

    async def list_agents(self) -> list[str]:
        """List all agent IDs."""
        keys = await self.backend.list_keys()
        return [key[6:] for key in keys if key.startswith("agent:")]

    async def list_checkpoints(self) -> list[str]:
        """List all checkpoint IDs."""
        keys = await self.backend.list_keys()
        return [key[11:] for key in keys if key.startswith("checkpoint:")]

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent state."""
        await self.backend.delete(f"agent:{agent_id}")

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint."""
        await self.backend.delete(f"checkpoint:{checkpoint_id}")


# Convenience functions
async def save_state(
    state: S,
    key: str,
    backend: PersistenceBackend[S] | None = None
) -> None:
    """Save a state with the given key."""
    if backend is None:
        backend = JSONFileBackend()
    await backend.save(key, state)


async def load_state(
    key: str,
    constructor: Callable[[dict[str, Any]], S],
    backend: PersistenceBackend[S] | None = None
) -> S | None:
    """Load a state with the given key."""
    if backend is None:
        backend = JSONFileBackend()
    return await backend.load(key, constructor)
