# Bearing Witness

**An always-on, fully local bearing-screening agent on the Dell Pro Max with GB10.**
Built by Team Hermit Crab at the Dell x NVIDIA AI Hackathon, New York City, August 22, 2026.

> Detect the change. Explain the spectrum. Escalate with evidence. A human has to say yes.

Plants lose a median of $125,000 per hour to unplanned downtime (ABB, Value of
Reliability survey, 2023, n=3,215), and in the largest utility motor reliability
study ever run, 41% of all failures came down to bearings (Albrecht et al., IEEE
Trans. Energy Conversion, 1986, 6,312 motors). The plants that need continuous
monitoring most are the ones whose vibration data is not allowed to leave the
building. Bearing Witness runs entirely on one box: SciPy owns the diagnosis,
a local model explains the evidence and files typed work orders, MongoDB keeps
the audit trail, and nothing ever leaves the room.

## Measured results (thresholds frozen before the run)

Frozen v3 evaluation over all 15 XJTU-SY run-to-failure bearings, no exclusions
(`eval/results_v3.json`, `eval/run_v3_output.txt`, thresholds sha embedded):

| Metric | Result |
|---|---|
| Wrong element calls | **0** |
| Missed detections | **0** (onset detected on 15 of 15) |
| Correct localizations | 10 exact + 1 cage-consistent |
| Honest abstentions | 4 (each carries its machine reason) |
| Warning lead time | median 99 min over 15 (98 excluding one structural floor; min 11, max 2,519) |

When the evidence does not clear the frozen 3-harmonic floor, the system
refuses to guess and says why. The refusal is a feature, not a failure mode.

## How it works

1. **Detect**: persistent change against the asset's own early, condition-matched
   baseline (one-sided modified z, group fusion, 3-window persistence).
2. **Explain**: known machine frequencies are labelled before any residual
   pattern is treated as bearing evidence.
3. **Corroborate**: a suspected fault must agree across the ordinary spectrum
   and the envelope spectrum, at slip-aware search widths.
4. **Escalate**: a typed work order is drafted with evidence locators; a human
   approves, rejects, or defers, and the decision write is compare-and-set so a
   refusal can never become an approval. Evidence is retained on rejection.

## Repository layout

| Path | What |
|---|---|
| `bearing_witness/` | The evidence engine: DSP, detection, trust gate, localization, contract, CLI |
| `eval/` | Frozen thresholds, evaluator, verbatim results over all 15 bearings |
| `bw_product/` | MongoDB store (validated collections, gated writes), NiceGUI evidence UI, engine adapter, always-on watch loop |
| `bearing-witness-tools/` | Six typed OpenClaw tools with confirm-before-mutate and an LLM output post-scan |
| `prep/` | Pre-event analysis harnesses (v1/v2 history that led to the frozen v3 design) |
| `tests/`, `bw_product/tests/` | 150+ tests across both layers |

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-product.txt

# engine + product tests (corpus-dependent tests skip with printed reasons)
.venv/bin/python -m pytest tests/ bw_product/tests/ -q -rs

# the UI (MongoDB optional: without it the app runs on a file-backed fallback
# and says so in the HUD)
.venv/bin/python -m bw_product.ui           # http://127.0.0.1:8080

# one window through the engine (requires the XJTU-SY dataset under data/)
.venv/bin/python -m bearing_witness analyze \
  --root data/XJTU-SY_Bearing_Datasets --condition 35Hz12kN \
  --bearing Bearing1_3 --record 155 --cache-dir eval/feature_cache
```

The XJTU-SY dataset (Wang et al., IEEE Trans. Reliability, 2020) is not
redistributed here; place it under `data/XJTU-SY_Bearing_Datasets/` to run
corpus-dependent paths. Derived features, fixtures, and evaluation results are
included.

## Honesty notes

- Starter scaffolding (fixtures, store, UI shell, engine skeleton) was built the
  night before the event and is disclosed plainly, as the event rules allow.
  Everything that runs (the engine, the wiring, the agent surface, the analysis)
  was built and gated at the event.
- Every number above comes from the frozen evaluator output committed in this
  repository. Wrong calls and abstentions are reported in the same sentence as
  the wins.
- The UI never renders an invented value: every chart, locator, and lamp state
  traces to a measured record with a sha256.

## Team Hermit Crab

Stephen Sookra (product loop, MongoDB, UI, demo), Vinh Le (evidence engine,
evaluator), Bharadhwaj K. (GB10 bring-up, inference serving), Jadyn Worthington
(OpenClaw agent surface, OpenShell policy).

MIT License. Built with NVIDIA NemoClaw, OpenClaw, OpenShell, MongoDB Community,
SciPy, and NiceGUI on a Dell Pro Max with GB10.
