import pytest

from bearing_witness import dsp, explain, trust
from bearing_witness.thresholds import THRESHOLDS as TH
from tests.synth import tones


def _ctx():
    return trust.xjtu_context("35Hz12kN", "Bearing1_3")


def test_labels_shaft_harmonics_and_reports_measured_speed_without_using_it():
    x = tones([(34.7, 1.0), (69.4, 0.4), (300.0, 0.5)], noise=0.5)
    freqs, amp = dsp.ordinary_spectrum(x)
    res = explain.explain_ordinary(freqs, amp, _ctx(), TH)
    labels = {p.label: p for p in res.peaks}
    assert "1x shaft" in labels and abs(labels["1x shaft"].freq_hz - 34.7) < dsp.BIN_W
    assert "2x shaft" in labels
    assert res.shaft_hz_measured == pytest.approx(34.7, abs=0.1)   # refined, anchors LABELS only
    assert res.shaft_hz_reference == 35.0                           # prediction still uses the setpoint (hard cut)
    assert labels["1x shaft"].order == 1 and labels["2x shaft"].order == 2
    unexplained = [p for p in res.peaks if p.label == "unexplained"]
    assert any(abs(p.freq_hz - 300.0) < 1.0 for p in unexplained)
    assert all(abs(f - 300.0) > 1.0 for f in res.explained_hz)
    assert all(p.order is None for p in unexplained)


def test_three_x_shaft_window_does_not_swallow_bpfo():
    """Real-data trap: 3x shaft (105 Hz) vs BPFO (107.9 Hz, measured 107.03). A 2% window at 3x
    reaches 107.1 Hz and would label the bearing peak as a shaft harmonic. The 0.5% anchored window must not."""
    x = tones([(34.7, 1.0), (107.03, 0.3)], noise=0.5)
    freqs, amp = dsp.ordinary_spectrum(x)
    res = explain.explain_ordinary(freqs, amp, _ctx(), TH)
    assert all(abs(f - 107.03) > 1.0 for f in res.explained_hz)


def test_view_a_supports_family_from_unexplained_harmonics():
    x = tones([(35.0, 1.0), (107.9, 0.3), (215.8, 0.2)], noise=0.5)
    freqs, amp = dsp.ordinary_spectrum(x)
    res = explain.explain_ordinary(freqs, amp, _ctx(), TH)
    va = explain.ordinary_supports(freqs, amp, 107.9, res.explained_hz, TH)
    assert va.supported and va.n_harmonics >= 2
    assert [h.k for h in va.harmonics][:2] == [1, 2]


def test_view_a_does_not_credit_explained_machine_peaks():
    x = tones([(35.0, 1.0), (70.0, 0.5), (105.0, 0.3)], noise=0.5, seed=3)
    freqs, amp = dsp.ordinary_spectrum(x)
    res = explain.explain_ordinary(freqs, amp, _ctx(), TH)
    va = explain.ordinary_supports(freqs, amp, 35.0, res.explained_hz, TH)   # "family" sitting on shaft orders
    assert not va.supported and va.n_harmonics == 0
    assert va.reason.startswith("ALL_HARMONICS_EXPLAINED_OR_BELOW_FLOOR")
