"""Addendum: evaluate the same fake-tone window under a ONE-SIDED rule
(feature abnormal only if z >= +5, i.e. direction consistent with fault
physics: energy/impulsiveness INCREASES on damage). Documents the fix
hypothesis exposed by the two-sided build-test result."""
import sys
sys.path.insert(0, '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad')
import bw_dsp
import numpy as np
import pandas as pd

SCRATCH = '/private/tmp/claude-501/-Users-vinhle-NVIDIA-x-Dell/6607c0ed-43f4-4df2-abe6-2f22ffb845fb/scratchpad'
DATA = '/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY/35Hz12kN/Bearing1_3'

feat = pd.read_csv(f'{SCRATCH}/stage1_features.csv', index_col='window')
base = feat.loc[1:10]
med = base.median()
mad = (base - med).abs().median()

x = bw_dsp.load_h(f'{DATA}/3.csv')
rms3 = float(np.sqrt(np.mean(x ** 2)))
t = np.arange(len(x)) / bw_dsp.FS
x_mod = x + 5.0 * rms3 * np.sin(2 * np.pi * 107.907 * t)
f_mod = bw_dsp.features(x_mod)

hits = {}
for g, members in bw_dsp.FEATURE_GROUPS.items():
    zs = {m: bw_dsp.robust_z(f_mod[m], med[m], mad[m]) for m in members}
    hits[g] = any(v >= 5.0 for v in zs.values())
    print(f'  {g:9s} one-sided abnormal={hits[g]}  ' + '  '.join(f'{m}={v:+.2f}' for m, v in zs.items()))
moved = [g for g, h in hits.items() if h]
print(f'one-sided groups moved: {len(moved)} {moved}')
print(f'one-sided classification: {"ABNORMAL" if len(moved) >= 2 else "NOT ABNORMAL"}')

# does the replay Part A change under one-sided rules? (sanity: onset window)
z = pd.DataFrame({c: [bw_dsp.robust_z(v, med[c], mad[c]) for v in feat[c]] for c in feat.columns}, index=feat.index)
ga = pd.DataFrame(index=feat.index)
for g, members in bw_dsp.FEATURE_GROUPS.items():
    ga[g] = (z[members] >= 5.0).any(axis=1)
run = 0; onset1 = None
for w in range(11, 159):
    if ga.loc[w].sum() >= 2:
        run += 1
        if run >= 3 and onset1 is None:
            onset1 = w - 2
    else:
        run = 0
print(f'replay onset under one-sided rule (sanity check): {onset1}')
