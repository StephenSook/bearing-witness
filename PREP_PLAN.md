# Prep Plan — Evidence Engine

Wednesday night → Friday. Everything here is learning and preparation, not product code.
Confirm scope with Stephen if anything feels close to the Rule 01 line.

## Engine hand-off (Aug 21)

- `from bearing_witness.engine import Engine; from bearing_witness.trust import xjtu_context, with_unverified`
- `eng = Engine(xjtu_context(cond, bearing), record_dir, cache_dir="eval/feature_cache")` — `a = eng.analyze(k)` → `a.result` is the 14-field contract (`model_dump()` for JSON), `a.series["ordinary"]`/`["envelope"]` are `(freqs, amp)` arrays for charts, `a.series["stage1"]` is the per-window z history for the trend plot.
- Decisions: `from bearing_witness.review import JsonDecisionStore, apply_decision` — `apply_decision(a.result, "APPROVE"|"REJECT"|"DEFER", reason, store)` (raises unless `result.status == "ANALYST_REVIEW_REQUIRED"`); Mongo store = same `record()` signature on the box.
- Demo step 7: `Engine(with_unverified(ctx, "geometry"), ...)` on the same window.
- CLI for the OpenClaw skill: `python -m bearing_witness analyze --root ... --condition ... --bearing ... --record N` prints the JSON.
- Status vocabulary: `contract.Status`. Traffic light maps `NO_ANOMALY_DETECTED`→green, `WATCH_EARLY`/`ABNORMAL_LOCATION_UNCONFIRMED`/`BLOCKED_*`→yellow, `ANALYST_REVIEW_REQUIRED`→red; always print the status string under the lamp.

---

## Measured findings (Aug 19)

Verified on my own machine. These are ours, not from a document.

### Frequencies — confirmed exact

| Family | Predicted | Note |
|---|---|---|
| BPFO | 107.907 Hz | Hand-checked term by term: 4 × 0.770767 × 35 |
| BPFI | 172.093 Hz | |
| 2×BSF | 144.660 Hz | |
| FTF | 13.488 Hz | The identity FTF = BPFO/8 holds |

### Bearing1_3, file 155 (98% through life) — outer race family present

Band-pass 2–4 kHz → Hilbert → square → FFT:

| Measured | Amplitude | Identity |
|---|---|---|
| 107.03 Hz | 0.638 | BPFO — predicted 107.91, Δ −0.88 Hz, inside ±2.16 window |
| 214.06 Hz | 0.594 | 2×BPFO, exact double |
| 321.09 Hz | 0.218 | 3×BPFO, exact triple |
| 120.3 / 227.3 / 334.4 Hz | ~0.2–0.3 | Each harmonic +13.28 Hz — cage-rate sidebands |

Raw signal: RMS 3.67, peak-to-peak 41, no visible periodicity. That's the argument for
demodulation in one plot.

### The slip finding — worth saying out loud in the pitch

Everything measured runs **0.8–1.5% low**. BPFO at 107.03 vs 107.91 predicted. Sideband
spacing 13.28 vs FTF's 13.49.

Both consistent with the shaft actually running **≈34.7 Hz, not the 35.0 Hz setpoint**.

This is live evidence for two things already in the spec:

1. **Why `TRUSTED_FOR_REPLAY` ≠ `TRUSTED_MEASURED`.** A documented setpoint is not per-window
   telemetry. The bearing does not run at the number on the datasheet.
2. **Why the search tolerance is doing real work.** A ±0.5% window would have missed this peak
   entirely.

### Resolution rule — confirmed empirically

FFT bin width = 25600 / 32768 = **0.78125 Hz**, half-bin = 0.39 Hz.

FTF is the **only** family where ±2% (0.27 Hz) is narrower than half a bin. The
`max(0.5 × bin_width, f × relative_uncertainty)` rule engages exactly there and nowhere else.

### Practical notes

- Official XJTU-SY site (biaowang.tech) is **down**. Hugging Face mirror hosts the full 5.4 GB
  zip; single bearings can be pulled via HTTP range requests without downloading everything.
- `data/` is gitignored — the dataset has no redistribution licence.
- **2–4 kHz is a working starting band** for this bearing. Keep it as the fallback if the
  kurtogram sweep misbehaves Saturday.

---

## Build order

Each item is small. Stop when a step works rather than polishing it.

