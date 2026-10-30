"""EventBus and structured event dataclasses for decoupling core logic from UI."""
from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class Event:
    """Base event class."""
    timestamp: float = field(default_factory=time.time)


@dataclass
class LogMessage(Event):
    """Event for log notifications."""
    level: str = "INFO"
    message: str = ""


@dataclass
class TestStarted(Event):
    """Emitted when a test run begins."""
    mode: str = ""
    total_nodes: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCompleted(Event):
    """Emitted when a test run finishes."""
    mode: str = ""
    total_nodes: int = 0
    passed_nodes: int = 0
    duration_sec: float = 0.0


@dataclass
class BatchStarted(Event):
    """Emitted when a batch of nodes starts executing in xray."""
    batch_index: int = 0
    total_batches: int = 0
    batch_size: int = 0


@dataclass
class BatchProgress(Event):
    """Emitted during batch progress."""
    batch_index: int = 0
    current: int = 0
    total: int = 0
    node_id: str = ""
    success: bool = False
    details: str = ""


@dataclass
class BatchCompleted(Event):
    """Emitted when an xray batch completes."""
    batch_index: int = 0
    passed_count: int = 0
    failed_count: int = 0


@dataclass
class RoundStarted(Event):
    """Emitted when a speed tournament round begins."""
    round_num: int = 1
    pool_size: int = 0


@dataclass
class RoundProgress(Event):
    """Emitted during a speed tournament round."""
    round_num: int = 1
    completed: int = 0
    total: int = 0
    node_id: str = ""
    speed_mbps: float = 0.0
    success: bool = False
    node_tag: str = ""


@dataclass
class RoundCompleted(Event):
    """Emitted when a speed tournament round finishes."""
    round_num: int = 1
    passed_count: int = 0
    failed_count: int = 0
    eliminated_count: int = 0


@dataclass
class NodeTestingStarted(Event):
    """Emitted when a node begins active testing."""
    node_id: str = ""
    node_tag: str = ""
    address: str = ""
    port: int = 0
    protocol: str = ""
    current: int = 0
    total: int = 0
    mode: str = "http"  # 'http' or 'speed'


@dataclass
class NodeTested(Event):
    """Emitted after an individual node test."""
    node_id: str = ""
    latency_ms: Optional[float] = None
    speed_mbps: Optional[float] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class NodeEliminated(Event):
    """Emitted when a node is eliminated or marked dead."""
    node_id: str = ""
    round_num: int = 0
    reason: str = ""


@dataclass
class NodeGeoUpdated(Event):
    """Emitted when a node's GeoIP and Google check complete."""
    node_id: str = ""
    country_code: str = ""
    isp: str = ""
    google_country: str = ""
    is_google_bad: bool = False


@dataclass
class GitHubSyncStatus(Event):
    """Emitted during GitHub sync operations."""
    status: str = ""
    message: str = ""
    url: Optional[str] = None


class EventBus:
    """Thread-safe and async-compatible event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], List[Callable[[Event], Any]]] = {}
        self._global_subscribers: List[Callable[[Event], Any]] = []

    def subscribe(self, event_type: Type[Event], callback: Callable[[Any], Any]) -> None:
        """Subscribe a callback to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[Event], Any]) -> None:
        """Subscribe a callback to all events."""
        if callback not in self._global_subscribers:
            self._global_subscribers.append(callback)

    def unsubscribe(self, callback: Callable[..., Any]) -> None:
        """Remove a callback from all subscriptions."""
        for subs in self._subscribers.values():
            if callback in subs:
                subs.remove(callback)
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)

    def emit(self, event: Event) -> None:
        """Emit an event to all relevant subscribers."""
        handlers: List[Callable[..., Any]] = list(self._global_subscribers)
        for evt_cls, subs in self._subscribers.items():
            if isinstance(event, evt_cls):
                handlers.extend(subs)

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    # If running in an asyncio event loop, schedule it
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as e:
                # Core never crashes due to UI handler exceptions
                pass

    def log(self, message: str, level: str = "INFO") -> None:
        """Convenience method to emit a LogMessage."""
        self.emit(LogMessage(level=level, message=message))
