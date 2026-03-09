import json
import queue
import threading
import time
from datetime import datetime, timezone


class EventBus:
    """SSE event bus for real-time pipeline progress updates."""

    def __init__(self):
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._history: list[dict] = []
        self._max_history = 100

    def subscribe(self) -> queue.Queue:
        q = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(self, event_type: str, data: dict):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass

    def get_history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return self._history[-limit:]

    def stream(self, q: queue.Queue):
        """Generator for SSE streaming."""
        try:
            while True:
                try:
                    event = q.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield f": keepalive {time.time()}\n\n"
        finally:
            self.unsubscribe(q)


event_bus = EventBus()
