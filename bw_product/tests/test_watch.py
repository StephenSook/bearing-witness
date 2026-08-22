"""WatchLoop: the always-on ticker, tested with an injected analyze callable
(no subprocess, no Mongo): the loop's job is cadence, resilience, and clean
stop semantics; the analyze path itself is covered by the adapter tests.
"""
import threading
import time

from bw_product.watch import WatchLoop


def test_watch_analyzes_every_window_and_finishes():
    seen = []
    loop = WatchLoop(db=None, windows=range(1, 6), interval_s=0.0,
                     analyze=seen.append)
    assert loop.start() is True
    deadline = time.monotonic() + 5
    while loop.snapshot()["running"] and time.monotonic() < deadline:
        time.sleep(0.01)
    snap = loop.snapshot()
    assert seen == [1, 2, 3, 4, 5]
    assert snap["analyzed"] == 5 and snap["errors"] == []
    assert snap["running"] is False


def test_watch_stop_is_prompt():
    started = threading.Event()

    def slow(w):
        started.set()
        time.sleep(0.05)

    loop = WatchLoop(db=None, windows=range(1, 1000), interval_s=5.0, analyze=slow)
    loop.start()
    assert started.wait(timeout=5)
    t0 = time.monotonic()
    loop.stop()
    assert time.monotonic() - t0 < 6  # interruptible wait, not a 5s-per-tick drain
    assert loop.snapshot()["running"] is False
    assert loop.snapshot()["analyzed"] < 999


def test_watch_records_errors_and_continues():
    def flaky(w):
        if w == 3:
            raise RuntimeError("engine refused window 3")

    loop = WatchLoop(db=None, windows=range(1, 6), interval_s=0.0, analyze=flaky)
    loop.start()
    deadline = time.monotonic() + 5
    while loop.snapshot()["running"] and time.monotonic() < deadline:
        time.sleep(0.01)
    snap = loop.snapshot()
    assert snap["analyzed"] == 4
    assert len(snap["errors"]) == 1 and snap["errors"][0][0] == 3
    assert "window 3" in snap["errors"][0][1]


def test_stop_during_blocked_analysis_reports_stopping_not_stopped():
    """The night-gate HIGH: an in-flight engine tick can outlive stop()'s join.
    stop() must return False (STOPPING), snapshot must say stopping while the
    worker lives, and only after the tick finishes does running go False."""
    release = threading.Event()
    started = threading.Event()

    def blocked(w):
        started.set()
        release.wait(timeout=10)

    loop = WatchLoop(db=None, windows=range(1, 3), interval_s=0.0, analyze=blocked)
    loop.start()
    assert started.wait(timeout=5)
    assert loop.stop(wait_s=0.2) is False       # worker still alive: STOPPING
    snap = loop.snapshot()
    assert snap["running"] is True and snap["stopping"] is True
    release.set()
    deadline = time.monotonic() + 5
    while loop.snapshot()["running"] and time.monotonic() < deadline:
        time.sleep(0.02)
    final = loop.snapshot()
    assert final["running"] is False and final["stopping"] is False
    assert final["analyzed"] <= 1               # no further ticks after the stop


def test_watch_start_is_idempotent():
    gate = threading.Event()
    loop = WatchLoop(db=None, windows=range(1, 3), interval_s=0.0,
                     analyze=lambda w: gate.wait(timeout=5))
    assert loop.start() is True
    assert loop.start() is False  # second start while running: refused
    gate.set()
    loop.stop()
