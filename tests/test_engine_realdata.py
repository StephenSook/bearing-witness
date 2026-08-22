"""Regression against the measured findings in PREP_PLAN.md (Bearing1_3). Slow; needs data/."""
import pytest

from bearing_witness import engine, trust
from tests.conftest import requires_data

pytestmark = [pytest.mark.slow, requires_data]


@pytest.fixture(scope="module")
def b13(b13_dir):
    from pathlib import Path
    cache = Path(__file__).resolve().parents[1] / "eval" / "feature_cache"
    return engine.Engine(trust.xjtu_context("35Hz12kN", "Bearing1_3"), b13_dir, cache_dir=cache)


def test_onset_is_window_59(b13):
    r = b13.analyze(158).result
    assert r.anomaly_evidence.onset_window == 59


def test_terminal_window_finds_bpfo_family_three_harmonics(b13):
    r = b13.analyze(158).result
    top = r.candidate_families[0]
    assert top.family == "BPFO" and top.harmonics_above_floor_median == 3 and top.score_median > 25
    assert abs(top.found_f0_hz - 107.0) < 1.5                       # measured 107.03 (slip ~0.8% low)
    # envelope part of the chain is unchanged from v2; only View A may hold the red light back
    assert r.status in ("ANALYST_REVIEW_REQUIRED", "ABNORMAL_LOCATION_UNCONFIRMED")
    if r.status == "ABNORMAL_LOCATION_UNCONFIRMED":
        assert r.refusal_reasons == ["VIEW_A_NO_SUPPORT_BPFO"]


def test_early_window_has_no_family_and_no_persistence(b13):
    r = b13.analyze(11).result
    assert not r.anomaly_evidence.persistent and r.candidate_families == []


def test_geometry_unverified_demo_step_7(b13, b13_dir):
    from pathlib import Path
    ctx = trust.with_unverified(trust.xjtu_context("35Hz12kN", "Bearing1_3"), "geometry")
    r = engine.Engine(ctx, b13_dir, cache_dir=Path(__file__).resolve().parents[1] / "eval" / "feature_cache").analyze(158).result
    assert r.anomaly_evidence.persistent and r.status == "ABNORMAL_LOCATION_UNCONFIRMED"
    assert r.inspection_draft.task_type == "VERIFY_BEARING_GEOMETRY"
