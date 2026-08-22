import numpy as np
import pytest

from bearing_witness import dsp, families
from bearing_witness.thresholds import THRESHOLDS as TH
from tests.synth import synth_fault

PREDS = dsp.fault_frequencies(35.0)


def _spectrum_with_peaks(peaks, floor=1.0, fmax=600.0):
    """Synthetic envelope-spectrum arrays on the real bin grid: flat floor + delta peaks."""
    freqs = np.arange(0.0, fmax, dsp.BIN_W)
    amp = np.full_like(freqs, floor)
    for f, a in peaks:
        amp[np.argmin(np.abs(freqs - f))] = a
    return freqs, amp


def test_score_family_counts_harmonics_and_finds_f0_inside_tolerance():
    freqs, amp = _spectrum_with_peaks([(107.0, 30.0), (214.0, 20.0), (321.0, 10.0)])   # ~0.8% low (slip)
    fs = families.score_family(freqs, amp, 1.0, "BPFO", PREDS["BPFO"], None, TH)
    assert fs.harmonics_above_floor == 3
    assert abs(fs.f0 - 107.0) < 0.5
    assert fs.score == pytest.approx(60.0, rel=0.05)
    assert fs.sideband_pairs == 0


def test_bpfi_sidebands_credit_both_sides_only():
    f0 = PREDS["BPFI"]
    harm = [(k * f0, 20.0) for k in (1, 2, 3)]
    one_side = harm + [(k * f0 - 35.0, 10.0) for k in (1, 2, 3)]
    both = one_side + [(k * f0 + 35.0, 10.0) for k in (1, 2, 3)]
    s_h = families.score_family(*_spectrum_with_peaks(harm), 1.0, "BPFI", f0, 35.0, TH)
    s_1 = families.score_family(*_spectrum_with_peaks(one_side), 1.0, "BPFI", f0, 35.0, TH)
    s_2 = families.score_family(*_spectrum_with_peaks(both), 1.0, "BPFI", f0, 35.0, TH)
    assert s_h.sideband_pairs == 0 and s_1.sideband_pairs == 0 and s_2.sideband_pairs == 3
    assert s_1.score == pytest.approx(s_h.score)
    assert s_2.score == pytest.approx(s_h.score + 60.0, rel=0.05)


def test_explained_mask_covers_top_harmonics_and_shaft_sidebands():
    freqs = np.arange(0.0, 600.0, dsp.BIN_W)
    mask = families.explained_mask(freqs, 115.6, 37.5, TH)
    for f in (115.6, 231.2, 346.8, 115.6 + 37.5, 231.2 - 75.0):
        assert mask[np.argmin(np.abs(freqs - f))]
    assert not mask[np.argmin(np.abs(freqs - 180.0))]


def test_localize_window_on_synthetic_outer_fault_calls_outer_with_margin():
    x = synth_fault(PREDS["BPFO"])
    loc = families.localize_window(x, 1, PREDS, 35.0, TH)
    assert loc.top == "BPFO"
    assert loc.scores["BPFO"].harmonics_above_floor == 3
    agg = families.aggregate([loc])
    dec = families.decide(agg, TH)
    assert dec.call == "SUSPECTED_OUTER" and dec.top == "BPFO"
    assert dec.margin is None or dec.margin >= TH.margin     # None = no eligible competitor at all


def test_exclusion_removes_competitor_peak_explained_by_top_family_sideband():
    """B2_5 lesson: BPFO + 1x shaft sideband (115.6+37.5=153.1 Hz at condition 2) lands inside the
    BSF2 fundamental window. After exclusion BSF2 must not be credited for it."""
    preds = dsp.fault_frequencies(37.5)
    peaks = [(k * 115.6, 30.0) for k in (1, 2, 3)] + [(153.1, 25.0)]
    freqs, amp = _spectrum_with_peaks(peaks)
    raw = families.score_family(freqs, amp, 1.0, "BSF2", preds["BSF2"], preds["FTF"], TH)
    assert raw.harmonics_above_floor >= 1                       # fooled before exclusion
    mask = families.explained_mask(freqs, 115.6, 37.5, TH)
    masked = families.score_family(freqs, amp, 1.0, "BSF2", preds["BSF2"], preds["FTF"], TH, mask=mask)
    assert masked.harmonics_above_floor == 0 and masked.score < raw.score


def test_decide_rules():
    def agg(**kw):
        base = {f: families.Aggregate(score=5.0, harmonics=0.0, sideband_pairs=0.0) for f in dsp.FAMILIES}
        base.update(kw); return base
    A = families.Aggregate
    assert families.decide(agg(BPFO=A(30.0, 3, 0)), TH).call == "SUSPECTED_OUTER"
    assert families.decide(agg(BPFI=A(30.0, 3, 2)), TH).call == "SUSPECTED_INNER"
    assert families.decide(agg(BSF2=A(30.0, 3, 0)), TH).call == "SUSPECTED_BALL"
    d = families.decide(agg(BPFO=A(20.0, 2, 0)), TH)                         # harmonic floor (B2_3 lesson)
    assert d.call == "ABNORMAL_LOCATION_UNCONFIRMED" and d.reasons[0].startswith("INSUFFICIENT_HARMONICS_BPFO")
    d = families.decide(agg(BPFO=A(30.0, 3, 0), BSF2=A(25.0, 3, 0)), TH)       # no margin
    assert d.call == "ABNORMAL_LOCATION_UNCONFIRMED" and d.reasons[0].startswith("NO_MARGIN")
    d = families.decide(agg(BPFO=A(30.0, 3, 0), BSF2=A(25.0, 0, 0)), TH)       # runner-up not eligible
    assert d.call == "SUSPECTED_OUTER"
    d = families.decide(agg(BPFO=A(8.0, 3, 0)), TH)                            # below family_present
    assert d.call == "ABNORMAL_LOCATION_UNCONFIRMED" and "BELOW" in d.reasons[0]
    assert families.decide(agg(FTF=A(16.0, 3, 0)), TH).call == "CAGE_CONSISTENT"
    d = families.decide(agg(FTF=A(16.0, 2, 0)), TH)
    assert d.call == "ABNORMAL_LOCATION_UNCONFIRMED" and "FAILS_COHERENCE" in d.reasons[0]
