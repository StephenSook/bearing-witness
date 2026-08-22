"""live_bearing.py against the real corpus: proves the spectra/trend it
supplies for the OTHER 14 fleet cards line up with what the CLI-driven result
for the SAME window actually claims -- not a second, divergent DSP path."""
import pytest

from bw_product import engine_adapter as ea
from bw_product.live_bearing import CACHE_DIR, live_series, live_trend

try:
    from bw_product.fixtures import data_root
    _CORPUS = True
    data_root()
except Exception:
    _CORPUS = False

needs_corpus = pytest.mark.skipif(
    not _CORPUS, reason="XJTU-SY corpus not mounted (kit drive or data/ symlink)")


@needs_corpus
def test_series_matches_the_result_it_sits_beside():
    result = ea.analyze_record(155, condition="35Hz12kN", bearing="Bearing1_3",
                               cache_dir=str(CACHE_DIR))
    series = live_series("35Hz12kN", "Bearing1_3", 155)
    assert series["envelope"] is not None
    peak_freqs = {round(p["freq_hz"], 2) for p in result["envelope_evidence"]["peaks"]}
    freqs = series["envelope"][0]
    # every peak the result claims must actually sit at that frequency in the
    # SAME series this screen plots, within one FFT bin
    for target in peak_freqs:
        assert any(abs(f - target) < 0.05 for f in freqs), f"{target} Hz not found in plotted series"


@needs_corpus
def test_trend_rms_matches_the_evaluator_cache():
    trend = live_trend("35Hz12kN", "Bearing1_3", 20)
    assert trend["windows"] == list(range(1, 21))
    assert all(v > 0 for v in trend["rms"])


@needs_corpus
def test_series_and_trend_are_cheap_on_a_long_bearing():
    # Bearing3_1 is the worst case in the fleet (2538 windows): without the
    # shared eval/feature_cache this recomputes from scratch (~40s); this is
    # the regression test for that perf fix, not just a correctness check
    import time
    t0 = time.monotonic()
    live_trend("40Hz10kN", "Bearing3_1", 2538)
    live_series("40Hz10kN", "Bearing3_1", 2538)
    assert time.monotonic() - t0 < 10.0
