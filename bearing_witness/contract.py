"""The one stable JSON per analysis (spec §5). Interface between engine, UI, evaluator and agent tools.

Field order and names are fixed. Every numeric claim a person can click resolves to a locator:
  {asset_id}|w{window}|{sha8}|{view}|{freq:.2f}Hz|h{k}[|sb{m:+d}]
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal[
    "BLOCKED_SIGNAL", "BLOCKED_BASELINE",
    "NO_ANOMALY_DETECTED", "WATCH_EARLY",
    "ABNORMAL_LOCATION_UNCONFIRMED", "ANALYST_REVIEW_REQUIRED",
    "INSPECTION_APPROVED", "INSPECTION_REJECTED",
]
TaskType = Literal["INSPECTION_WORK_ORDER", "MEASURE_SHAFT_SPEED", "VERIFY_BEARING_GEOMETRY", "RECAPTURE_SIGNAL", "ANALYST_REVIEW"]


def locator(asset_id: str, window: int, sha256: str, view: str, freq_hz: float, k: int | None = None, m: int | None = None) -> str:
    if m is not None and k is None:
        raise ValueError("locator: sideband |sb requires a harmonic order |h")
    s = f"{asset_id}|w{window}|{sha256[:8]}|{view}|{freq_hz:.2f}Hz"
    if k is not None:
        s += f"|h{k}"
    if m is not None:
        s += f"|sb{m:+d}"
    return s


class SourceWindow(BaseModel):
    record: int
    file: str
    channel: str
    n_samples: int
    fs_hz: float
    duration_s: float
    sha256: str


class InputTrust(BaseModel):
    trust_level: str
    signal_ok: bool
    blocks: list[str]
    tasks: list[str]
    speed: dict
    geometry: dict
    regime: dict
    acquisition: dict
    notes: list[str]


class AnomalyEvidence(BaseModel):
    stage1_state: str
    persistent: bool
    onset_window: int | None
    run_length: int
    moved_groups: list[str]
    z: dict[str, float]
    features: dict[str, float]
    baseline: dict | None        # {"windows": [...], "median": {...}, "mad": {...}}
    rule: dict                   # {"z_thresh", "one_sided", "min_groups", "persist", "baseline_n"}


class SpectrumPeak(BaseModel):
    freq_hz: float
    amp: float
    label: str
    locator: str


class MachineComponents(BaseModel):
    shaft_hz_nominal: float
    shaft_hz_measured: float | None
    shaft_hz_used_for_prediction: float
    bearing_model: str | None
    geometry_verified: bool
    predicted_hz: dict[str, float]
    explained_peaks: list[SpectrumPeak]


class OrdinarySpectrumEvidence(BaseModel):
    max_hz: float
    noise_floor: float
    peaks: list[SpectrumPeak]
    view_a_supports: str | None     # family name or None
    notes: str


class EnvelopeEvidence(BaseModel):
    band_hz: list[float]
    band_source: str
    sk: float | None
    noise_floor: float
    peaks: list[SpectrumPeak]
    notes: str


class CandidateFamily(BaseModel):
    family: str
    element: str
    predicted_hz: float
    found_f0_hz: float | None
    score_median: float
    score_current: float
    harmonics_above_floor_median: float
    sideband_pairs_median: float
    eligible: bool
    excluded_hz: list[float]
    locators: list[str]


class InspectionDraft(BaseModel):
    task_type: TaskType
    title: str
    asset_id: str
    suspected_element: str | None
    evidence_locators: list[str]
    recommended_action: str
    not_claimed: list[str]


class HumanReview(BaseModel):
    required: bool
    decision: str | None = None
    reason: str | None = None
    timestamp: str | None = None


class ResultContract(BaseModel):
    analysis_id: str
    asset_id: str
    source_window: SourceWindow
    input_trust: InputTrust
    anomaly_evidence: AnomalyEvidence
    machine_components: MachineComponents
    ordinary_spectrum_evidence: OrdinarySpectrumEvidence
    envelope_evidence: EnvelopeEvidence
    candidate_families: list[CandidateFamily]
    suspected_location: str | None
    status: Status
    refusal_reasons: list[str]
    inspection_draft: InspectionDraft | None
    human_review: HumanReview | None


EMPTY: dict = {
    "analysis_id": "", "asset_id": "",
    "source_window": {"record": 0, "file": "", "channel": "", "n_samples": 0, "fs_hz": 0.0, "duration_s": 0.0, "sha256": ""},
    "input_trust": {"trust_level": "UNVERIFIED", "signal_ok": False, "blocks": ["ALL"], "tasks": ["RECAPTURE_SIGNAL"],
                    "speed": {}, "geometry": {}, "regime": {}, "acquisition": {}, "notes": []},
    "anomaly_evidence": {"stage1_state": "BASELINE", "persistent": False, "onset_window": None, "run_length": 0,
                         "moved_groups": [], "z": {}, "features": {}, "baseline": None, "rule": {}},
    "machine_components": {"shaft_hz_nominal": 0.0, "shaft_hz_measured": None, "shaft_hz_used_for_prediction": 0.0,
                           "bearing_model": None, "geometry_verified": False, "predicted_hz": {}, "explained_peaks": []},
    "ordinary_spectrum_evidence": {"max_hz": 0.0, "noise_floor": 0.0, "peaks": [], "view_a_supports": None, "notes": ""},
    "envelope_evidence": {"band_hz": [], "band_source": "fixed", "sk": None, "noise_floor": 0.0, "peaks": [], "notes": ""},
    "candidate_families": [], "suspected_location": None, "status": "BLOCKED_SIGNAL", "refusal_reasons": [],
    "inspection_draft": None, "human_review": None,
}
