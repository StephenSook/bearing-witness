"""Pure signal math. No I/O, no state, no thresholds.

Conventions (measured on XJTU-SY, Aug 19–21 — see PREP_PLAN.md):
- fs = 25600 Hz, N = 32768 -> FFT bin 0.78125 Hz
- Envelope chain: band-pass -> Hilbert -> |analytic| -> square -> subtract mean -> rFFT
- Search tolerance: half_width = max(0.5*bin, f_expected*rel_uncertainty)
"""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

FS = 25600.0
N_EXPECTED = 32768
BIN_W = FS / N_EXPECTED  # 0.78125 Hz

FAMILIES = ("BPFO", "BPFI", "BSF2", "FTF")


def fault_frequencies(f_shaft: float, n: int = 8, d: float = 7.92, D: float = 34.55,
                      contact_angle_deg: float = 0.0) -> dict[str, float]:
    """BPFO/BPFI/2xBSF/FTF in Hz. 2xBSF is the primary rolling-element search (spec §2)."""
    ratio = (d / D) * math.cos(math.radians(contact_angle_deg))
    return {
        "BPFO": (n / 2) * (1 - ratio) * f_shaft,
        "BPFI": (n / 2) * (1 + ratio) * f_shaft,
        "BSF2": 2 * (D / (2 * d)) * (1 - ratio ** 2) * f_shaft,
        "FTF": 0.5 * (1 - ratio) * f_shaft,
    }


def bandpass(x, lo: float, hi: float, fs: float = FS, order: int = 4) -> np.ndarray:
    sos = butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, np.asarray(x, dtype=float))


def envelope(x, band: tuple[float, float], fs: float = FS) -> tuple[np.ndarray, np.ndarray]:
    """(envelope, band-passed signal)."""
    xb = bandpass(x, band[0], band[1], fs)
    return np.abs(hilbert(xb)), xb


def envelope_spectrum(x, band: tuple[float, float], fs: float = FS) -> tuple[np.ndarray, np.ndarray]:
    """(freqs, amplitude) of the squared, mean-subtracted envelope."""
    env, _ = envelope(x, band, fs)
    e2 = env ** 2
    e2 = e2 - e2.mean()
    amp = np.abs(np.fft.rfft(e2)) / len(e2)
    freqs = np.fft.rfftfreq(len(e2), d=1.0 / fs)
    return freqs, amp


def ordinary_spectrum(x, fs: float = FS) -> tuple[np.ndarray, np.ndarray]:
    """(freqs, amplitude) of the raw waveform, Hann-windowed, amplitude-corrected so a
    unit sine reads ~1.0."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    w = np.hanning(len(x))
    amp = 2.0 * np.abs(np.fft.rfft(x * w)) / w.sum()
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs)
    return freqs, amp


def half_width(f_expected: float, rel_unc: float = 0.02, bin_w: float = BIN_W) -> float:
    """Search half-width: never narrower than half a bin (practitioner rule, confirmed
    empirically on FTF — PREP_PLAN 'Resolution rule')."""
    return max(0.5 * bin_w, f_expected * rel_unc)


def noise_floor(freqs, amp, lo: float = 5.0, hi: float = 500.0) -> float:
    m = (freqs > lo) & (freqs <= hi)
    return float(np.median(amp[m])) if m.any() else 0.0


def local_noise(freqs, amp, f: float, half_span: float = 20.0, exclude_hw: float = 0.0) -> float:
    m = (freqs >= f - half_span) & (freqs <= f + half_span) & (np.abs(freqs - f) > exclude_hw)
    return float(np.median(amp[m])) if m.any() else 0.0


def peak_in_window(freqs, amp, f_center: float, hw: float) -> tuple[float, float]:
    """(freq, amp) of the largest bin within ±hw of f_center; (nan, 0.0) if no bin falls inside."""
    m = (freqs >= f_center - hw) & (freqs <= f_center + hw)
    if not m.any():
        return float("nan"), 0.0
    idx = np.flatnonzero(m)
    j = idx[np.argmax(amp[idx])]
    return float(freqs[j]), float(amp[j])


def refine_peak(freqs, amp, j: int) -> float:
    """Parabolic interpolation on log-amplitude of bins j-1..j+1. Reduces the 0.78 Hz bin
    quantization to ~0.05 Hz for a windowed sinusoid. Edge/zero bins fall back to the bin centre."""
    if j <= 0 or j >= len(amp) - 1 or amp[j - 1] <= 0 or amp[j] <= 0 or amp[j + 1] <= 0:
        return float(freqs[j])
    a, b, c = np.log(amp[j - 1]), np.log(amp[j]), np.log(amp[j + 1])
    denom = a - 2 * b + c
    if denom == 0:
        return float(freqs[j])
    delta = 0.5 * (a - c) / denom
    return float(freqs[j] + delta * (freqs[1] - freqs[0]))


def excess_kurtosis(a) -> float:
    a = np.asarray(a, dtype=float)
    ac = a - a.mean()
    var = np.mean(ac ** 2)
    if var <= 0:
        return 0.0
    return float(np.mean(ac ** 4) / var ** 2 - 3.0)


def robust_z(value: float, median: float, mad: float) -> float:
    """Modified z-score. MAD from an accepted baseline, never the full lifecycle."""
    if mad <= 0:
        return 0.0 if value == median else math.copysign(1e9, value - median)
    return 0.6745 * (value - median) / mad
