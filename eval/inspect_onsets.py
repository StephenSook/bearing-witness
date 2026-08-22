"""Why does B3_5 fire at window 9 (inside the 10-window baseline!) and B3_1 at 19 of 2538?
Prints baseline rows, median/MAD, and z for the first 30 windows so a human can decide whether the
baseline is contaminated (defect present from the start) before anyone quotes a lead time.
Analysis only — changes nothing."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bearing_witness.detect import ReplayDetector                   # noqa: E402
from bearing_witness.engine import FeatureCache                      # noqa: E402
from bearing_witness.features import FEATURE_GROUPS                  # noqa: E402
from bearing_witness.thresholds import THRESHOLDS                    # noqa: E402

EVAL = Path(__file__).resolve().parent
SHOW = ["rms", "kurtosis_excess", "be_2000_4000", "env_energy"]
out = ["# Onset inspection — B3_5 and B3_1\n"]
for bearing in ("Bearing3_5", "Bearing3_1"):
    cache = FeatureCache(EVAL / "feature_cache" / f"{bearing}.csv")
    det = ReplayDetector(THRESHOLDS)
    res = [det.push(w, cache.get(w)) for w in range(1, 31)]
    out.append(f"\n## {bearing}\n\n### Baseline windows 1..10\n\n| w | " + " | ".join(SHOW) + " |\n|---|" + "---|" * len(SHOW))
    for w in range(1, 11):
        f = cache.get(w)
        out.append(f"| {w} | " + " | ".join(f"{f[n]:.4g}" for n in SHOW) + " |")
    b = det.baseline
    out.append("\nmedian: " + ", ".join(f"{n}={b.median[n]:.4g}" for n in SHOW))
    out.append("MAD:    " + ", ".join(f"{n}={b.mad[n]:.4g}" for n in SHOW))
    spread = {n: max(abs(cache.get(w)[n] - b.median[n]) / b.mad[n] for w in range(1, 11)) if b.mad[n] > 0 else float("inf") for n in SHOW}
    out.append("max |x-med|/MAD inside baseline: " + ", ".join(f"{n}={v:.1f}" for n, v in spread.items()))
    out.append("\n### Windows 11..30 (state, groups moved, z of shown features)\n\n| w | state | moved | " + " | ".join("z_" + n for n in SHOW) + " |\n|---|---|---|" + "---|" * len(SHOW))
    for r in res[10:]:
        out.append(f"| {r.window} | {r.state.value} | {','.join(r.moved) or '-'} | " + " | ".join(f"{r.z[n]:+.1f}" for n in SHOW) + " |")
    out.append(f"\nonset (one-sided v3 rule): {det.onset_window}")
    out.append("\nVerdict (human to fill): baseline clean / baseline contaminated (defect present near start) / unclear\n")
target = EVAL / "onset_inspection.md"
if target.exists() and "Verdict (human to fill)" not in target.read_text():
    # The file already carries the hand-written step-0 reconciliation and filled Verdicts (Task 14) that
    # PLAN.md / PREP_PLAN.md / TECHNICAL_REFERENCE.md cite. Never overwrite them; print the tables only.
    print(f"NOT WRITTEN: {target} holds hand-written reconciliation/verdicts — tables printed below only. "
          f"To regenerate from scratch, delete the file first and restore the prose from git.", file=sys.stderr)
else:
    target.write_text("\n".join(out) + "\n")
print("\n".join(out))
