"""Live per-bearing evidence screen: any of the 15 XJTU-SY bearings, at the
window the frozen v3 evaluator actually verdicted (`eval/results_v3.json`'s
own `onset_window`), through the SAME real engine + gated Mongo path the
Bearing1_3 replay uses -- not fixtures, not the four curated "one real life"
beats.

Deliberately a SEPARATE render path from `evidence.py`/`decide.py` rather than
a shared refactor: those are the rehearsed, QA'd Bearing1_3 pitch screens, and
this module must never be able to change their behavior. Some layout code is
duplicated on purpose (see the module docstrings there and here) to keep that
isolation real, not just intended.
"""
from __future__ import annotations

from nicegui import run, ui

from .. import engine_adapter as ea
from ..contract_shape import traffic_light
from ..live_bearing import CACHE_DIR, live_series, live_trend
from . import charts, trust
from .casedata import Backend
from .hud import Hud
from .theme import LAMP

MEANING = {
    "green": "NO PERSISTENT CHANGE IN THE AVAILABLE EVIDENCE. NOT A VERIFIED HEALTHY LABEL.",
    "yellow": "KEEP TRENDING OR COLLECT THE MISSING CONTEXT. DO NOT SCHEDULE REPAIR.",
    "red": "TWO SIGNAL VIEWS SUPPORT AN INSPECTION DRAFT. HUMAN REVIEW REQUIRED. INSPECT, NEVER REPLACE.",
}
DEFAULT_MEANING = "A HUMAN DECIDED. THE EVIDENCE RECORD IS RETAINED EITHER WAY."


def _explain_panel(result: dict) -> None:
    mc = result["machine_components"]
    with ui.element("div").classes("bw-card w-full").style("cursor:default"):
        ui.label("STAGE 2 · KNOWN MACHINE FREQUENCIES FIRST").classes("bw-mono").style("font-weight:700")
        ui.label("CALCULATED FAMILIES SUPPORT LOCALIZATION. THEY ARE NOT THE DETECTOR.") \
            .classes("bw-mono").style("opacity:0.55;margin-top:4px;font-size:9px")
        for fam, hz in mc["predicted_hz"].items():
            with ui.element("div").classes("bw-caprow").style("margin-top:6px"):
                ui.label(fam)
                ui.element("span").classes("leader")
                ui.label(f"{hz:.3f} HZ · ±{charts.half_width(hz):.2f}")
        with ui.element("div").classes("bw-caprow").style("margin-top:6px"):
            ui.label("SHAFT 1X (SETPOINT)")
            ui.element("span").classes("leader")
            ui.label(f'{mc["shaft_hz_nominal"]:.1f} HZ · PREDICTIONS USE THIS')
        ui.label("ENVELOPE PEAK HEIGHT IS NOT SEVERITY: LATE-STAGE IMPACTS BROADEN AND OVERLAP.") \
            .classes("bw-mono").style("opacity:0.5;margin-top:10px;font-size:9px")


def _decide_block(result: dict, backend: Backend, refresh) -> None:
    status = result["status"]
    lamp = traffic_light(status)
    with ui.element("div").classes("bw-lamp w-full").style(f"background:{LAMP[lamp]}"):
        ui.label(status).classes("bw-state-string")
        ui.label(MEANING.get(lamp, DEFAULT_MEANING)).classes("bw-mono").style("opacity:0.85;margin-top:8px")

    draft = result["inspection_draft"]
    hr = result["human_review"]
    decidable = (status == "ANALYST_REVIEW_REQUIRED" and draft
                 and draft["task_type"] == "INSPECTION_WORK_ORDER")
    if draft:
        with ui.element("div").classes("bw-card w-full").style("cursor:default;margin-top:12px"):
            ui.label(f"DRAFTED TASK · {draft['task_type']}").classes("bw-mono").style("font-weight:700")
            ui.label(draft["title"].upper()).classes("bw-subhead bw-display").style("margin-top:6px")
            ui.label(draft["recommended_action"]).classes("bw-mono-lg").style("margin-top:8px;text-transform:none")
            ui.label("NOT CLAIMED: " + ", ".join(draft["not_claimed"]).upper()) \
                .classes("bw-mono").style("opacity:0.55;margin-top:8px")

            if hr and hr.get("decision"):
                ui.label(f"DECISION · {hr['decision']} · {hr['timestamp']}") \
                    .classes("bw-mono bw-chip").style("margin-top:12px")
                ui.label(f"REASON · {hr['reason']}").classes("bw-mono").style("opacity:0.7;margin-top:6px")
            if (not hr or hr.get("decision") in (None, "DEFER")) and decidable and hr and hr.get("required"):
                reason = ui.input(label="reason (stored with the decision)") \
                    .classes("w-full").props("dense outlined")

                async def _decide(decision: str) -> None:
                    if not reason.value:
                        ui.notify("a stored decision needs a reason", type="warning")
                        return
                    try:
                        await run.io_bound(backend.store.record, result["analysis_id"], decision, reason.value)
                    except Exception as exc:
                        ui.notify(f"decision refused · {exc}", type="negative")
                        await refresh()
                        return
                    ui.notify(f"{decision} recorded · evidence retained", type="positive")
                    await refresh()

                with ui.element("div").style("display:flex;gap:12px;margin-top:12px"):
                    ui.button("APPROVE INSPECTION", on_click=lambda: _decide("APPROVE")) \
                        .props("unelevated no-caps").classes("bw-mono") \
                        .style("background:var(--ink) !important;color:var(--paper-bright)")
                    ui.button("REJECT", on_click=lambda: _decide("REJECT")) \
                        .props("outline no-caps").classes("bw-mono").style("color:inherit")
                    ui.button("DEFER", on_click=lambda: _decide("DEFER")) \
                        .props("flat no-caps").classes("bw-mono").style("opacity:0.7")
            elif not (hr and hr.get("decision")):
                ui.label("NO APPROVAL PATH HERE · COMPLETE THE TASK, RESTORE TRUST, RE-RUN") \
                    .classes("bw-mono").style("opacity:0.6;margin-top:12px")
    if result["refusal_reasons"]:
        with ui.element("div").classes("bw-caprow").style("margin-top:12px"):
            ui.label("REFUSAL").style("font-weight:700")
            ui.element("span").classes("leader")
            ui.label("; ".join(result["refusal_reasons"]).upper())


