"""Stage-1 per-window indicators. FAULT-AGNOSTIC: no BPFO/BPFI/BSF/FTF lookup here (spec §3 Stage 1).

Names are frozen so the prep feature cache (eval/feature_cache/*.csv) stays valid.
"""
from __future__ import annotations

import numpy as np

from .dsp import FS, bandpass, envelope, excess_kurtosis

FIXED_BANDS = ((2000.0, 4000.0), (4000.0, 6000.0), (6000.0, 8000.0), (8000.0, 10000.0))
ENV_BAND = (2000.0, 10000.0)  # broad fixed resonance band for the envelope-energy feature

FEATURE_GROUPS: dict[str, list[str]] = {
    "energy": ["rms", "p2p"],
    "shape": ["crest", "kurtosis_excess"],
    "hf_band": ["be_2000_4000", "be_4000_6000", "be_6000_8000", "be_8000_10000"],
    "envelope": ["env_energy"],
}
FEATURE_NAMES: list[str] = [n for names in FEATURE_GROUPS.values() for n in names]


def compute_features(x, fs: float = FS) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    rms = float(np.sqrt(np.mean(x ** 2)))
    out = {
        "rms": rms,
        "p2p": float(x.max() - x.min()),
        "crest": float(np.max(np.abs(x)) / rms) if rms > 0 else 0.0,
        "kurtosis_excess": excess_kurtosis(x),
    }
    for lo, hi in FIXED_BANDS:
        xb = bandpass(x, lo, hi, fs)
        out[f"be_{int(lo)}_{int(hi)}"] = float(np.sqrt(np.mean(xb ** 2)))
    env, _ = envelope(x, ENV_BAND, fs)
    out["env_energy"] = float(np.sqrt(np.mean(env ** 2)))
    return out
