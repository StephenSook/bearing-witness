"""Traffic light + human decision block (PLAN.md 2.7).

The lamp is a costume: the deterministic state string always renders inside it,
red reads "inspection review", never "replace". Approve AND reject both persist
a stored decision through the DecisionStore; rejection keeps the evidence.
"""
from __future__ import annotations

from nicegui import ui

from ..contract_shape import traffic_light
from .casedata import Backend
from .hud import Hud
from .theme import LAMP

MEANING = {
    "green": "NO PERSISTENT CHANGE IN THE AVAILABLE EVIDENCE. NOT A VERIFIED HEALTHY LABEL.",
    "yellow": "KEEP TRENDING OR COLLECT THE MISSING CONTEXT. DO NOT SCHEDULE REPAIR.",
    "red": "TWO SIGNAL VIEWS SUPPORT AN INSPECTION DRAFT. HUMAN REVIEW REQUIRED. INSPECT, NEVER REPLACE.",
    "resolved": "A HUMAN DECIDED. THE EVIDENCE RECORD IS RETAINED EITHER WAY.",
}


def block(name: str, backend: Backend, hud: Hud, refresh) -> None:
    result = backend.case(name)
    status = result["status"]
    lamp = traffic_light(status)

    with ui.element("div").classes("bw-lamp w-full").style(f"background:{LAMP[lamp]}"):
        ui.label(status).classes("bw-state-string")
        ui.label(MEANING[lamp]).classes("bw-mono").style("opacity:0.85;margin-top:8px")

    draft = result["inspection_draft"]
    hr = result["human_review"]
    # Approve/reject/defer applies ONLY to an inspection work order awaiting review.
    # A refusal case's remediation task (e.g. VERIFY_BEARING_GEOMETRY) is work to do,
    # not something a human can "approve" into INSPECTION_APPROVED. The store enforces
    # the same gate server-side; this just keeps the ineligible buttons off the screen.
    can_decide_here = (backend.decidable_here(name) if hasattr(backend, "decidable_here")
                       else name not in getattr(backend, "unpersisted", frozenset()))
    decidable = (status == "ANALYST_REVIEW_REQUIRED" and draft
                 and draft["task_type"] == "INSPECTION_WORK_ORDER"
                 and can_decide_here)
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
            # a DEFER stays open for a final decision; APPROVE/REJECT are final
            if (not hr or hr.get("decision") in (None, "DEFER")) \
                    and decidable and hr and hr.get("required"):
                reason = ui.input(label="reason (stored with the decision)") \
                    .classes("w-full").props("dense outlined")

                def _decide(decision: str) -> None:
                    if not reason.value:
                        ui.notify("a stored decision needs a reason", type="warning")
                        return
                    try:
                        backend.store.record(result["analysis_id"], decision, reason.value)
                    except Exception as exc:  # DecisionConflict or backend error
                        ui.notify(f"decision refused · {exc}", type="negative")
                        refresh()
                        return
                    ui.notify(f"{decision} recorded · evidence retained", type="positive")
                    refresh()

                with ui.element("div").style("display:flex;gap:12px;margin-top:12px"):
                    ui.button("APPROVE INSPECTION", on_click=lambda: _decide("APPROVE")) \
                        .props("unelevated no-caps").classes("bw-mono") \
                        .style("background:var(--ink) !important;color:var(--paper-bright)")
                    ui.button("REJECT", on_click=lambda: _decide("REJECT")) \
                        .props("outline no-caps").classes("bw-mono").style("color:inherit")
                    ui.button("DEFER", on_click=lambda: _decide("DEFER")) \
                        .props("flat no-caps").classes("bw-mono").style("opacity:0.7")
            elif name in getattr(backend, "unpersisted", frozenset()):
                ui.label("CASE NOT PERSISTED TO MONGO · DECISIONS DISABLED (SEED FAILED, SEE LOG)") \
                    .classes("bw-mono").style("opacity:0.6;margin-top:12px")
            elif name in getattr(backend, "degraded", set()):
                ui.label("STORED CASE UNREADABLE OR MISSING · SHOWING FIXTURE EVIDENCE · "
                         "DECISIONS DISABLED UNTIL THE STORE ANSWERS") \
                    .classes("bw-mono").style("opacity:0.6;margin-top:12px")
            elif not (hr and hr.get("decision")):
                ui.label("NO APPROVAL PATH HERE · COMPLETE THE TASK, RESTORE TRUST, RE-RUN") \
                    .classes("bw-mono").style("opacity:0.6;margin-top:12px")
    if result["refusal_reasons"]:
        with ui.element("div").classes("bw-caprow").style("margin-top:12px"):
            ui.label("REFUSAL").style("font-weight:700")
            ui.element("span").classes("leader")
            ui.label("; ".join(result["refusal_reasons"]).upper())
