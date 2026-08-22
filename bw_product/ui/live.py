"""Pick-any-window live analysis (the pitch flex, PLAN 2.8 surface).

Renders NOTHING until the engine CLI actually answers (engine_available() is an
invocation probe, not an import check), so tonight this is dormant and Saturday
it appears on its own once `python -m bearing_witness` exists. The subprocess
runs io_bound so the UI never freezes; the result renders from the engine's own
validated contract JSON, and the case lands in Mongo through the same gated
writes as everything else. A failed analysis shows the engine's error verbatim;
it never falls back to a fixture.
"""
from __future__ import annotations

from nicegui import run, ui

from .. import engine_adapter as ea
from ..contract_shape import traffic_light
from ..watch import WatchLoop
from .casedata import Backend
from .theme import LAMP

_watch: WatchLoop | None = None


def live_analysis_row(backend: Backend) -> None:
    if backend.kind != "mongo" or not ea.engine_available():
        return

    with ui.element("div").classes("bw-card w-full").style("cursor:default;margin-top:18px"):
        ui.label("LIVE ANALYSIS · ANY WINDOW, 1-158 · ENGINE, NOT A RECORDING") \
            .classes("bw-mono").style("font-weight:700")
        with ui.element("div").style("display:flex;gap:12px;align-items:center;margin-top:8px"):
            win = ui.number(label="window", value=100, min=1, max=158, precision=0) \
                .props("dense outlined").style("width:120px")
            btn = ui.button("ANALYZE LIVE",
                            on_click=lambda: _analyze(backend, int(win.value), btn)) \
                .props("unelevated no-caps").classes("bw-mono") \
                .style("background:var(--ink) !important;color:var(--paper-bright)")
        # the always-on beat: replay the bearing's life through the engine on a
        # cadence; cases land by themselves while nobody clicks
        with ui.element("div").style("display:flex;gap:12px;align-items:center;margin-top:10px"):
            wbtn = ui.button("START WATCH", on_click=lambda: _toggle_watch(backend, wbtn)) \
                .props("outline no-caps").classes("bw-mono").style("color:inherit")
            status = ui.label("").classes("bw-mono").style("opacity:0.7")

            def _tick() -> None:
                if _watch is None:
                    status.text = ""
                    return
                s = _watch.snapshot()
                wbtn.text = "STOP WATCH" if s["running"] else "START WATCH"
                if s["stopping"]:
                    # honest state: the in-flight engine tick cannot be cancelled;
                    # it may still land one case before the worker dies
                    status.text = (f"STOPPING · FINISHING W{s['current_window'] or 0:03d} "
                                   "(engine tick can take minutes)")
                elif s["running"]:
                    status.text = (f"WATCHING · W{s['current_window'] or 0:03d} · "
                                   f"{s['analyzed']} ANALYZED · {len(s['errors'])} ERR")
                else:
                    status.text = (f"WATCH DONE · {s['analyzed']} ANALYZED · "
                                   f"{len(s['errors'])} ERR" if s["analyzed"] else "")

            ui.timer(1.0, _tick)


def _toggle_watch(backend: Backend, btn) -> None:
    global _watch
    if _watch is not None and _watch.snapshot()["running"]:
        if _watch.stop(wait_s=2.0):
            ui.notify("watch stopped", type="info")
        else:
            ui.notify("stop requested · finishing the current analysis first "
                      "(one more case may still land)", type="warning")
        return
    _watch = WatchLoop(backend.db)
    _watch.start()
    ui.notify("watch started · replaying the bearing's life through the engine",
              type="positive")


async def _analyze(backend: Backend, window: int, btn) -> None:
    btn.props("loading")
    try:
        result = await run.io_bound(ea.analyze_and_store, backend.db, window)
    except ea.EngineError as exc:
        ui.notify(f"engine refused · {exc}", type="negative", multi_line=True)
        return
    finally:
        btn.props(remove="loading")
    _show(result)


def _show(r: dict) -> None:
    lamp = traffic_light(r["status"])
    with ui.dialog() as dialog, ui.element("div").classes("bw-card").style(
            "min-width:420px;max-width:640px;cursor:default"):
        ui.label(f"W{r['source_window']['record']:03d} · LIVE RESULT").classes("bw-mono") \
            .style("font-weight:700")
        with ui.element("div").classes("bw-lamp w-full").style(
                f"background:{LAMP[lamp]};margin-top:10px"):
            ui.label(r["status"]).classes("bw-state-string")
        if r["suspected_location"]:
            ui.label(f"SUSPECTED · {r['suspected_location'].upper()}").classes("bw-mono") \
                .style("margin-top:8px")
        for fam in r["candidate_families"]:
            ui.label(f"{fam['family']} · f0 {fam['found_f0_hz']} Hz · "
                     f"score {fam['score_current']}").classes("bw-mono").style("opacity:0.8")
        for loc in (r["candidate_families"][0]["locators"] if r["candidate_families"] else [])[:3]:
            ui.label(loc).classes("bw-locator")
        if r["refusal_reasons"]:
            ui.label("REFUSAL · " + "; ".join(r["refusal_reasons"]).upper()) \
                .classes("bw-mono").style("margin-top:8px;opacity:0.8")
        ui.button("CLOSE", on_click=dialog.close).props("flat no-caps") \
            .classes("bw-mono").style("margin-top:12px")
    dialog.open()
