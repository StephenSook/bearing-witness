"""Always-on watch loop (the event brief's own words: an ALWAYS-ON business
agent). Replays the bearing's life chronologically through the live engine at a
fixed cadence: every tick analyzes the next window through the same adapter,
validation, and gated Mongo writes as a human-triggered run, so cases land on
their own while nobody is clicking. Nothing here is a recording: each tick is a
real engine invocation.

Dormant until the engine CLI exists (the UI gates on engine_available, same as
the live row). Errors are recorded and the loop continues: one bad window must
not kill an always-on process. Built Friday night as disclosed scaffolding;
first wired run is Saturday.
"""
from __future__ import annotations

import threading
from typing import Callable, Iterable

from . import engine_adapter as ea
from . import store as st


class WatchLoop:
    """Single background replay ticker. start() is idempotent; stop() is prompt
    (the inter-tick sleep is an interruptible wait, not time.sleep)."""

    def __init__(self, db, windows: Iterable[int] = range(1, 159),
                 interval_s: float = 2.0,
                 analyze: Callable[[int], dict] | None = None,
                 resume: Callable[[], set] | None = None):
        self._db = db
        self._windows = list(windows)
        self._interval = interval_s
        self._analyze = analyze or (lambda w: ea.analyze_and_store(self._db, w))
        # the loop's memory is the DATABASE: at start it asks Mongo which
        # windows already have a case on record and skips them, so a killed
        # and restarted agent resumes where the stored record says it left off
        self._resume = resume or (lambda: st.recorded_windows(self._db))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = {"running": False, "current_window": None,
                       "analyzed": 0, "skipped_on_record": 0, "errors": []}

    def snapshot(self) -> dict:
        t = self._thread
        alive = t is not None and t.is_alive()
        with self._lock:
            return {**self._state, "errors": list(self._state["errors"]),
                    "running": alive,
                    "stopping": alive and self._stop.is_set()}

    def start(self) -> bool:
        with self._lock:
            if self._state["running"]:
                return False
            self._state.update({"running": True, "analyzed": 0,
                                "skipped_on_record": 0, "errors": []})
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self, wait_s: float = 5.0) -> bool:
        """Request stop and wait briefly. Returns True only when the worker is
        actually dead. An IN-FLIGHT engine tick (a subprocess that can run for
        minutes) cannot be cancelled mid-analysis, so False means STOPPING: the
        current tick will finish and may still write its case; no further ticks
        start. Callers must not announce 'stopped' on False — watch snapshot()
        until running goes False."""
        self._stop.set()
        t = self._thread
        if t is None:
            return True
        t.join(timeout=wait_s)
        return not t.is_alive()

    def _run(self) -> None:
        try:
            try:
                on_record = self._resume()
            except Exception as exc:  # resume is an optimization, never a crash
                with self._lock:
                    self._state["errors"].append(("resume", str(exc)[:200]))
                on_record = set()
            skipped = [w for w in self._windows if w in on_record]
            with self._lock:
                self._state["skipped_on_record"] = len(skipped)
            for w in self._windows:
                if w in on_record:
                    continue
                if self._stop.is_set():
                    break
                with self._lock:
                    self._state["current_window"] = w
                try:
                    self._analyze(w)
                    with self._lock:
                        self._state["analyzed"] += 1
                except Exception as exc:  # an always-on loop records and continues
                    with self._lock:
                        self._state["errors"].append((w, str(exc)[:200]))
                if self._stop.wait(self._interval):
                    break
        finally:
            with self._lock:
                self._state["running"] = False
