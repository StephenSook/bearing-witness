"""Stage-1 chronological feature replay over Bearing1_3 full life (158 windows).

Replay discipline: a window's state uses only windows 1..that window.
Baseline = windows 1..10 (median + MAD per feature, from baseline ONLY).
Windows 1..10 are the baseline-accumulation period; abnormal evaluation
begins at window 11 (evaluating earlier windows would peek at a baseline
not yet complete at that point in the replay).

Working thresholds (hypotheses, NOT calibrated):
  - feature abnormal if |modified z| >= 5
  - group abnormal if any member feature abnormal
  - window ABNORMAL if >= 2 groups abnormal
  - persistent ABNORMAL = 3 consecutive ABNORMAL windows
    (onset = first window of the first such run)
  - WATCH_EARLY = only hf_band and/or envelope groups moved (energy+shape quiet)
"""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import bw_dsp
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCRATCH = '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad'
DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'
N_WIN = 158
Z_THRESH = 5.0
PERSIST = 3
BASELINE_WINDOWS = list(range(1, 11))

# ---- 1. Features for all windows ----
rows = []
for w in range(1, N_WIN + 1):
    x = bw_dsp.load_h(f'{DATA}/{w}.csv')
    assert len(x) == bw_dsp.N_EXPECTED, f'window {w}: {len(x)} samples'
    rows.append(bw_dsp.features(x))
feat = pd.DataFrame(rows, index=range(1, N_WIN + 1))
feat.index.name = 'window'
feat.to_csv(f'{SCRATCH}/stage1_features.csv')
print(f'features computed for {len(feat)} windows -> stage1_features.csv')
print('feature columns:', list(feat.columns))

# ---- 2. Baseline stats (windows 1..10 ONLY) ----
base = feat.loc[BASELINE_WINDOWS]
med = base.median()
mad = (base - med).abs().median()
print('\nbaseline (windows 1..10) median / MAD:')
for c in feat.columns:
    print(f'  {c:16s} median={med[c]:.6f}  MAD={mad[c]:.6f}')

# ---- 3. z-scores + replay state machine ----
z = pd.DataFrame(
    {c: [bw_dsp.robust_z(v, med[c], mad[c]) for v in feat[c]] for c in feat.columns},
    index=feat.index,
)
z.to_csv(f'{SCRATCH}/stage1_zscores.csv')

group_abn = pd.DataFrame(index=feat.index)
for g, members in bw_dsp.FEATURE_GROUPS.items():
    group_abn[g] = (z[members].abs() >= Z_THRESH).any(axis=1)

states = {}
run = 0
onset = None
abnormal_windows = []
watch_early_windows = []
for w in range(1, N_WIN + 1):
    if w <= max(BASELINE_WINDOWS):
        states[w] = 'BASELINE'
        continue
    gm = group_abn.loc[w]
    moved = [g for g in bw_dsp.FEATURE_GROUPS if gm[g]]
    n_moved = len(moved)
    if n_moved >= 2:
        states[w] = 'ABNORMAL'
        abnormal_windows.append(w)
        run += 1
        if run >= PERSIST and onset is None:
            onset = w - PERSIST + 1  # first window of the first 3-run
    else:
        run = 0
        if n_moved >= 1 and set(moved) <= {'hf_band', 'envelope'}:
            states[w] = 'WATCH_EARLY'
            watch_early_windows.append(w)
        elif n_moved >= 1:
            states[w] = 'WATCH'
        else:
            states[w] = 'NORMAL'

# ---- 4. Report ----
print(f'\nonset window: {onset}')
lead_min = N_WIN - onset if onset else None
print(f'lead time before window {N_WIN}: {lead_min} minutes (1 record/minute)')

print('\ngroups moved at onset window with z-values:')
for g, members in bw_dsp.FEATURE_GROUPS.items():
    flags = {m: z.loc[onset, m] for m in members}
    hit = group_abn.loc[onset, g]
    print(f'  {g:9s} abnormal={hit}  ' + '  '.join(f'{m}={v:+.2f}' for m, v in flags.items()))

pre_onset_watch = [w for w in watch_early_windows if w < onset]
print(f'\nWATCH_EARLY windows before onset ({len(pre_onset_watch)}): {pre_onset_watch}')

pre_onset_abn = [w for w in abnormal_windows if w < onset]
# isolated = ABNORMAL runs before onset that never reached PERSIST length
iso_runs = []
if pre_onset_abn:
    start = prev = pre_onset_abn[0]
    for w in pre_onset_abn[1:]:
        if w == prev + 1:
            prev = w
        else:
            iso_runs.append((start, prev))
            start = prev = w
    iso_runs.append((start, prev))
print(f'isolated (non-persistent) ABNORMAL windows before onset: {pre_onset_abn}')
print(f'  as runs (start, end): {iso_runs}')

first_abn = abnormal_windows[0] if abnormal_windows else None
print(f'first ABNORMAL window ever: {first_abn}')
print('\nstate timeline (first occurrence of each transition):')
prev_state = None
for w in range(1, N_WIN + 1):
    s = states[w]
    if s != prev_state:
        print(f'  window {w:3d}: {s}')
        prev_state = s

# max z per group at onset and at window 158 for context
print('\nmax |z| per group at onset / at window 158:')
for g, members in bw_dsp.FEATURE_GROUPS.items():
    zo = z.loc[onset, members].abs().max()
    zf = z.loc[N_WIN, members].abs().max()
    print(f'  {g:9s} onset={zo:.1f}  final={zf:.1f}')

# ---- 5. Figure ----
GROUP_ORDER = ['energy', 'shape', 'hf_band', 'envelope']
fig, axes = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
zc = z.clip(-50, 50)
for ax, g in zip(axes, GROUP_ORDER):
    for m in bw_dsp.FEATURE_GROUPS[g]:
        ax.plot(zc.index, zc[m], lw=1.1, label=m)
    ax.axhspan(-Z_THRESH, Z_THRESH, color='green', alpha=0.10, label='|z| < 5 (normal)')
    ax.axhline(Z_THRESH, color='green', ls='--', lw=0.8)
    ax.axhline(-Z_THRESH, color='green', ls='--', lw=0.8)
    if onset:
        ax.axvline(onset, color='red', ls='-', lw=1.4)
        ax.text(onset + 1, 40, f'onset w{onset}', color='red', fontsize=9)
    ax.set_ylim(-55, 55)
    ax.set_ylabel('modified z (capped ±50)')
    ax.set_title(f'group: {g}', loc='left', fontsize=10)
    ax.legend(loc='upper left', fontsize=8, ncol=2)
axes[-1].set_xlabel('window index (1..158, 1 min per window)')
fig.suptitle('Bearing1_3 Stage-1 replay — modified z vs baseline (windows 1–10)', y=0.995)
fig.tight_layout()
fig.savefig(f'{SCRATCH}/stage1_trend.png', dpi=140)
print('\nfigure saved -> stage1_trend.png')
