"""Shared DSP utilities for Bearing Witness prep work. NOT product code.

Conventions (locked by prior measured work, Aug 21):
- fs = 25600 Hz, N = 32768, bin = 0.78125 Hz
- Envelope chain: band-pass -> Hilbert -> |analytic| -> square -> subtract mean -> rFFT
- Horizontal channel = column 0 of each CSV (header row present)
- Search tolerance: half_width = max(0.5*bin, f_expected * rel_uncertainty)
- Measured slip on Bearing1_3: shaft ~34.7 Hz vs 35.0 setpoint (peaks run ~1% low)
"""
import math
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, hilbert

FS = 25600.0
N_EXPECTED = 32768
BIN_W = FS / N_EXPECTED  # 0.78125 Hz

GEOM = {"n": 8, "d": 7.92, "D": 34.55, "contact_angle_deg": 0.0}
CONDITIONS = {"35Hz12kN": 35.0, "37.5Hz11kN": 37.5, "40Hz10kN": 40.0}

FIXED_BANDS = [(2000.0, 4000.0), (4000.0, 6000.0), (6000.0, 8000.0), (8000.0, 10000.0)]
ENV_BAND = (2000.0, 10000.0)   # broad fixed resonance band for the envelope-energy feature
DEMOD_BAND = (2000.0, 4000.0)  # working demodulation band, validated on B1_3 file 155

FEATURE_GROUPS = {
    "energy":   ["rms", "p2p"],
    "shape":    ["crest", "kurtosis_excess"],
    "hf_band":  ["be_2000_4000", "be_4000_6000", "be_6000_8000", "be_8000_10000"],
    "envelope": ["env_energy"],
}

def fault_frequencies(f_shaft, n=8, d=7.92, D=34.55, contact_angle_deg=0.0):
    ratio = (d / D) * math.cos(math.radians(contact_angle_deg))
    return {
        "BPFO": (n / 2) * (1 - ratio) * f_shaft,
        "BPFI": (n / 2) * (1 + ratio) * f_shaft,
        "BSF2": 2 * (D / (2 * d)) * (1 - ratio ** 2) * f_shaft,
        "FTF":  0.5 * (1 - ratio) * f_shaft,
    }

def load_h(path):
    """Horizontal channel of one XJTU-SY CSV as float array."""
    return pd.read_csv(path).iloc[:, 0].to_numpy(dtype=float)

def bandpass(x, lo, hi, fs=FS, order=4):
    sos = butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, x)

def envelope(x, band=ENV_BAND, fs=FS):
    """(envelope, band-passed signal)."""
    xb = bandpass(x, band[0], band[1], fs)
    return np.abs(hilbert(xb)), xb

def envelope_spectrum(x, band, fs=FS):
    """(freqs, amplitude) of the squared, mean-subtracted envelope."""
    env, _ = envelope(x, band, fs)
    e2 = env ** 2
    e2 = e2 - e2.mean()
    amp = np.abs(np.fft.rfft(e2)) / len(x)
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs)
    return freqs, amp

def half_width(f_expected, rel_unc=0.02, bin_w=BIN_W):
    return max(0.5 * bin_w, f_expected * rel_unc)

def excess_kurtosis(a):
    a = np.asarray(a, dtype=float)
    ac = a - a.mean()
    var = np.mean(ac ** 2)
    if var <= 0:
        return 0.0
    return float(np.mean(ac ** 4) / var ** 2 - 3.0)

def features(x, fs=FS):
    """Six fault-agnostic Stage-1 indicator families. No BPFO lookup here."""
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

def robust_z(value, median, mad):
    """Modified z-score. MAD from an accepted baseline, never the full lifecycle."""
    if mad <= 0:
        return 0.0 if value == median else math.copysign(1e9, value - median)
    return 0.6745 * (value - median) / mad