async def view(bearing: str, condition: str, record: int, backend: Backend, hud: Hud, dark: bool) -> None:
    if backend.kind != "mongo":
        ui.label("live per-bearing view needs the Mongo backend").classes("bw-mono")
        return

    async def _render() -> None:
        container.clear()
        with container:
            ui.label("ANALYZING · REAL ENGINE, NOT A RECORDING").classes("bw-mono").style("opacity:0.6")
        try:
            result = await run.io_bound(ea.analyze_and_store, backend.db, record,
                                        condition=condition, bearing=bearing,
                                        cache_dir=str(CACHE_DIR))
        except ea.EngineError as exc:
            container.clear()
            with container:
                ui.label(f"ENGINE REFUSED · {exc}").classes("bw-mono")
            return
        trend = await run.io_bound(live_trend, condition, bearing, record)
        series = await run.io_bound(live_series, condition, bearing, record)
        container.clear()
        with container:
            hud.show_case(result)

            ui.html(f'<div class="bw-display bw-headline">{bearing.upper()} · LIVE</div>')
            with ui.element("div").style(
                    "display:flex;justify-content:space-between;align-items:center;"
                    "margin-top:12px;flex-wrap:wrap;gap:10px"):
                ui.label(f"W{record:03d} · {condition} · REAL ENGINE, NOT A FIXTURE").classes("bw-mono")
                ui.button("← FLEET", on_click=lambda: ui.navigate.to("/")) \
                    .props("flat no-caps").classes("bw-mono")
                ui.label(result["analysis_id"].upper()).classes("bw-mono").style("opacity:0.5")

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 1 · TREND VS THE ASSET'S OWN EARLY BASELINE · "
                         f"REPLAY SEES ONLY WINDOWS 1-{record}").classes("bw-mono")
                ui.element("div").classes("rule")
            onset = result["anomaly_evidence"].get("onset_window")
            ui.plotly({**charts.trend_figure(trend, record, onset, dark),
                       "config": charts.CONFIG}).classes("w-full").style("height:230px")

            with ui.element("div").classes("w-full grid grid-cols-1 lg:grid-cols-2 gap-4"):
                trust.panel(result)
                _explain_panel(result)

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 3 · TWO VIEWS, SIDE BY SIDE").classes("bw-mono")
                ui.element("div").classes("rule")
            with ui.element("div").classes("w-full grid grid-cols-1 lg:grid-cols-2 gap-4"):
                ui.plotly({**charts.spectrum_figure(
                    series["ordinary"], dark, title="View A · ordinary spectrum",
                    xmax=2000, log_y=True), "config": charts.CONFIG}) \
                    .classes("w-full").style("height:300px")
                if series["envelope"]:
                    ui.plotly({**charts.spectrum_figure(
                        series["envelope"], dark, title="View B · envelope spectrum (2-4 kHz demod)",
                        xmax=450, predicted=result["machine_components"]["predicted_hz"],
                        peaks=result["envelope_evidence"]["peaks"]), "config": charts.CONFIG}) \
                        .classes("w-full").style("height:300px")
                else:
                    ui.label("VIEW B NOT COMPUTED · LOCALIZATION BLOCKED (SEE TRUST PANEL)") \
                        .classes("bw-mono").style("padding-top:40px")

            locs = [loc for fam in result["candidate_families"] for loc in fam["locators"]]
            if result["inspection_draft"]:
                locs = locs or result["inspection_draft"]["evidence_locators"]
            if locs:
                with ui.element("div").classes("bw-section"):
                    ui.label("EVIDENCE LOCATORS · EVERY CLAIM RESOLVES").classes("bw-mono")
                    ui.element("div").classes("rule")
                for loc in locs:
                    ui.label(loc).classes("bw-locator").on(
                        "click", lambda l=loc: ui.notify(f"locator · {l}", type="info"))

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 4 · A HUMAN SAYS YES").classes("bw-mono")
                ui.element("div").classes("rule")
            _decide_block(result, backend, _render)

    container = ui.element("div").classes("w-full")
    await _render()
