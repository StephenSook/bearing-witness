"""PREP_PLAN item 2: spectral-kurtosis band sweep on Bearing1_3 file 155,
with BPFO harmonic-family sanity check, vs the guessed 2-4 kHz band."""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bw_dsp

SCRATCH = '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad'
DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3/155.csv'
FS = bw_dsp.FS

BANDWIDTHS = [4000.0, 2000.0, 1000.0, 500.0]
EDGE_LO, EDGE_HI = 1000.0, 12200.0
F0_LO, F0_HI = 105.2, 110.6          # BPFO fundamental search window (Hz)
HARM_TOL = 1.5                        # +/- Hz around each harmonic
BPFO_PRED = 107.907

x = bw_dsp.load_h(DATA)
print(f"loaded {DATA}: n={len(x)}")

# ---------- 1. build candidate bands and score ----------
bands = []
for bw in BANDWIDTHS:
    step = bw / 2.0
    c = EDGE_LO + bw / 2.0
    while c + bw / 2.0 <= EDGE_HI + 1e-9:
        bands.append((bw, c - bw / 2.0, c + bw / 2.0))
        c += step
print(f"total candidate bands: {len(bands)}")

rows = []
for bw, lo, hi in bands:
    xb = bw_dsp.bandpass(x, lo, hi)
    k_time = bw_dsp.excess_kurtosis(xb)
    env, _ = bw_dsp.envelope(x, (lo, hi))
    k_env = bw_dsp.excess_kurtosis(env)
    rows.append({"bw": bw, "lo": lo, "hi": hi, "k_time": k_time, "k_env": k_env})

rank_time = sorted(rows, key=lambda r: r["k_time"], reverse=True)
rank_env  = sorted(rows, key=lambda r: r["k_env"],  reverse=True)

print("\n--- top 10 by TIME-signal excess kurtosis ---")
for r in rank_time[:10]:
    print(f"  {r['lo']:7.0f}-{r['hi']:7.0f} Hz (bw {r['bw']:.0f})  k_time={r['k_time']:8.3f}  k_env={r['k_env']:8.3f}")
print("\n--- top 10 by ENVELOPE excess kurtosis ---")
for r in rank_env[:10]:
    print(f"  {r['lo']:7.0f}-{r['hi']:7.0f} Hz (bw {r['bw']:.0f})  k_time={r['k_time']:8.3f}  k_env={r['k_env']:8.3f}")

agree = (rank_time[0]["lo"], rank_time[0]["hi"]) == (rank_env[0]["lo"], rank_env[0]["hi"])
print(f"\nrankings agree on winner: {agree}")
print(f"  time winner: {rank_time[0]['lo']:.0f}-{rank_time[0]['hi']:.0f} Hz  k_time={rank_time[0]['k_time']:.3f}")
print(f"  env  winner: {rank_env[0]['lo']:.0f}-{rank_env[0]['hi']:.0f} Hz  k_env={rank_env[0]['k_env']:.3f}")

# ---------- 2. BPFO harmonic-family sanity check ----------
def family_check(band):
    """Envelope spectrum of the band; best BPFO family f0 in [F0_LO,F0_HI].
    Returns dict with f0, per-harmonic peak amps, family sum, median 5-500 Hz, ratio."""
    freqs, amp = bw_dsp.envelope_spectrum(x, band)
    med = float(np.median(amp[(freqs >= 5.0) & (freqs <= 500.0)]))
    cand = freqs[(freqs >= F0_LO) & (freqs <= F0_HI)]
    best = None
    for f0 in cand:
        peaks = []
        ok = True
        for k in (1, 2, 3):
            m = np.abs(freqs - k * f0) <= HARM_TOL
            if not m.any():
                ok = False
                break
            peaks.append(float(amp[m].max()))
        if not ok:
            continue
        s = sum(peaks)
        if best is None or s > best["fam_sum"]:
            best = {"f0": float(f0), "peaks": peaks, "fam_sum": s}
    best["median"] = med
    best["ratio"] = best["fam_sum"] / med if med > 0 else float("inf")
    return best, freqs, amp

