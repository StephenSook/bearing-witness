"""Stage 2 — explain known machine frequencies BEFORE blaming the bearing; and View A —
does the ordinary spectrum carry the family the envelope proposes?

Speed discipline: the 1x shaft peak found inside the setpoint's uncertainty window is refined
and used ONLY as the anchor for labelling shaft orders (k x anchor, tight 0.5% windows). Every
bearing-family prediction uses the setpoint (`shaft_hz_reference`). That is the spec §11 hard cut:
no speed inference feeds a fault frequency. Reported as `shaft_hz_measured` so the UI can show slip.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .dsp import BIN_W, half_width, local_noise, noise_floor, peak_in_window, refine_peak
from .thresholds import Thresholds
from .trust import AssetContext


@dataclass
class LabeledPeak:
    freq_hz: float
    amp: float
    label: str          # "1x shaft", "2x line", "unexplained"
    snr_local: float
    order: int | None = None


@dataclass
class ExplainResult:
    peaks: list[LabeledPeak]
    explained_hz: list[float]
    shaft_hz_reference: float         # the setpoint used for every prediction
    shaft_hz_measured: float | None   # reported only
    noise_floor: float


def _labelled(freqs, amp, f, hw, th: Thresholds) -> tuple[float, float, float] | None:
    fp, ap = peak_in_window(freqs, amp, f, hw)
    if not np.isfinite(fp):
        return None
    ln = local_noise(freqs, amp, fp, th.ordinary_local_span_hz, hw)
    if ln <= 0 or ap < th.ordinary_snr * ln:
        return None
    return fp, ap, ap / ln


def explain_ordinary(freqs, amp, ctx: AssetContext, th: Thresholds) -> ExplainResult:
    m = freqs <= th.ordinary_max_hz
    freqs, amp = freqs[m], amp[m]
    nf = noise_floor(freqs, amp, *th.ordinary_noise_band)
    f_ref = ctx.speed.value_hz
    peaks: list[LabeledPeak] = []
    explained: list[float] = []

    # 1x shaft: search the setpoint's uncertainty window; refine; use as the LABELLING anchor only
    measured = None
    hit = _labelled(freqs, amp, f_ref, half_width(f_ref, ctx.speed.uncertainty_rel), th)
    if hit:
        measured = refine_peak(freqs, amp, int(np.argmin(np.abs(freqs - hit[0]))))
    anchor = measured if measured is not None else f_ref

    for k in range(1, ctx.machine_map.shaft_orders + 1):
        f = k * anchor
        hit = _labelled(freqs, amp, f, max(BIN_W, th.shaft_order_rel * f), th)
        if hit:
            peaks.append(LabeledPeak(hit[0], hit[1], f"{k}x shaft", hit[2], order=k)); explained.append(hit[0])
    if ctx.machine_map.line_hz:
        for k in range(1, th.line_orders + 1):
            f = k * ctx.machine_map.line_hz
            hit = _labelled(freqs, amp, f, max(BIN_W, th.shaft_order_rel * f), th)
            if hit:
                peaks.append(LabeledPeak(hit[0], hit[1], f"{k}x line", hit[2], order=k)); explained.append(hit[0])

    # residual: strongest unexplained local maxima
    cand = np.flatnonzero((amp[1:-1] > amp[:-2]) & (amp[1:-1] >= amp[2:])) + 1
    cand = cand[amp[cand] >= th.residual_snr * nf] if nf > 0 else np.array([], dtype=int)
    cand = cand[np.argsort(-amp[cand])]
    for j in cand:
        f = float(freqs[j])
        if any(abs(f - e) <= half_width(e, ctx.speed.uncertainty_rel) for e in explained):
            continue
        ln = local_noise(freqs, amp, f, th.ordinary_local_span_hz, half_width(f, ctx.speed.uncertainty_rel))
        peaks.append(LabeledPeak(f, float(amp[j]), "unexplained", float(amp[j] / ln) if ln > 0 else 0.0))
        if sum(p.label == "unexplained" for p in peaks) >= th.residual_top_n:
            break
    return ExplainResult(peaks=peaks, explained_hz=explained, shaft_hz_reference=f_ref,
                         shaft_hz_measured=measured, noise_floor=nf)


@dataclass
class ViewAHarmonic:
    k: int
    freq_hz: float
    amp: float
    snr_local: float


@dataclass
class ViewASupport:
    supported: bool
    n_harmonics: int
    harmonics: list[ViewAHarmonic] = field(default_factory=list)
    reason: str = ""


def ordinary_supports(freqs, amp, f0: float, explained_hz: list[float], th: Thresholds) -> ViewASupport:
    """View A: count ordinary-spectrum harmonics k*f0 (k=1..view_a_harmonics) that are above the local
    floor AND not already explained as a machine component."""
    m = freqs <= th.ordinary_max_hz
    freqs, amp = freqs[m], amp[m]
    found: list[ViewAHarmonic] = []
    for k in range(1, th.view_a_harmonics + 1):
        f = k * f0
        hw = half_width(f, th.harm_rel)
        if any(abs(f - e) <= hw for e in explained_hz):
            continue
        hit = _labelled(freqs, amp, f, hw, th)
        if hit:
            found.append(ViewAHarmonic(k, hit[0], hit[1], hit[2]))
    ok = len(found) >= th.view_a_min_harmonics
    reason = "" if ok else f"ALL_HARMONICS_EXPLAINED_OR_BELOW_FLOOR_k1..{th.view_a_harmonics}"
    return ViewASupport(supported=ok, n_harmonics=len(found), harmonics=found, reason=reason)
