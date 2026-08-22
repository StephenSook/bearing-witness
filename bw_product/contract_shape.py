"""The 14-field result contract as consumed by the product loop.

Transcribed from docs/superpowers/plans/2026-08-21-engine.md (Task 9 ResultContract +
EMPTY) and PLAN.md "Shared Contracts". The engine lane owns the contract; this module
only mirrors its shape so the store and UI can run on fixtures before the engine lands.
When bearing_witness.contract exists on main, `pydantic_contract()` returns it and
everything downstream validates against the real models.
"""
from __future__ import annotations

from typing import Any

# PLAN.md Shared Contracts: status vocabulary (engine-owned)
STATUSES = (
    "BLOCKED_SIGNAL",
    "BLOCKED_BASELINE",
    "NO_ANOMALY_DETECTED",
    "WATCH_EARLY",
    "ABNORMAL_LOCATION_UNCONFIRMED",
    "ANALYST_REVIEW_REQUIRED",
    "INSPECTION_APPROVED",
    "INSPECTION_REJECTED",
)

# PLAN.md Shared Contracts: task types (Mongo validators key on these)
TASK_TYPES = (
    "INSPECTION_WORK_ORDER",
    "MEASURE_SHAFT_SPEED",
    "VERIFY_BEARING_GEOMETRY",
    "RECAPTURE_SIGNAL",
    "ANALYST_REVIEW",
)

DECISIONS = ("APPROVE", "REJECT", "DEFER")

# Contract field order is fixed (engine plan Task 9).
FIELDS = (
    "analysis_id",
    "asset_id",
    "source_window",
    "input_trust",
    "anomaly_evidence",
    "machine_components",
    "ordinary_spectrum_evidence",
    "envelope_evidence",
    "candidate_families",
    "suspected_location",
    "status",
    "refusal_reasons",
    "inspection_draft",
    "human_review",
)

# PLAN.md: green=NO_ANOMALY_DETECTED; yellow=WATCH_EARLY/ABNORMAL_LOCATION_UNCONFIRMED/
# BLOCKED_*; red=ANALYST_REVIEW_REQUIRED. The color is a costume: always render the
# state string next to it. Approved/rejected render as resolved states.
def traffic_light(status: str) -> str:
    if status == "NO_ANOMALY_DETECTED":
        return "green"
    if status in ("WATCH_EARLY", "ABNORMAL_LOCATION_UNCONFIRMED") or status.startswith("BLOCKED_"):
        return "yellow"
    if status == "ANALYST_REVIEW_REQUIRED":
        return "red"
    if status in ("INSPECTION_APPROVED", "INSPECTION_REJECTED"):
        return "resolved"
    raise ValueError(f"unknown status: {status}")


def locator(asset_id: str, window: int, sha256: str, view: str, freq_hz: float,
            harmonic: int, sideband: int | None = None) -> str:
    """PLAN.md Shared Contracts evidence-locator format."""
    loc = f"{asset_id}|w{window}|{sha256[:8]}|{view}|{freq_hz:.2f}Hz|h{harmonic}"
    if sideband is not None:
        loc += f"|sb{sideband:+d}"
    return loc


def empty_contract() -> dict[str, Any]:
    """Transcription of contract.EMPTY from the engine plan (Task 9, Step 3)."""
    return {
        "analysis_id": "", "asset_id": "",
        "source_window": {"record": 0, "file": "", "channel": "", "n_samples": 0,
                          "fs_hz": 0.0, "duration_s": 0.0, "sha256": ""},
        "input_trust": {"trust_level": "UNVERIFIED", "signal_ok": False, "blocks": ["ALL"],
                        "tasks": ["RECAPTURE_SIGNAL"], "speed": {}, "geometry": {},
                        "regime": {}, "acquisition": {}, "notes": []},
        "anomaly_evidence": {"stage1_state": "BASELINE", "persistent": False,
                             "onset_window": None, "run_length": 0, "moved_groups": [],
                             "z": {}, "features": {}, "baseline": None, "rule": {}},
        "machine_components": {"shaft_hz_nominal": 0.0, "shaft_hz_measured": None,
                               "shaft_hz_used_for_prediction": 0.0, "bearing_model": None,
                               "geometry_verified": False, "predicted_hz": {},
                               "explained_peaks": []},
        "ordinary_spectrum_evidence": {"max_hz": 0.0, "noise_floor": 0.0, "peaks": [],
                                       "view_a_supports": None, "notes": ""},
        "envelope_evidence": {"band_hz": [], "band_source": "fixed", "sk": None,
                              "noise_floor": 0.0, "peaks": [], "notes": ""},
        "candidate_families": [], "suspected_location": None, "status": "BLOCKED_SIGNAL",
        "refusal_reasons": [], "inspection_draft": None, "human_review": None,
    }


def validate_shape(result: dict[str, Any]) -> list[str]:
    """Return a list of problems (empty list = conforms). Not a replacement for the
    engine's Pydantic models; a tripwire for fixture and adapter drift."""
    problems: list[str] = []
    for f in FIELDS:
        if f not in result:
            problems.append(f"missing field: {f}")
    for f in result:
        if f not in FIELDS:
            problems.append(f"unknown field: {f}")
    status = result.get("status")
    if status not in STATUSES:
        problems.append(f"bad status: {status!r}")
    draft = result.get("inspection_draft")
    if draft is not None:
        if draft.get("task_type") not in TASK_TYPES:
            problems.append(f"bad task_type: {draft.get('task_type')!r}")
        action = str(draft.get("recommended_action", ""))
        if "replace" in action.lower():
            problems.append("recommended_action contains 'replace' (red is inspect, never replace)")
    hr = result.get("human_review")
    if hr is not None and hr.get("decision") is not None and hr["decision"] not in DECISIONS:
        problems.append(f"bad decision: {hr['decision']!r}")
    return problems


def pydantic_contract():
    """Return the engine's real contract module once it exists, else None."""
    try:
        from bearing_witness import contract  # type: ignore
        return contract
    except ImportError:
        return None