### 1. Early-life contrast — do this first

Take a file from the first ~10 minutes of Bearing1_3. Run the **identical** chain.

**Expected:** no BPFO family. No peak at 107, no harmonic ladder, no cage sidebands.

Why it matters more than it looks:
- **First negative case.** You've proven the method finds a fault that's there. You have not
  proven it stays quiet when nothing is wrong. False-positive behaviour is what kills condition
  monitoring programmes.
- **If a healthy bearing shows a peak at 107 Hz, the chain is wrong** and you need to know
  tonight, not Saturday.
- It doubles as the **Stage 1 baseline** — record RMS, kurtosis, crest factor, band energy,
  envelope energy for those early windows. That's the reference every later window compares to.

### 2. Kurtogram band selection

Replace the guessed 2–4 kHz with a sweep.

Sweep candidate bands across 2–10 kHz, score each by **spectral kurtosis**, pick the most
impulsive. Compare the winner against 2–4 kHz on file 155 — does it find the same family,
better or worse?

**The trap to guard against:** the kurtogram can be fooled by impulsive noise unrelated to the
bearing. If a band scores high on kurtosis but produces **no coherent harmonic family**, that
means the band selection went wrong — not that the bearing is fine. Build that sanity check
alongside the sweep.

This is the fiddliest part of the chain and the most likely to eat Saturday. Better to fight it
now.

### 3. Stage 1 feature extraction

Six per-window indicators: RMS, peak-to-peak, crest factor, excess kurtosis, band energy,
envelope energy.

**Fault-agnostic — no BPFO lookup at this stage.** Otherwise you find the peak because you went
looking for it, then count the same evidence again during localization.

Baseline logic:
- First 10 chronological windows, same bearing and operating condition
- Robust scaling: median and MAD from the accepted baseline
- Persistence: at least 3 consecutive abnormal windows
- Fusion: at least 2 different feature groups must move
- **Only windows available at that point in the replay.** Never normalize using the completed
  lifecycle.

### 4. The build test

Inject a synthetic peak at 107.9 Hz into a baseline window. Confirm Stage 1 **cannot** be
bypassed and no element call is produced.

If a fake peak can trigger a diagnosis, the stage ordering isn't actually enforced.

### 5. Eval harness

Run the chain across all 15 bearings, compare against documented failure modes, produce a
score.

Nazar's line: *"so 'it works' is a number rather than a vibe."*

**Freeze thresholds before the run.** Do not claim a headline number unless a frozen evaluator
produced it with no exclusions and no later tuning.

Measure:
- Warning lead time before the terminal record
- Abstention rate and reason-code counts
- Wrong-call count with class denominators

### 6. Interface against mock data

NiceGUI: dropdown, chart, audio player, state display. Doesn't need real physics to exist —
only to display it.

The dashboard is a **scored requirement**, not decoration. Building it against fixtures now
means Saturday is wiring, not learning.

---

## Result contract — decide the shape early

Saturday you emit this. Deciding the fields now costs nothing and prevents a mid-build rewrite.

```json
{
  "analysis_id": "",
  "asset_id": "",
  "source_window": {},
  "input_trust": {},
  "anomaly_evidence": {},
  "machine_components": {},
  "ordinary_spectrum_evidence": {},
  "envelope_evidence": {},
  "candidate_families": [],
  "suspected_location": null,
  "status": "",
  "refusal_reasons": [],
  "inspection_draft": null,
  "human_review": null
}
```

**Evidence locators.** Every claim resolves to something checkable — asset, window, source hash,
frequency, harmonic, sideband. One vocabulary shared by the UI, the report, and the agent tools.

---

## Open items

- [x] Send Stephen the slip finding — RECEIVED 2026-08-21; goes in the demo trust panel (setpoint 35.0 vs measured ~34.7 Hz)
- [x] Confirm Rule 01 scope — CLEARED 2026-08-21: starter scaffolding per event wording, disclosed plainly in the submission; proceed past Task 0
- [ ] Watch for replies from Lei, Antoni, Randall, Green on the bin-width rule
- [ ] Box ownership if the roster changes — 09:00–11:30 needs a named owner before doors
- [ ] Only one copy of the kit exists

---

## Saturday reminders

