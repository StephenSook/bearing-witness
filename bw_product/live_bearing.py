"""Live series (spectra + broadband-RMS trend) for ANY of the 15 XJTU-SY
bearings, not just the curated Bearing1_3 story.

The diagnostic RESULT itself always comes from `engine_adapter.analyze_and_store`
(the same gated CLI-subprocess -> Mongo path the "live analysis" row already
uses for Bearing1_3) -- nothing here ever originates a status or verdict. This
module only supplies the two spectra and the trend line the fleet-case screen
plots alongside that result, computed in-process through the real engine
package (bearing_witness.engine.Engine / .features / .data), never a
reimplementation of the DSP or the detector.
"""
from __future__ import annotations

import os
from pathlib import Path

from bearing_witness.data import load_record
from bearing_witness.engine import Engine, FeatureCache
from bearing_witness.features import compute_features
from bearing_witness.trust import xjtu_context

from .fixtures import data_root

# eval/feature_cache/{bearing}.csv is the SAME cache dir eval/run_eval.py
# itself points every Engine at -- a normal shared read/write cache, not a
# frozen artifact. Without it, a late-life window on a long bearing (e.g.
# Bearing3_1, 2538 windows) recomputes every prior window's features from
# scratch every single call (~15 ms/window, ~40s for that one), since the
# replay-discipline baseline/z-score math genuinely needs all of them, not
# just the requested window.
CACHE_DIR = Path(__file__).parent.parent / "eval" / "feature_cache"
_CACHE_DIR = CACHE_DIR  # internal alias, kept short at call sites below


def _root(root: str | None) -> str:
    return root or os.environ.get("BW_ENGINE_ROOT") or str(data_root())


def live_series(condition: str, bearing: str, record: int, *,
                 root: str | None = None, cache_dir: str | None = None) -> dict:
    """(ordinary, envelope) spectra for `record`, from the SAME Engine.analyze()
    call the CLI wraps, so the plotted spectra always match whatever
    status/candidate_families the persisted result already carries."""
    record_dir = Path(_root(root)) / condition / bearing
    eng = Engine(xjtu_context(condition, bearing), record_dir,
                cache_dir=cache_dir or str(_CACHE_DIR))
    analysis = eng.analyze(record)
    fo, ao = analysis.series["ordinary"]
    series = {"ordinary": [list(map(float, fo)), list(map(float, ao))], "envelope": None}
    if analysis.series["envelope"] is not None:
        fe, ae = analysis.series["envelope"]
        series["envelope"] = [list(map(float, fe)), list(map(float, ae))]
    return series


def live_trend(condition: str, bearing: str, through: int, *, root: str | None = None) -> dict:
    """Broadband RMS per window, 1..through -- the same feature
    (bearing_witness.features.compute_features) the engine's own Stage-1
    baseline/z-score math runs on, read here only for the trend line.
    Prefers the evaluator's own precomputed cache (instant); only falls back
    to recomputing a window from the raw CSV if that window is somehow
    missing from it, and never persists that fallback back into the cache."""
    record_dir = Path(_root(root)) / condition / bearing
    cache = FeatureCache(_CACHE_DIR / f"{bearing}.csv")
    windows, rms = [], []
    for w in range(1, through + 1):
        feats = cache.get(w)
        if feats is None:
            x = load_record(record_dir / f"{w}.csv", w).x
            feats = compute_features(x)
        windows.append(w)
        rms.append(feats["rms"])
    return {"windows": windows, "rms": rms}
