"""Stage 4 — draft the next task; a human approves or rejects. No automatic work order.

The decision store is a protocol: JsonDecisionStore today, MongoDB on the box (same interface).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from .contract import HumanReview, InspectionDraft, ResultContract, TaskType

Decision = Literal["APPROVE", "REJECT", "DEFER"]

_ACTIONS: dict[str, str] = {
    "INSPECTION_WORK_ORDER": "Draft inspection for analyst review: confirm the cited envelope and ordinary-spectrum "
                       "evidence on the named element. This is a review request, not a repair order.",
    "MEASURE_SHAFT_SPEED": "Measure shaft speed on this asset (tachometer or keyphasor) and record it with units "
                           "and time alignment. Localization is blocked until speed is trusted.",
    "VERIFY_BEARING_GEOMETRY": "Verify the installed bearing's geometry (element count, element diameter, pitch "
                               "diameter, contact angle) against the physical part. Model number is not geometry.",
    "RECAPTURE_SIGNAL": "Recapture the vibration record: the acquisition failed a signal check (length, sample rate, "
                        "non-finite samples, or clipping).",
    "ANALYST_REVIEW": "Route to a vibration analyst: a persistent change exists but the element cannot be named "
                      "with a clear margin from the available evidence.",
}
_NOT_CLAIMED = [
    "No remaining-useful-life (RUL) estimate",
    "No universal failure stage or severity scale from envelope peak height",
    "No part number, outage window, or repair schedule",
    "No claim of health: NO_ANOMALY_DETECTED means no persistent change in the evidence we have",
]


def draft_task(task_type: TaskType, asset_id: str, suspected_element: str | None,
               evidence_locators: list[str]) -> InspectionDraft:
    title = {
        "INSPECTION_WORK_ORDER": f"Inspect bearing — suspected {suspected_element} race/element pattern",
        "MEASURE_SHAFT_SPEED": "Measure shaft speed",
        "VERIFY_BEARING_GEOMETRY": "Verify bearing geometry",
        "RECAPTURE_SIGNAL": "Recapture vibration signal",
        "ANALYST_REVIEW": "Analyst review — location unconfirmed",
    }[task_type]
    return InspectionDraft(task_type=task_type, title=title, asset_id=asset_id,
                           suspected_element=suspected_element, evidence_locators=list(evidence_locators),
                           recommended_action=_ACTIONS[task_type], not_claimed=list(_NOT_CLAIMED))


class DecisionStore(Protocol):
    def record(self, analysis_id: str, decision: Decision, reason: str) -> HumanReview: ...


class JsonDecisionStore:
    def __init__(self, path):
        self.path = Path(path)

    def record(self, analysis_id: str, decision: Decision, reason: str) -> HumanReview:
        entry = {"analysis_id": analysis_id, "decision": decision,
                 "reason": (reason or "").strip() or "(no reason given)",
                 "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            rows = json.loads(self.path.read_text())
            assert isinstance(rows, list)
        except Exception:
            rows = []
        rows.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2))
        return HumanReview(required=True, decision=decision, reason=entry["reason"], timestamp=entry["timestamp"])


def apply_decision(result: ResultContract, decision: Decision, reason: str, store: DecisionStore) -> ResultContract:
    """Only ANALYST_REVIEW_REQUIRED cases are decidable; APPROVE and REJECT write a stored decision, evidence retained unchanged."""
    if result.status != "ANALYST_REVIEW_REQUIRED":
        raise ValueError(f"{decision} not allowed on status {result.status}: only ANALYST_REVIEW_REQUIRED cases are decidable")
    hr = store.record(result.analysis_id, decision, reason)
    status = {"APPROVE": "INSPECTION_APPROVED", "REJECT": "INSPECTION_REJECTED", "DEFER": result.status}[decision]
    return result.model_copy(update={"status": status, "human_review": hr})