- Features and baselines **do not wait on a GPU** — start at 9:00 regardless of box status
- If the model isn't serving by 11:15, that's someone else's switch decision, not your problem
- The result JSON exists whether or not a model is running. The demo narrows; it doesn't die.
- Freeze thresholds before the evaluator run
- **Do not reboot** after freeze — the inference container does not come back

---

## Measured findings (Aug 21, overnight run) — all six build-order items done

Every analysis item was independently re-verified by a second agent recomputing from raw
CSVs with shared DSP code (`scratchpad/bw_dsp.py`). Full corpus (all 15 bearings, 9,216
files) downloaded and extracted; counts match the Lei et al. tutorial table exactly.

### 1. Early-life contrast ✅ (verified)

Identical chain on files 2 and 8: **no BPFO family** — BPFO-window peaks at 1.8–2.0× the
noise median (floor level), no harmonic ladder, no sidebands. File 155's BPFO peak is
**303× larger** than file 2's. Strongest early peak is shaft frequency, as it should be.
Baseline features (files 1–10) recorded; all MADs tight (<3% of median) **except excess
kurtosis (MAD 3.4× its median)** — kurtosis z-scores will be jumpy; expected, it hovers
near zero on healthy records.

### 2. Kurtogram ✅ (verified) — the trap is real and worse than expected

Kurtosis rank is **anti-correlated with demodulation quality** here. Both SK variants
agree the winner is 11.5–12 kHz, but its BPFO family is **8× weaker** than the 2–4 kHz
fallback (family SNR 11.4× vs 30.1×). Full-sweep family scan says the best bands are LOW:
1–1.5 kHz (80.9×) and 1–5 kHz (largest absolute family sum). **Keep 2–4 kHz for Saturday;
never trust kurtosis without the harmonic-coherence check.** If changing, go 1–5 kHz,
validated on earlier weaker-fault files first.

### 3. Stage-1 replay ✅ (verified) — onset window 59, 99 min lead

Baseline 1–10, |z|≥5, ≥2 groups, 3-consecutive. Onset at window 59/158 (energy z≈+10/+8,
hf_band z≈+5.4). 12 WATCH_EARLY windows and 3 isolated abnormals before onset — all
absorbed by persistence; no false persistent onset. Two independent implementations (agent
+ evaluator) got window 59 exactly.

### 4. Build test ⚠️ FALSIFIED the two-sided rule — fix verified

A 107.9 Hz tone at 5× RMS moves **two** groups (energy UP, shape DOWN — a pure sine
suppresses crest/kurtosis), so the injected window classifies ABNORMAL under two-sided
|z|≥5. Persistence still blocks (one window ≠ 3), and the tone cannot survive the 2–4 kHz
band-pass (envelope amp near BPFO unchanged, ratio 1.0001) — **no element call possible**.
Verified fix for Saturday: **one-sided z ≥ +5 in fault-physics direction** → fake window
drops to 1 group (NOT abnormal); real onset unchanged at 59.

### 5. Frozen evaluator, all 15 bearings, no exclusions

Thresholds frozen before each run (`scratchpad/frozen_thresholds.md`, `_v2.md`; v3: `eval/frozen_thresholds_v3.md` at `3bda3b7`, run at `978f025`).

| | v1 (SK band, flat ±1.5 Hz) | v2 (coherence-checked band, resolution-aware windows) | v3 (Aug 21 23:43 EDT, frozen; one-sided z, harmonic floor, sidebands, exclusion, View A gate) |
|---|---|---|---|
| Correct element calls | 1 | **10** | **10** |
| Cage-consistent (B1_4) | 1 | 1 | 1 |
| Abstained | 13 | 3 | 4 (0 of them View A `VIEW_A_NO_SUPPORT`) |
| **Wrong calls** | **0** | **1** (B2_3: cage called outer) | **0** |
| Missed (no onset) | 0 | 0 | 0 |

**v3 (frozen run, 15/15, no exclusions): 0 wrong calls.** 10 correct / 1 cage-consistent / 4 abstain / 0 missed; View A abstains 0. vs v2 the wrong call is gone, correct set changed (−B2_4, −B3_2 on the harmonic floor as predeclared; +B2_5 via exclusion, +B3_3 via sidebands); 7 Stage-1 onsets moved later under one-sided z (table in `eval/frozen_thresholds_v3.md`). Onset semantics reconciled in `eval/onset_inspection.md` (Task 14 step 0, PLAN.md 1.8): v3 lead times are `files − onset`, onset = first of 3 consecutive one-sided abnormal windows after the 10-window baseline (earliest 11). Results verbatim: `eval/results_v3.json`, `eval/run_v3_output.txt`.

