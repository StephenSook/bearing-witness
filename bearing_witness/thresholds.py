"""Every tunable in one frozen place. Mirror of eval/frozen_thresholds_v3.md.

Rule (spec §10): freeze BEFORE the evaluator run; do not tune after seeing results.
If these prove wrong we report that they were wrong. eval/run_eval.py embeds
thresholds_sha256() in its output so a result is bound to the exact values that produced it.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Thresholds:
    VERSION: str = "v3"

    # ---- Stage 1: detect (fault-agnostic) ----
    baseline_n: int = 10            # first N chronological windows, same asset + regime
    z_thresh: float = 5.0           # modified z, MAD-scaled
    one_sided: bool = True          # v3: abnormal only if z >= +z_thresh (fault physics: indicators rise)
    min_groups: int = 2             # fusion: >= 2 feature groups must move
    persist: int = 3                # consecutive ABNORMAL windows for onset
    watch_early_groups: tuple[str, ...] = ("hf_band", "envelope")

    # ---- Stage 3 View B: envelope family scoring ----
    demod_band: tuple[float, float] = (2000.0, 4000.0)   # validated fallback; coherence check may prefer SK band
    sk_bandwidths: tuple[float, ...] = (4000.0, 2000.0, 1000.0)
    sk_lo_hz: float = 1000.0
    sk_hi_hz: float = 12200.0
    noise_band: tuple[float, float] = (5.0, 500.0)       # envelope noise floor = median amplitude here
    f0_rel: float = 0.025           # fundamental search ±2.5% of prediction (setpoint slip measured ~1%)
    harm_rel: float = 0.015         # per-harmonic half-width = max(0.5*bin, harm_rel*k*f0)  (v2 change 2)
    n_harmonics: int = 3
    harm_snr: float = 3.0           # harmonic "above floor" if amp >= harm_snr * noise
    sideband_spacing: tuple[tuple[str, str], ...] = (("BPFI", "shaft"), ("BSF2", "FTF"))  # spec §2 table
    exclusion_harmonics: int = 5    # explained-peak exclusion: k*f0_top for k=1..5
    exclusion_sidebands: int = 2    # ... ± m*f_shaft for m=0..2
    family_present: float = 9.0     # ≈ three harmonics each 3x the floor
    margin: float = 1.5             # top family score >= margin * eligible runner-up
    margin_min_harmonics: int = 1   # a family may be runner-up only if >= 1 harmonic above floor (v2 change 3)
    cage_min_harmonics: int = 3     # FTF needs 3 to be eligible at all; never a confirmed element
    element_min_harmonics: int = 3  # v3: any element call needs >= 3 harmonics above floor (harmonic floor)
    loc_last: int = 5               # decide on median over the last 5 windows (<= current)

    # ---- Stage 2 + View A: ordinary spectrum ----
    ordinary_max_hz: float = 1000.0
    ordinary_noise_band: tuple[float, float] = (5.0, 1000.0)
    ordinary_local_span_hz: float = 20.0
    ordinary_snr: float = 3.0       # labelled machine-component peak if >= ordinary_snr * local noise
    shaft_orders: int = 10          # label 1x..10x shaft
    shaft_order_rel: float = 0.005  # shaft-order label half-width = max(bin, 0.5% * k * anchor); tight so
                                    # 3x shaft (105 Hz) never swallows BPFO (107.9 Hz)
    line_orders: int = 4
    residual_snr: float = 5.0       # unexplained peaks reported if >= residual_snr * global noise
    residual_top_n: int = 5
    view_a_harmonics: int = 5       # ordinary-spectrum harmonics k=1..5 of the envelope f0
    view_a_min_harmonics: int = 1   # View A supports the family if >= 1 unexplained harmonic above local floor


THRESHOLDS = Thresholds()


def thresholds_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
