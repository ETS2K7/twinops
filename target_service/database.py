import asyncio
import time
import uuid
from typing import Optional


class ConnectionPoolExhaustedError(Exception):
    pass


class Connection:
    def __init__(self, connection_id: str):
        self.id = connection_id
        self.created_at = time.time()
        self.last_query: Optional[str] = None


class DatabasePool:
    def __init__(self, max_connections: int = 5, timeout_seconds: float = 1.0):
        self.max_connections = max_connections
        self.timeout_seconds = timeout_seconds
        self._active_connections: dict[str, Connection] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_connections)
        self.wait_queue_length = 0

    @property
    def active_count(self) -> int:
        return len(self._active_connections)

    async def acquire(self) -> Connection:
        self.wait_queue_length += 1
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            active_ids = list(self._active_connections.keys())
            raise ConnectionPoolExhaustedError(
                f"ResourceRequest timed out after {self.timeout_seconds}s. "
                f"Connection pool saturated: {self.active_count}/{self.max_connections} active connections. "
                f"Active connection IDs: {active_ids}"
            )
        finally:
            self.wait_queue_length = max(0, self.wait_queue_length - 1)

        conn_id = f"conn_{uuid.uuid4().hex[:8]}"
        conn = Connection(conn_id)
        async with self._lock:
            self._active_connections[conn_id] = conn
        return conn

    async def release(self, connection: Connection) -> None:
        async with self._lock:
            if connection.id in self._active_connections:
                del self._active_connections[connection.id]
                self._semaphore.release()

    async def reset(self) -> None:
        async with self._lock:
            self._active_connections.clear()
            self._semaphore = asyncio.Semaphore(self.max_connections)
            self.wait_queue_length = 0

    def stats(self) -> dict:
        return {
            "max_connections": self.max_connections,
            "active_connections": self.active_count,
            "wait_queue_length": self.wait_queue_length,
            "utilization_percent": round((self.active_count / self.max_connections) * 100, 1),
        }