def band_key(r):
    return (r["lo"], r["hi"])

top5_time = rank_time[:5]
top5_env  = rank_env[:5]
check_bands = {}
for r in top5_time + top5_env:
    check_bands.setdefault(band_key(r), r)

fam = {}
print("\n--- BPFO family check on top-5 bands (by each score) ---")
print(f"    (f0 search {F0_LO}-{F0_HI} Hz, harmonics 1-3 each +/-{HARM_TOL} Hz, median over 5-500 Hz)")
for key, r in check_bands.items():
    res, _, _ = family_check(key)
    fam[key] = res
    tag = []
    if r in top5_time: tag.append(f"time#{rank_time.index(r)+1}")
    if r in top5_env:  tag.append(f"env#{rank_env.index(r)+1}")
    print(f"  {key[0]:7.0f}-{key[1]:7.0f} Hz [{','.join(tag):>12s}]  f0={res['f0']:7.3f}  "
          f"peaks={['%.4g' % p for p in res['peaks']]}  fam_sum={res['fam_sum']:.5g}  "
          f"median={res['median']:.5g}  ratio={res['ratio']:.1f}x")

# coherence flag: family must stand well above the noise floor
COHERENCE_MIN = 10.0   # fam_sum >= 10x median amplitude (3 harmonics, so ~3.3x each)
flagged = [k for k, res in fam.items() if res["ratio"] < COHERENCE_MIN]
print(f"\nbands flagged (ratio < {COHERENCE_MIN}x median => no coherent BPFO family): "
      f"{[f'{k[0]:.0f}-{k[1]:.0f}' for k in flagged] or 'none'}")

# ---------- 3. overall winner vs 2-4 kHz fallback ----------
# overall winner = top envelope-kurtosis band that passes the family coherence check
winner = None
for r in rank_env:
    key = band_key(r)
    if key not in fam:
        res, _, _ = family_check(key)
        fam[key] = res
    if fam[key]["ratio"] >= COHERENCE_MIN:
        winner = r
        break
wkey = band_key(winner)
wres = fam[wkey]
print(f"\nOVERALL WINNER: {wkey[0]:.0f}-{wkey[1]:.0f} Hz")
print(f"  k_env={winner['k_env']:.3f}  k_time={winner['k_time']:.3f}")
print(f"  f0={wres['f0']:.3f} Hz  fundamental peak={wres['peaks'][0]:.5g}  "
      f"fam_sum={wres['fam_sum']:.5g}  ratio={wres['ratio']:.1f}x")

fb_key = (2000.0, 4000.0)
fb_res, fb_freqs, fb_amp = family_check(fb_key)
fb_row = next(r for r in rows if band_key(r) == fb_key)
print(f"\nFALLBACK 2000-4000 Hz:")
print(f"  k_env={fb_row['k_env']:.3f}  k_time={fb_row['k_time']:.3f}")
print(f"  f0={fb_res['f0']:.3f} Hz  fundamental peak={fb_res['peaks'][0]:.5g}  "
      f"fam_sum={fb_res['fam_sum']:.5g}  median={fb_res['median']:.5g}  ratio={fb_res['ratio']:.1f}x")

same_family = abs(wres["f0"] - fb_res["f0"]) <= 1.5
print(f"\nsame family found (|f0 diff| <= 1.5 Hz): {same_family}  "
      f"(winner f0={wres['f0']:.3f}, fallback f0={fb_res['f0']:.3f})")
print(f"fundamental peak: winner {wres['peaks'][0]:.5g} vs fallback {fb_res['peaks'][0]:.5g}  "
      f"-> winner {'BETTER' if wres['peaks'][0] > fb_res['peaks'][0] else 'WORSE'} "
      f"({wres['peaks'][0]/fb_res['peaks'][0]:.2f}x)")
