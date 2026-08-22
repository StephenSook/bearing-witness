import numpy as np
import pytest

from bearing_witness import trust
from bearing_witness.data import Record


def _rec(x, fs=25600.0):
    return Record(index=1, path="x.csv", x=np.asarray(x, float), fs=fs, sha256="0" * 64)


def _good(n=32768, seed=0):
    return np.random.default_rng(seed).normal(0.0, 1.0, n)   # all-zeros would trip the FLATLINE check


def test_xjtu_context_is_trusted_for_replay_and_predicts_known_frequencies():
    ctx = trust.xjtu_context("35Hz12kN", "Bearing1_3")
    assert ctx.asset_id == "XJTU-SY/35Hz12kN/Bearing1_3"
    assert ctx.speed.value_hz == 35.0 and ctx.speed.trust == trust.TrustLevel.TRUSTED_FOR_REPLAY
    assert ctx.geometry.model_number == "LDK UER204" and ctx.geometry.n_elements == 8
    assert ctx.fault_frequencies()["BPFO"] == pytest.approx(107.907, abs=1e-3)
    res = trust.evaluate_trust(ctx, _rec(_good()))
    assert res.signal_ok and res.blocks == [] and res.tasks == []
    assert res.trust_level == trust.TrustLevel.TRUSTED_FOR_REPLAY


def test_unverified_geometry_blocks_localization_and_creates_task():
    ctx = trust.xjtu_context("35Hz12kN", "Bearing1_3")
    ctx2 = trust.with_unverified(ctx, "geometry")
    res = trust.evaluate_trust(ctx2, _rec(_good()))
    assert "LOCALIZATION" in res.blocks and "BASELINE_COMPARISON" not in res.blocks
    assert res.tasks == ["VERIFY_BEARING_GEOMETRY"]
    assert res.trust_level == trust.TrustLevel.UNVERIFIED


def test_unverified_speed_blocks_order_analysis_and_localization():
    ctx = trust.with_unverified(trust.xjtu_context("37.5Hz11kN", "Bearing2_1"), "speed")
    res = trust.evaluate_trust(ctx, _rec(_good()))
    assert set(res.blocks) >= {"ORDER_ANALYSIS", "LOCALIZATION"}
    assert res.tasks == ["MEASURE_SHAFT_SPEED"]


def test_unverified_regime_blocks_baseline_comparison():
    ctx = trust.with_unverified(trust.xjtu_context("40Hz10kN", "Bearing3_1"), "regime")
    res = trust.evaluate_trust(ctx, _rec(_good()))
    assert "BASELINE_COMPARISON" in res.blocks


def test_bad_signal_blocks_everything_and_requests_recapture():
    ctx = trust.xjtu_context("35Hz12kN", "Bearing1_3")
    short = trust.evaluate_trust(ctx, _rec(_good(100)))
    assert not short.signal_ok and short.tasks == ["RECAPTURE_SIGNAL"] and "ALL" in short.blocks
    nan = _good(); nan[5] = np.nan
    assert not trust.evaluate_trust(ctx, _rec(nan)).signal_ok
    clipped = _good() * 0.01; clipped[:1000] = 1.0; clipped[1000:2000] = -1.0
    assert not trust.evaluate_trust(ctx, _rec(clipped)).signal_ok
    assert not trust.evaluate_trust(ctx, _rec(np.zeros(32768))).signal_ok        # flatline = dead sensor
    assert not trust.evaluate_trust(ctx, _rec(_good(), fs=20000.0)).signal_ok
