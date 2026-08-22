"""Stage 3, View B — envelope-spectrum family scoring and the localization decision.

Frozen rules (see eval/frozen_thresholds_v3.md):
- band: SK-winner vs fixed 2–4 kHz, whichever yields the more coherent harmonic family (tie -> fixed)
- fundamental searched ±f0_rel of prediction; harmonic half-width max(0.5*bin, harm_rel*k*f0)
- family score = (sum of harmonic peaks + characteristic sideband pairs) / envelope noise floor
- explained-peak exclusion: competitors may not score peaks that are k*f0_top ± m*f_shaft
- decision: eligible runner-up, family_present, margin, harmonic floor, cage never confirmed
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

import numpy as np

from .dsp import BIN_W, FAMILIES, FS, envelope, envelope_spectrum, excess_kurtosis, half_width, noise_floor, peak_in_window
from .thresholds import Thresholds

ELEMENT = {"BPFO": "outer", "BPFI": "inner", "BSF2": "ball", "FTF": "cage"}


@dataclass
class HarmonicPeak:
    k: int
    freq_hz: float
    amp: float
    above_floor: bool


@dataclass
class SidebandPair:
    k: int
    lo_hz: float
    hi_hz: float
    lo_amp: float
    hi_amp: float


@dataclass
class FamilyScore:
    family: str
    predicted_hz: float
    f0: float | None
    score: float
    harmonics: list[HarmonicPeak] = field(default_factory=list)
    sidebands: list[SidebandPair] = field(default_factory=list)
    excluded_hz: list[float] = field(default_factory=list)

    @property
    def harmonics_above_floor(self) -> int:
        return sum(h.above_floor for h in self.harmonics)

    @property
    def sideband_pairs(self) -> int:
        return len(self.sidebands)


def sideband_spacing(family: str, f_shaft: float, preds: dict[str, float], th: Thresholds) -> float | None:
    for fam, kind in th.sideband_spacing:
        if fam == family:
            return f_shaft if kind == "shaft" else preds["FTF"]
    return None


def sk_winner_band(x, th: Thresholds, fs: float = FS) -> tuple[tuple[float, float], float]:
    """Compact kurtogram: spectral kurtosis = excess kurtosis of the envelope of the band-passed signal."""
    best, best_sk = th.demod_band, -np.inf
    for bw in th.sk_bandwidths:
        lo = th.sk_lo_hz
        while lo + bw <= th.sk_hi_hz:
            env, _ = envelope(x, (lo, lo + bw), fs)
            sk = excess_kurtosis(env)
            if sk > best_sk:
                best_sk, best = sk, (lo, lo + bw)
            lo += bw / 2
    return best, float(best_sk)


def explained_mask(freqs, f0_top: float, f_shaft: float, th: Thresholds) -> np.ndarray:
    mask = np.zeros(len(freqs), dtype=bool)
    for k in range(1, th.exclusion_harmonics + 1):
        for m in range(-th.exclusion_sidebands, th.exclusion_sidebands + 1):
            f = k * f0_top + m * f_shaft
            if f <= 0:
                continue
            hw = half_width(f, th.harm_rel)
            mask |= (freqs >= f - hw) & (freqs <= f + hw)
    return mask


def score_family(freqs, amp, noise: float, family: str, fpred: float, spacing: float | None,
                 th: Thresholds, mask=None) -> FamilyScore:
    amp_eff = amp if mask is None else np.where(mask, 0.0, amp)
    cands = np.arange(fpred * (1 - th.f0_rel), fpred * (1 + th.f0_rel), BIN_W / 2)
    best = FamilyScore(family, fpred, None, 0.0)
    best_sum = -1.0
    for f0 in cands:
        s = 0.0
        harms, sbs = [], []
        for k in range(1, th.n_harmonics + 1):
            f = k * f0
            hw = half_width(f, th.harm_rel)
            fp, ap = peak_in_window(freqs, amp_eff, f, hw)
            s += ap
            harms.append(HarmonicPeak(k, fp, ap, bool(noise > 0 and ap >= th.harm_snr * noise)))
            if spacing:
                flo, alo = peak_in_window(freqs, amp_eff, f - spacing, hw)
                fhi, ahi = peak_in_window(freqs, amp_eff, f + spacing, hw)
                if noise > 0 and alo >= th.harm_snr * noise and ahi >= th.harm_snr * noise:
                    s += alo + ahi
                    sbs.append(SidebandPair(k, flo, fhi, alo, ahi))
        if s > best_sum:
            best_sum = s
            best = FamilyScore(family, fpred, float(f0), float(s / noise) if noise > 0 else 0.0, harms, sbs)
    # Flat search windows make many grid candidates tie; report the MEASURED fundamental (the k=1 peak)
    # as f0 when it is real — View A, exclusion and the UI depend on f0 to ~1 Hz, not to the 2.5% grid.
    if best.harmonics and best.harmonics[0].above_floor and np.isfinite(best.harmonics[0].freq_hz):
        best.f0 = best.harmonics[0].freq_hz
    return best


@dataclass
class WindowLocalization:
    window: int
    band: tuple[float, float]
    band_source: str          # "fixed" | "sk"
    sk: float
    noise: float
    scores: dict[str, FamilyScore]
    top: str
    freqs: np.ndarray
    amp: np.ndarray


def _score_all(freqs, amp, preds, f_shaft, th, mask=None) -> dict[str, FamilyScore]:
    noise = noise_floor(freqs, amp, *th.noise_band)
    return {f: score_family(freqs, amp, noise, f, preds[f], sideband_spacing(f, f_shaft, preds, th), th, mask)
            for f in FAMILIES}


def localize_window(x, window: int, preds: dict[str, float], f_shaft: float, th: Thresholds,
                    fs: float = FS) -> WindowLocalization:
    band_sk, sk = sk_winner_band(x, th, fs)
    cands = []
    for source, band in (("fixed", th.demod_band), ("sk", band_sk)):
        freqs, amp = envelope_spectrum(x, band, fs)
        scores = _score_all(freqs, amp, preds, f_shaft, th)
        coherence = max(s.harmonics_above_floor for s in scores.values())
        cands.append((source, band, freqs, amp, scores, coherence))
    fixed, skc = cands
    source, band, freqs, amp, scores, _ = fixed if fixed[5] >= skc[5] else skc
    noise = noise_floor(freqs, amp, *th.noise_band)
    top = max(scores, key=lambda f: scores[f].score)
    if scores[top].f0 is not None:
        mask = explained_mask(freqs, scores[top].f0, f_shaft, th)
        for f in FAMILIES:
            if f == top:
                continue
            before = scores[f]
            after = score_family(freqs, amp, noise, f, preds[f], sideband_spacing(f, f_shaft, preds, th), th, mask)
            after.excluded_hz = [h.freq_hz for h in before.harmonics
                                 if h.above_floor and np.isfinite(h.freq_hz) and mask[np.argmin(np.abs(freqs - h.freq_hz))]]
            scores[f] = after
    return WindowLocalization(window, tuple(band), source, sk, noise, scores, top, freqs, amp)


@dataclass
class Aggregate:
    score: float
    harmonics: float
    sideband_pairs: float


def aggregate(locs: list[WindowLocalization]) -> dict[str, Aggregate]:
    return {f: Aggregate(score=float(median(l.scores[f].score for l in locs)),
                         harmonics=float(median(l.scores[f].harmonics_above_floor for l in locs)),
                         sideband_pairs=float(median(l.scores[f].sideband_pairs for l in locs)))
            for f in FAMILIES}


@dataclass
class Decision:
    call: str                 # SUSPECTED_OUTER|INNER|BALL · CAGE_CONSISTENT · ABNORMAL_LOCATION_UNCONFIRMED
    top: str | None
    runner: str | None
    margin: float | None
    reasons: list[str]


def decide(agg: dict[str, Aggregate], th: Thresholds) -> Decision:
    def eligible(f: str) -> bool:
        need = th.cage_min_harmonics if f == "FTF" else th.margin_min_harmonics
        return agg[f].harmonics >= need

    ranked = sorted(FAMILIES, key=lambda f: -agg[f].score)
    top = ranked[0]
    top_s = agg[top].score
    if not eligible(top):
        return Decision("ABNORMAL_LOCATION_UNCONFIRMED", top, None, None, [f"TOP_{top}_FAILS_COHERENCE_{agg[top].harmonics:g}"])
    comp = [f for f in ranked[1:] if eligible(f)]
    runner = comp[0] if comp else None
    runner_s = agg[runner].score if runner else 0.0
    margin = (top_s / runner_s) if runner_s > 0 else None
    if top_s < th.family_present:
        return Decision("ABNORMAL_LOCATION_UNCONFIRMED", top, runner, margin, [f"TOP_{top}_{top_s:.1f}_BELOW_{th.family_present:g}"])
    if runner_s > 0 and top_s < th.margin * runner_s:
        return Decision("ABNORMAL_LOCATION_UNCONFIRMED", top, runner, margin, [f"NO_MARGIN_{top}_{top_s:.1f}_vs_{runner}_{runner_s:.1f}"])
    if agg[top].harmonics < th.element_min_harmonics:
        return Decision("ABNORMAL_LOCATION_UNCONFIRMED", top, runner, margin, [f"INSUFFICIENT_HARMONICS_{top}_{agg[top].harmonics:g}_NEED_{th.element_min_harmonics}"])
    if top == "FTF":
        return Decision("CAGE_CONSISTENT", top, runner, margin, [])
    return Decision("SUSPECTED_" + ELEMENT[top].upper(), top, runner, margin, [])
