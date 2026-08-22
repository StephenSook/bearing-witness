import numpy as np
import pytest

from bearing_witness import engine, trust
from bearing_witness.dsp import FS, N_EXPECTED
from tests.synth import synth_fault, white

BPFO35 = 107.907


def _write(dirpath, k, x):
    dirpath.mkdir(parents=True, exist_ok=True)
    rows = np.column_stack([x, np.zeros_like(x)])
    np.savetxt(dirpath / f"{k}.csv", rows, delimiter=",", header="Horizontal_vibration_signals,Vertical_vibration_signals", comments="")


@pytest.fixture(scope="module")
def synthetic_asset(tmp_path_factory):
    """Windows 1..14 healthy noise; 15..22 outer-race fault at 107.9 Hz with a 35 Hz shaft tone in the raw signal
    so View A has a machine component to explain and BPFO ordinary harmonics to find."""
    d = tmp_path_factory.mktemp("asset") / "35Hz12kN" / "BearingS_1"
    t = np.arange(N_EXPECTED) / FS
    shaft = 0.3 * np.sin(2 * np.pi * 35.0 * t)
    for k in range(1, 15):
        _write(d, k, white(0.2, seed=k) + shaft)
    for k in range(15, 23):
        x = synth_fault(BPFO35, amp=2.0, noise=0.2, seed=k) + shaft
        x += 0.05 * np.sin(2 * np.pi * BPFO35 * t) + 0.03 * np.sin(2 * np.pi * 2 * BPFO35 * t)   # ordinary-spectrum harmonics
        _write(d, k, x)
    return d


def _engine(d, cache=None):
    return engine.Engine(trust.xjtu_context("35Hz12kN", "BearingS_1"), d, cache_dir=cache)


def test_baseline_windows_are_blocked_baseline(synthetic_asset):
    r = _engine(synthetic_asset).analyze(5).result
    assert r.status == "BLOCKED_BASELINE" and r.refusal_reasons == ["BASELINE_ACCUMULATING_5_OF_10"]
    assert r.anomaly_evidence.baseline is None and r.inspection_draft is None


def test_healthy_window_is_green_with_no_candidates(synthetic_asset):
    a = _engine(synthetic_asset).analyze(12)
    r = a.result
    # a 10-window MAD can be small enough that one early indicator crosses z=5 by chance -> WATCH_EARLY;
    # what must hold: no persistence, no families, no location
    assert r.status in ("NO_ANOMALY_DETECTED", "WATCH_EARLY") and not r.anomaly_evidence.persistent
    assert r.candidate_families == [] and r.suspected_location is None
    assert r.anomaly_evidence.baseline["windows"] == list(range(1, 11))
    assert r.machine_components.shaft_hz_used_for_prediction == 35.0
    assert "ordinary" in a.series and a.series["envelope"] is None


def test_persistent_fault_goes_red_with_outer_and_draft(synthetic_asset, tmp_path):
    a = _engine(synthetic_asset, cache=tmp_path / "cache").analyze(22)
    r = a.result
    assert r.anomaly_evidence.onset_window == 15 and r.anomaly_evidence.persistent
    assert r.status == "ANALYST_REVIEW_REQUIRED" and r.suspected_location == "outer"
    assert r.candidate_families[0].family == "BPFO" and r.candidate_families[0].eligible
    assert r.inspection_draft.task_type == "INSPECTION_WORK_ORDER" and r.human_review.required
    assert r.ordinary_spectrum_evidence.view_a_supports == "BPFO"
    assert any(p.label == "1x shaft" for p in r.machine_components.explained_peaks)
    assert all(loc.startswith(r.asset_id + "|w") for loc in r.inspection_draft.evidence_locators)
    assert (tmp_path / "cache" / "BearingS_1.csv").exists()


def test_geometry_unverified_keeps_detector_abnormal_but_blocks_localization(synthetic_asset):
    ctx = trust.with_unverified(trust.xjtu_context("35Hz12kN", "BearingS_1"), "geometry")
    r = engine.Engine(ctx, synthetic_asset).analyze(22).result
    assert r.anomaly_evidence.persistent and r.anomaly_evidence.onset_window == 15
    assert r.status == "ABNORMAL_LOCATION_UNCONFIRMED"
    assert r.candidate_families == [] and r.suspected_location is None
    assert r.inspection_draft.task_type == "VERIFY_BEARING_GEOMETRY"
    assert "GEOMETRY_UNVERIFIED" in r.input_trust.notes and not r.machine_components.geometry_verified


def test_speed_unverified_blocks_order_analysis_and_localization(synthetic_asset):
    ctx = trust.with_unverified(trust.xjtu_context("35Hz12kN", "BearingS_1"), "speed")
    a = engine.Engine(ctx, synthetic_asset).analyze(22)
    r = a.result
    assert r.anomaly_evidence.persistent and r.anomaly_evidence.onset_window == 15
    assert r.status == "ABNORMAL_LOCATION_UNCONFIRMED" and r.refusal_reasons == ["LOCALIZATION_BLOCKED_SPEED_UNVERIFIED"]
    assert r.inspection_draft.task_type == "MEASURE_SHAFT_SPEED"
    assert r.candidate_families == [] and r.suspected_location is None
    assert r.machine_components.explained_peaks == [] and r.machine_components.shaft_hz_measured is None and r.machine_components.predicted_hz == {}
    assert "ORDER_ANALYSIS" in r.input_trust.blocks and "SPEED_UNVERIFIED" in r.input_trust.notes
    assert "ordinary" in a.series


def test_acquisition_unverified_blocks_all_conclusions(synthetic_asset):
    ctx = trust.with_unverified(trust.xjtu_context("35Hz12kN", "BearingS_1"), "acquisition")
    a = engine.Engine(ctx, synthetic_asset).analyze(22)
    r = a.result
    assert r.status == "BLOCKED_SIGNAL" and r.refusal_reasons == ["ACQUISITION_UNVERIFIED"]
    assert r.inspection_draft.task_type == "RECAPTURE_SIGNAL"
    assert not r.anomaly_evidence.persistent and r.candidate_families == [] and r.suspected_location is None
    assert r.machine_components.explained_peaks == [] and r.machine_components.predicted_hz == {} and r.machine_components.shaft_hz_measured is None
    assert "ALL" in r.input_trust.blocks and r.input_trust.signal_ok is True


def test_build_test_injected_tone_cannot_produce_element_call(synthetic_asset):
    """Spec Stage-1 build test at engine level: inject a BPFO tone at 5x RMS into healthy windows 11..13.
    Stage 1 must not reach persistence; no family may be scored; no element call."""
    eng = _engine(synthetic_asset)
    t = np.arange(N_EXPECTED) / FS
    overrides = {}
    for k in (11, 12, 13):
        x = white(0.2, seed=k) + 0.3 * np.sin(2 * np.pi * 35.0 * t)
        rms = float(np.sqrt(np.mean(x ** 2)))
        overrides[k] = x + 5.0 * rms * np.sin(2 * np.pi * BPFO35 * t)
    r = eng.analyze(13, overrides=overrides).result
    assert r.source_window.sha256 == "INJECTED"
    assert not r.anomaly_evidence.persistent
    assert r.status in ("NO_ANOMALY_DETECTED", "WATCH_EARLY")
    assert r.candidate_families == [] and r.suspected_location is None and r.inspection_draft is None


def test_bad_signal_is_blocked(synthetic_asset):
    r = _engine(synthetic_asset).analyze(12, overrides={12: np.zeros(100)}).result
    assert r.status == "BLOCKED_SIGNAL" and r.inspection_draft.task_type == "RECAPTURE_SIGNAL"
