"""Synthetic signals for fast unit tests. fs/N match XJTU-SY so bin widths are realistic."""
import numpy as np

FS = 25600.0
N = 32768


def white(sigma=1.0, n=N, seed=0):
    return np.random.default_rng(seed).normal(0.0, sigma, n)


def tones(freqs_amps, n=N, fs=FS, noise=0.05, seed=0):
    """Sum of sinusoids [(f_hz, amp), ...] plus white noise."""
    t = np.arange(n) / fs
    x = np.random.default_rng(seed).normal(0.0, noise, n)
    for f, a in freqs_amps:
        x += a * np.sin(2 * np.pi * f * t)
    return x


def synth_fault(f_imp, n=N, fs=FS, carrier=3000.0, tau=0.001, amp=1.0, noise=0.2, seed=0):
    """Impulse train at f_imp Hz, each impulse exciting a decaying `carrier` Hz ring, in white noise.
    This is the textbook bearing-fault model the envelope chain is designed to recover."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, noise, n)
    period = fs / f_imp
    ring_t = np.arange(int(fs * tau * 6)) / fs
    ring = amp * np.exp(-ring_t / tau) * np.sin(2 * np.pi * carrier * ring_t)
    k = 0
    while True:
        i = int(round(k * period))
        if i >= n:
            break
        seg = ring[: n - i]
        x[i:i + len(seg)] += seg
        k += 1
    return x
