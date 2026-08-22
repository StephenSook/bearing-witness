"""Steps 3-5: raw plot, band-pass + Hilbert + FFT, envelope spectrum 0-500 Hz.

Exploratory validation only — not product code.
Usage: python envelope_demo.py <csv_path> <out_png>
"""
import sys
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, hilbert

FS = 25600.0
BAND = (2000.0, 4000.0)          # initial guess, no kurtogram sweep yet

def fault_frequencies(n, d, D, rpm, contact_angle_deg=0.0):
    f = rpm / 60.0
    ratio = (d / D) * math.cos(math.radians(contact_angle_deg))
    return {
        "BPFO": (n / 2) * (1 - ratio) * f,
        "BPFI": (n / 2) * (1 + ratio) * f,
        "BSF2": 2 * (D / (2 * d)) * (1 - ratio ** 2) * f,
        "FTF":  0.5 * (1 - ratio) * f,
    }

def main(csv_path, out_png):
    ff = fault_frequencies(8, 7.92, 34.55, 2100)

    df = pd.read_csv(csv_path)
    print("columns:", list(df.columns), "| rows:", len(df))
    x = df.iloc[:, 0].to_numpy(dtype=float)      # horizontal channel
    N = len(x)
    t = np.arange(N) / FS

    # Step 4: band-pass -> Hilbert envelope -> square -> FFT
    sos = butter(4, BAND, btype="bandpass", fs=FS, output="sos")
    xb = sosfiltfilt(sos, x)
    env = np.abs(hilbert(xb))
    env2 = env ** 2
    env2 = env2 - env2.mean()                     # drop DC so the 0 Hz spike doesn't dwarf peaks
    spec = np.abs(np.fft.rfft(env2)) / N
    freqs = np.fft.rfftfreq(N, d=1.0 / FS)

    # Peak hunt near BPFO, resolution-aware half-width
    bin_w = FS / N
    half_w = max(0.5 * bin_w, ff["BPFO"] * 0.02)
    m = (freqs >= ff["BPFO"] - half_w) & (freqs <= ff["BPFO"] + half_w)
    pk_idx = np.argmax(np.where(m, spec, -np.inf))
    lo500 = (freqs > 5) & (freqs <= 500)          # ignore near-DC
    print(f"raw: n={N}, mean={x.mean():+.4f}, rms={np.sqrt((x**2).mean()):.4f}, "
          f"p2p={x.max()-x.min():.2f}, kurtosis(excess)={((x-x.mean())**4).mean()/x.var()**2 - 3:.2f}")
    print(f"band {BAND[0]:.0f}-{BAND[1]:.0f} Hz | bin={bin_w} Hz | BPFO search +/-{half_w:.3f} Hz")
    print(f"peak in BPFO window: {freqs[pk_idx]:.3f} Hz, amp {spec[pk_idx]:.4f}")
    top = np.argsort(np.where(lo500, spec, -np.inf))[::-1][:8]
    print("top peaks 5-500 Hz:")
    for i in sorted(top, key=lambda i: -spec[i]):
        print(f"  {freqs[i]:8.3f} Hz  amp {spec[i]:.4f}")

    # ---- figure: raw signal + envelope spectrum ----
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    name = csv_path.rsplit("/", 1)[-1]

    ax = axes[0]
    ax.plot(t, x, lw=0.3, color="#333")
    ax.set_title(f"Step 3 — raw signal, Bearing1_3/{name} (horizontal, {N} samples, 1.28 s)")
    ax.set_xlabel("time [s]"); ax.set_ylabel("accel")

    ax = axes[1]
    i0, i1 = 0, int(0.1 * FS)                     # 100 ms zoom
    ax.plot(t[i0:i1], xb[i0:i1], lw=0.4, color="#888", label=f"band-passed {BAND[0]:.0f}-{BAND[1]:.0f} Hz")
    ax.plot(t[i0:i1], env[i0:i1], lw=1.0, color="#c0392b", label="Hilbert envelope")
    exp_period = 1.0 / ff["BPFO"]
    ax.set_title(f"Step 4 — band-passed + envelope, first 100 ms (BPFO period = {exp_period*1000:.2f} ms)")
    ax.set_xlabel("time [s]"); ax.legend(loc="upper right")

    ax = axes[2]
    mm = freqs <= 500
    ax.plot(freqs[mm], spec[mm], lw=0.8, color="#1a5276")
    colors = {"BPFO": "#c0392b", "BPFI": "#7d3c98", "BSF2": "#1e8449", "FTF": "#b7950b"}
    for fam, fv in ff.items():
        ax.axvline(fv, color=colors[fam], ls="--", lw=1, alpha=0.8)
        ax.text(fv, ax.get_ylim()[1]*0.0, f" {fam}\n {fv:.1f}", color=colors[fam],
                fontsize=8, va="bottom")
    for h in (2, 3, 4):                            # BPFO harmonics
        ax.axvline(h * ff["BPFO"], color=colors["BPFO"], ls=":", lw=0.8, alpha=0.6)
        ax.text(h * ff["BPFO"], 0, f" {h}xBPFO", color=colors["BPFO"], fontsize=7, va="bottom")
    ax.set_xlim(0, 500)
    ax.set_title("Step 5 — envelope spectrum 0-500 Hz (squared envelope)")
    ax.set_xlabel("frequency [Hz]"); ax.set_ylabel("amplitude")

    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    print("saved:", out_png)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
