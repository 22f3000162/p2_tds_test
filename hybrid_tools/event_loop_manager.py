"""
Persistent Event Loop Manager for Hybrid Quiz Solver

Provides a single, persistent asyncio event loop for running async code
from synchronous contexts (LangGraph / LangChain tools), preventing
'Event loop is closed' errors.
"""

import asyncio
import threading
from typing import Coroutine, TypeVar, Any

T = TypeVar("T")


class EventLoopManager:
    """
    Singleton manager for a persistent asyncio event loop
    running in a background thread.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._start_loop()

    def _start_loop(self):
        """Start the persistent event loop in a background thread."""

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

        # Wait until loop is ready
        while self._loop is None:
            pass

        print("[EVENT_LOOP] ✓ Persistent event loop started")

    def run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run an async coroutine safely from synchronous code.
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Event loop is not running")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def shutdown(self):
        """Stop the event loop (optional, call on program exit)."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            print("[EVENT_LOOP] ✓ Event loop stopped")


# --------------------------------------------------
# GLOBAL ACCESSORS
# --------------------------------------------------
_event_loop_manager: EventLoopManager | None = None


def get_event_loop_manager() -> EventLoopManager:
    global _event_loop_manager
    if _event_loop_manager is None:
        _event_loop_manager = EventLoopManager()
    return _event_loop_manager


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Convenience helper.

    Example:
        result = run_async(fetch_data(url))
    """
    return get_event_loop_manager().run_async(coro)