v3 detection: 15/15 onsets, lead 11–2519 min (median 99 over 15; 98 over the 14 without B3_5), v3 semantics (`eval/results_v3.json`); B3_5's 11 is the structural floor (baseline contaminated — `eval/onset_inspection.md`), not a measured onset, so its lead (103, the floor value) is not quoted on its own. The v2 aggregate ("lead 11–2519 min, median 129") is **dropped** (its min/max coincide with v3's only because B2_4 = 11 and B3_1 = 2519 are among the 8 bearings whose onset is identical under both rules; the median moved 129 → 99): v2 scored baseline windows (B3_5 onset 9) under two-sided |z|, and 7 of 15 onsets differ from v3 (B1_2, B2_1, B2_2, B2_3, B2_5, B3_4, B3_5 — recomputed from v3); the other 8 are identical under both rules. v1's abstentions were the
kurtogram trap (SK electing 11–12 kHz noise bands) plus FTF score inflation from the flat
±1.5 Hz harmonic window (11% of FTF!). v2 fixed both, as pre-declared.

Remaining v2 non-calls, diagnosed (v3 candidates — need fresh freeze, not tonight):
- **B2_3 WRONG (cage→outer):** envelope genuinely shows a 2–3-harmonic BPFO family; a
  fractured cage lets elements bunch and strike the outer race. Candidate guard: any FTF
  evidence alongside a BPFO family ⇒ flag possible cage involvement, dual-list.
- **B2_5 abstain (outer, margin 1.39 vs BSF2):** BPFO+shaft sideband (115.6+37.5=153.1 Hz)
  lands **inside** the BSF2 f0 search window (151–159 Hz) at condition 2 — cross-family
  window collision. Fix: explained-peak exclusion between competing families (this is
  literally Stage-2 discipline applied inside Stage-3).
- **B2_1/B3_3 abstain (inner, margins 1.15/1.43):** BPFI top with harmonics but no margin;
  inner-race energy spreads into shaft-spaced sidebands the scorer doesn't credit. The
  spec's own sideband rule, scored, would likely close both.

### 6. NiceGUI interface mock ✅

`scratchpad/ui_mock/` — serves HTTP 200; all three contract states (green/yellow/red)
from fixtures with exactly the 14 result-contract fields; traffic light always shows the
deterministic state string; approve AND reject both write `{decision, reason, timestamp}`
to decisions.json. Playwright click-test skipped (not installed) — handler verified by
direct invocation.

### Corpus + ground truth

- Full dataset at `data/XJTU-SY_Bearing_Datasets/` (gitignored), 9,216 files verified.
- `scratchpad/ground_truth.json` — failure elements extracted from the tutorial paper PDF
  itself (not recall); file counts cross-sum to 9,216. The paper quotes BPFO theory
  107.91 Hz — matches ours.

### Saturday to-dos generated tonight

- [x] Switch Stage-1 to one-sided z (fault-physics direction) — verified fix, re-freeze (v3)
- [ ] ~~Add FTF-evidence guard before naming outer (B2_3 lesson)~~ — NOT adopted in v3 (would have blocked B1_3 and missed B2_3; `frozen_thresholds_v3.md` §2); harmonic floor instead
- [x] Explained-peak exclusion between families (B2_5 lesson) (v3)
- [x] Score BPFI shaft-sidebands per spec (B2_1/B3_3 lesson) (v3)
- [ ] Consider 1–5 kHz demod band, validated on early files first
- [x] Onset at window 9 on B3_5 — RESOLVED (Task 14, `eval/onset_inspection.md`): v2 scored baseline windows 1–10 against their own median under two-sided |z| (`prep/eval_harness.py:63-77`), so window 9 was an artifact; v3 holds 1–10 as BASELINE (earliest 11). B3_5 baseline is contaminated (rms 14.8 MAD inside 1–10; defect present near start) → v3 onset 11 is the floor, no B3_5 lead time quoted.
      B3_1 onset 19/2538 — baseline clean (≤2.6 MAD), gradual hf_band → envelope rise; genuine v3 onset, lead 2519 min quotable after 1.8 ✅