print(f"family sum:       winner {wres['fam_sum']:.5g} vs fallback {fb_res['fam_sum']:.5g}  "
      f"-> winner {'BETTER' if wres['fam_sum'] > fb_res['fam_sum'] else 'WORSE'} "
      f"({wres['fam_sum']/fb_res['fam_sum']:.2f}x)")
print(f"family SNR ratio: winner {wres['ratio']:.1f}x vs fallback {fb_res['ratio']:.1f}x")

# ---------- 4. figures ----------
# kurtogram heatmaps (paint each band's extent on its bandwidth-level row)
fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
for ax, score, label in [(axes[0], "k_time", "excess kurtosis of band-passed signal"),
                         (axes[1], "k_env",  "excess kurtosis of Hilbert envelope")]:
    vals = [r[score] for r in rows]
    vmin, vmax = min(vals), max(vals)
    for i, bw in enumerate(BANDWIDTHS):
        for r in rows:
            if r["bw"] != bw:
                continue
            colr = plt.cm.viridis((r[score] - vmin) / (vmax - vmin) if vmax > vmin else 0.5)
            ax.add_patch(plt.Rectangle((r["lo"], i - 0.45), r["hi"] - r["lo"], 0.9,
                                       facecolor=colr, edgecolor='k', linewidth=0.3))
    ax.set_yticks(range(len(BANDWIDTHS)))
    ax.set_yticklabels([f"{int(b)} Hz" for b in BANDWIDTHS])
    ax.set_ylim(len(BANDWIDTHS) - 0.5, -0.5)
    ax.set_ylabel("bandwidth")
    ax.set_title(label, fontsize=10)
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin, vmax))
    fig.colorbar(sm, ax=ax, pad=0.01, label="excess kurtosis")
    # mark winner and fallback
    ax.add_patch(plt.Rectangle((wkey[0], BANDWIDTHS.index(winner["bw"]) - 0.45),
                               wkey[1] - wkey[0], 0.9, facecolor='none',
                               edgecolor='red', linewidth=2.0))
axes[1].set_xlabel("frequency (Hz)")
axes[1].set_xlim(0, 12800)
fig.suptitle(f"Kurtogram sweep, Bearing1_3 file 155 (red = winner {wkey[0]:.0f}-{wkey[1]:.0f} Hz)")
fig.tight_layout()
fig.savefig(f"{SCRATCH}/kurt_kurtogram.png", dpi=140)
plt.close(fig)

# winner envelope spectrum 0-500 Hz with BPFO lines
_, wfreqs, wamp = family_check(wkey)
fig, ax = plt.subplots(figsize=(11, 4.5))
m = wfreqs <= 500
ax.plot(wfreqs[m], wamp[m], lw=0.8, color='C0')
for k in (1, 2, 3):
    ax.axvline(k * wres["f0"], color='r', ls='--', lw=1.0,
               label=f"measured {k}xBPFO = {k*wres['f0']:.1f} Hz" if k == 1 else None)
    ax.axvline(k * BPFO_PRED, color='gray', ls=':', lw=1.0,
               label=f"predicted {k}xBPFO ({BPFO_PRED:.1f} Hz)" if k == 1 else None)
ax.axhline(wres["median"], color='g', ls='-', lw=0.8,
           label=f"median 5-500 Hz = {wres['median']:.3g}")
ax.set_xlim(0, 500)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("envelope-spectrum amplitude")
ax.set_title(f"Envelope spectrum, winning band {wkey[0]:.0f}-{wkey[1]:.0f} Hz "
             f"(file 155): f0={wres['f0']:.2f} Hz, family sum {wres['fam_sum']:.3g} "
             f"= {wres['ratio']:.0f}x median")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(f"{SCRATCH}/kurt_winner_envelope.png", dpi=140)
plt.close(fig)
print("\nfigures written: kurt_kurtogram.png, kurt_winner_envelope.png")
