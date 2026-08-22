# Bearing Witness — Build Spec

Dell × NVIDIA Hackathon · New York · Saturday 22 August 2026
Team: Hermit Crab

> **Locked mechanism:** Detect the change. Explain the spectrum. Escalate with evidence.

> **Note on Rule 01:** the team brief says no product code before doors. This document is a
> specification and reference, not the product. Confirm with Stephen before writing anything
> that ships.

---

## 1. What we're building

A local agent that watches real vibration, explains the machine, and drafts an inspection
only when two signal views agree. A human has to say yes.

**Four jobs, in order:**

1. Detect a persistent change from the same asset's early, condition-matched baseline.
2. Explain known machine frequencies before treating any pattern as bearing evidence.
3. Corroborate a suspected fault across an ordinary spectrum **and** an envelope spectrum.
4. Draft the next task, then require human review before issuing a work order.

Calculated BPFO/BPFI/2×BSF/FTF **support localization**. They are not the detector, and they
are not a hard veto against a strong bearing pattern.

**What it is not:** not a CMMS, not a replacement for a vibration analyst, not RUL, not a
handheld sensor, not "every mechanical fault in the plant," not incident-log triage, not
B agents in parallel.

---

## 2. Physics reference

### The bearing

Rolling-element bearing = outer race (fixed to housing), inner race (clamped to shaft),
rolling elements (balls), cage (spacer). A defect sits on **one** of those four, and each
produces impacts at a different calculable rate.

### Demo bearing — LDK UER204 (XJTU-SY)

| Parameter | Value |
|---|---|
| Rolling elements (n) | 8 |
| Ball diameter (d) | 7.92 mm |
| Pitch diameter (D) | 34.55 mm |
| Contact angle (α) | 0° |
| Shaft speed | 2100 rpm = **35 Hz** |

### The four frequencies

```
BPFO = (n/2)(1 − d/D·cos α) · f_shaft
BPFI = (n/2)(1 + d/D·cos α) · f_shaft
BSF  = (D/2d)(1 − (d/D·cos α)²) · f_shaft
FTF  = (1/2)(1 − d/D·cos α) · f_shaft
```

Computed for the demo bearing:

| Family | Value | Note |
|---|---|---|
| **BPFO** | 107.9 Hz | Outer race |
| **BPFI** | 172.1 Hz | Inner race |
| **BSF × 2** | 144.7 Hz | **Search the double** — a rolling-element defect strikes both races per revolution |
| **FTF** | 13.5 Hz | Cage. Weak and ambiguous — never call cage from one sub-synchronous peak |

```python
def fault_frequencies(n, d, D, rpm, contact_angle_deg=0.0):
    import math
    f = rpm / 60.0
    ratio = (d / D) * math.cos(math.radians(contact_angle_deg))
    return {
        "BPFO": (n / 2) * (1 - ratio) * f,
        "BPFI": (n / 2) * (1 + ratio) * f,
        "BSF":  (D / (2 * d)) * (1 - ratio ** 2) * f,
        "BSF2": 2 * (D / (2 * d)) * (1 - ratio ** 2) * f,
        "FTF":  0.5 * (1 - ratio) * f,
    }
```

### Why a plain FFT doesn't work

The impacts are small and the machine is loud. But each impact **excites a structural
resonance** somewhere in 2–10 kHz — it rings like a struck bell. So the impact is invisible
at 107.9 Hz in the raw spectrum, but the high-frequency ringing *pulses* at 107.9 Hz.

Envelope analysis recovers the pulse rate:

1. Band-pass to the resonance band (discards loud low-frequency machine noise)
2. Hilbert envelope (traces the outline of the ringing, discards the carrier)
3. Square it
4. FFT the envelope → the impact repetition rate appears as a clean peak

### Search tolerance — critical

At 25.6 kHz over 32,768 points: record length **1.28 s**, FFT bin width **0.78125 Hz**.

A fixed ±2% window at FTF (13.5 Hz) is ±0.27 Hz — **narrower than half a bin**. The transform
cannot resolve it. Use:

```
half_width = max(0.5 × bin_width, f_expected × combined_relative_uncertainty)
```

Status: practitioner-supplied. Awaiting independent confirmation from academics contacted.
Until then it is **assumed**, not verified — do not claim it as validated.

### Severity — the trap

**Envelope peak height is not a severity scale.** It weakens as impacts broaden and overlap
in late-stage damage. A system reading that fall as recovery would be dangerously wrong.

Severity comes from ordinary-spectrum harmonics, sidebands, broadband energy, and noise
floor. Do not claim a universal failure stage or RUL.

### Pattern rules per family

| Family | Expected pattern |
|---|---|
| Outer race | BPFO harmonic family, usually weak sidebands |
| Inner race | BPFI harmonics with **shaft-speed** sidebands |
| Rolling element | Search primarily at **2×BSF**, harmonics with **FTF-spaced** sidebands |
| Cage | FTF evidence is weak and ambiguous — do not call from one peak |

---

## 3. The evidence engine — five stages

### Stage 0 — Trust

A mathematically correct frequency is still wrong when speed or geometry is wrong.

| Input | Store | If untrusted |
|---|---|---|
| Shaft speed | value, units, source, time alignment, uncertainty, VFD state | Block order analysis and element localization |
| Operating regime | load/condition ID and source | Block condition-matched trend comparison |
| Bearing internals | element count, element diameter, pitch diameter, contact angle, source | Block element localization |
| Acquisition | sample rate, channel, axis, clipping, source hash | Block conclusions, request recapture |
| Baseline | early chronological windows, same asset and regime | Block baseline-vs-change decision |
| Machine map | shafts, line frequency, gear teeth, belts, blades/vanes, known orders | Prevent bearing-specific claim until competing components explained |

**Two traps:**
- A bearing **model number is not geometry**. Two bearings with the same part number can
  contain different numbers of rolling elements. Version geometry for the installed bearing.
- **Speed error multiplies.** 1 Hz error at 1× becomes 10 Hz at the 10th order.

**XJTU-SY trust state:** `TRUSTED_FOR_REPLAY`, not `TRUSTED_MEASURED`. Speed and load are
documented test-condition setpoints, not per-window telemetry.

### Stage 1 — Detect (fault-agnostic)

**Do not look at BPFO/BPFI/BSF/FTF here.** Otherwise you find the peak because you went
looking for it, and then count the same evidence twice during localization.

Per-window indicators:

| Feature | Measures |
|---|---|
| RMS | Broadband energy |
| Peak-to-peak | Impact magnitude |
| Crest factor | Peak ÷ RMS |
| Excess kurtosis | Impulsive shape |
| Band energy | Fixed high-frequency ranges |
| Envelope energy | Fixed broad resonance band |

Compare each against an early chronological baseline from the **same bearing and operating
condition**. Use only windows available at that point in the replay. **Never normalize using
the completed lifecycle.**

Starting hypotheses (not claims):
- Minimum baseline: first 10 chronological windows
- Persistence: at least 3 consecutive abnormal windows
- Fusion: at least 2 different feature groups must move
- Robust scaling: median and MAD from the accepted baseline

These features come from the same waveform. Their agreement is supporting evidence, **not
independent probability votes**.

Outputs: `NO_ANOMALY_DETECTED` · `ABNORMAL` · `BLOCKED_BASELINE` · `BLOCKED_SIGNAL`
An early envelope-only or high-frequency change maps to `WATCH_EARLY`.

**Build test:** prove that injecting a fake fault-frequency peak into a baseline window
cannot bypass Stage 1 and produce an element call.

### Stage 2 — Explain

A peak in a "bearing zone" can be electrical, gear mesh, vane pass, or a shaft harmonic.
Name what the machine is expected to produce before blaming the bearing.

### Stage 3 — Corroborate

Two views must agree:

- **View A — ordinary spectrum:** explains synchronous machine components, tracks harmonics,
  sidebands, noise-floor change, later-stage progression.
- **View B — envelope spectrum:** recovers repetitive impact rates from resonance, supports
  family localization and early warning.

If the pattern looks like a bearing problem but the calculated line misses:
`BEARING_PATTERN_LOCATION_UNCONFIRMED`. That is **not** a clean bill of health.

### Stage 4 — Review

Draft the task. A human approves or rejects. No automatic work order.

### Decision rule

Produce a suspected element **only** when all are true:

1. Stage 1 found a persistent abnormal change without using fault-frequency labels
2. Speed, geometry, regime, sampling, and provenance passed the trust gate
3. Known machine components were explained
4. Ordinary and envelope spectra support the **same** bearing family
5. That family has a clear margin over competing families

Otherwise return watch, unconfirmed-location, or missing-measurement.

---

## 4. States

| Color | State | What a person should hear |
|---|---|---|
| Green | `NO_ANOMALY_DETECTED` | No persistent change in the evidence we have. **Not** "healthy." |
| Yellow | `WATCH_EARLY` / `ABNORMAL_LOCATION_UNCONFIRMED` | Something moved, or only one view agrees. |
| Red | `ANALYST_REVIEW_REQUIRED` | Two views support a draft inspection. **Not** "replace now." |

Human review flow:
1. Deterministic engine creates the evidence record
2. A corroborated suspected location creates an inspection draft
3. UI shows exact windows, frequencies, harmonics, sidebands, band selection, source hash, trusted context
4. Person approves, rejects, or defers
5. MongoDB stores the decision and reason with the immutable evidence record
6. Approval → `INSPECTION_APPROVED`. Rejection → `INSPECTION_REJECTED`, evidence retained

Missing evidence must create a **useful task**, not a guess:
`MEASURE_SHAFT_SPEED` · `VERIFY_BEARING_GEOMETRY` · `RECAPTURE_SIGNAL` · `ANALYST_REVIEW`

The product does not autonomously schedule a repair, choose an outage window, or invent a
part number.

---

## 5. Result contract

One stable JSON per analysis. This is the interface between the engine, the UI, and the
agent tools.

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

**Evidence locator format.** Every claim must resolve to something checkable — asset, window,
source hash, frequency, harmonic, sideband. One vocabulary shared by search results, UI
clicks, report footnotes, and agent tool output.

**The model is never the source of truth.** Schema-constrain output, validate with Pydantic,
then re-read the cited source and discard claims it cannot support. Store the original text
at the locator, never the model's quote. Recompute every number in Python.

---

## 6. Data

**XJTU-SY** — real accelerated run-to-failure bearing data.

| Property | Value |
|---|---|
| Bearings | 15, across 3 operating conditions |
| Files | 9,216 CSVs |
| Sample rate | 25.6 kHz |
| Points per record | 32,768 |
| Record length | 1.28 s |
| Cadence | one record per minute |
| Nyquist limit | 12.8 kHz |

**What it does not give us:** per-window tachometer telemetry, temperature, non-bearing fault
distractors, a standalone rolling-element failure for validation, proven channel units,
evidence above 12.8 kHz.

Therefore **do not claim**: ultrasonic 32–40 kHz detection, calibrated velocity, production
generalization, or false-alarm rejection against unbalance, misalignment, electrical faults,
looseness, and gears.

---

## 7. Stack

### Signal processing (this is the engine)

```python
import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert
```

| Layer | Choice | Note |
|---|---|---|
| DSP | SciPy + NumPy | Verified on ARM. CPU work, no GPU dependency. |
| Storage | MongoDB 8.0 ARM64 | Sponsor product. Assets, parts, history, decisions. |
| Interface | NiceGUI | Pure Python on FastAPI. Charts, audio, live refresh, no CSS. |
| Always-on | Heartbeat loop | Watches a directory, triggers analysis. This makes it an agent. |
| Runtime | Node 22 ARM64, CPython 3.12 | 68 aarch64 wheels staged, zero source distributions. |

**Rejected:** Streamlit (reads as a data-science notebook), DuckDB (no ARM wheels in recent
versions), GPU-accelerated DSP (launch overhead dominates at 32,768 samples; crossover is
hundreds of batched records).

### Model layer

| Item | Value |
|---|---|
| Model | `nvidia/Qwen3.6-35B-A3B-NVFP4`, revision `491c2f1` |
| Primary runtime | NemoClaw-managed vLLM, pinned ARM64 image |
| Flags | `--quantization modelopt --moe-backend marlin --tool-call-parser qwen3_coder` |
| Memory | `--gpu-memory-utilization 0.4` — KV cache is the hog |
| Endpoint | `localhost:8000` |
| **11:15 parachute** | Ollama `qwen3.6:35b-a3b-nvfp4` (~22 GB), Ollama 0.15+, native `/api/chat` **not** `/v1` |

`--moe-backend marlin` is **mandatory**: sm_121 lacks the tensor-core path the native FP4 MoE
kernel needs, so the CUTLASS path crashes and MoE layers must fall back to Marlin.

`qwen3_coder` is deliberate — `qwen3_xml` produced malformed tool arguments on a real DGX Spark.

### Required by the event

| Name | What it is |
|---|---|
| **OpenClaw** 2026.7.1-2 | Agent framework. Our skill is a markdown file that shells out to Python. |
| **NemoClaw** 0.0.110 | NVIDIA wrapper. Installs the stack, adds security controls. |
| **OpenShell** 0.0.106 | Sandbox runtime. Kernel isolation, default-deny networking, audit logging. |

### Hardware

Dell Pro Max with GB10 — Grace Blackwell, 20-core ARM, 128 GB unified LPDDR5X @ 273 GB/s,
sm_121, DGX OS 7.

**ARM changes everything.** Many Python packages ship x86-only binaries. sm_121 is *not* the
sm_100 of datacenter Blackwell — a container built for a B200 will not run here.

---

## 8. Known traps

| Trap | Mitigation |
|---|---|
| NemoClaw onboarding times out at 900s pulling its inference image | Pull manually before anything else |
| Sandbox file permissions fixed at creation | Get paths right first time or rebuild — an hour gone mid-build |
| Ollama's OpenAI-compatible endpoint silently drops tool calls | Use native `/api/chat`, not `/v1` |
| First-start CUDA-graph compilation runs 5–8 min after load | **Not a hang.** Don't kill and restart. |
| First request always slow regardless of config | Model warmup. Separate from the above. Also not a fault. |
| Standard NVIDIA vLLM container may lack the NVFP4 Blackwell MoE path | One GB10 recipe required `vllm/vllm-openai:cu130-nightly`. Verify. |
| KV cache pre-allocation is the biggest memory hog | Default 0.9 allocates ~89 GB for 6.2M tokens; single-user needs ~300K |
| Ollama on DGX Spark can detect the GPU but not use it | Silent CPU fallback. If throughput looks wrong, check logs for a skipped CUDA device. |
| Venue Wi-Fi had client isolation at a previous event | Blocked a team from reaching their own box. Direct ethernet as backup. |
| USB is 480 Mbps | Copy kit to internal NVMe before serving. Never serve a model off external. |
| Rebooting kills the inference container | It does not come back. Do not reboot after freeze. |

---

## 9. Demo

### Five-minute sequence

1. Replay one real bearing from early baseline to a persistent change
2. Show documented replay context and trust state
3. Explain known machine frequencies **before** considering a bearing pattern
4. Ordinary and envelope spectra side by side
5. Green / yellow / red with the exact deterministic state underneath
6. If red, open the inspection draft and approve or reject on screen
7. Mark geometry unverified, replay the same waveform → detector stays abnormal, localization
   stops, `VERIFY_BEARING_GEOMETRY` appears

The last screen is **a decision plus evidence plus action**. Not a lone spectrum.

### The audio beat — separate, native speed

Play one healthy record and one late-stage record at native 1.28 s. About three seconds of
sound, **outside** the seven steps. Bring a speaker; audio-out on the box is unverified. If
the room can't hear it, drop the claim.

Chronological replay stays one record per minute. Do not compress into a fake lifetime.

### Pitch structure (Nazar's shape — 2nd place Seattle, ran 1:49)

| Beat | Content |
|---|---|
| Open on money | "$125,000 an hour of unplanned downtime. 41% of industrial motor failures are one part." |
| The gap, one line | "The tools that catch this need to have already seen the machine fail — and these machines run nine years without failing." |
| The turn | "So we don't learn what failure sounds like. We calculate it." |
| Kill the objection | "You're wondering if this is playback. It is — that's how we prove the peaks land where physics said, against documented ground truth." |
| The refusal | Ambiguous evidence → NO CALL. "Any system that names one element here is lying to you." |
| Close | "One analyst with a handheld checks one machine a month. This watches every machine, continuously, and only interrupts a human when it can prove which part is breaking." |

### Why this box, honestly

The physics does not need Blackwell. SciPy does the diagnosis. Do not tell a judge we need
128 GB to compute RMS.

What the box is for: the event requires an always-on local agent on this machine with
NemoClaw/OpenClaw/OpenShell, and the vibration never leaves the room. Calls are sequential,
not a burst. If the model is down at noon, the result JSON still exists — the demo gets
narrower, it does not die.

---

## 10. Measurement

Measure what the user gets:

- Warning lead time before the terminal record (precise definition required)
- Alerts per early-life prefix or asset-day equivalent
- Abstention rate and reason-code counts
- Wrong-call count with class denominators
- Suspected-location performance on a **predeclared** bearing-level holdout, only if frozen
  before evaluation
- End-to-end throughput on the GB10

**Do not lead with chunk accuracy. Do not claim 15/15 unless a frozen evaluator produced it
with no exclusions and no later tuning.**

Freeze thresholds **before** the full evaluator run.

---

## 11. Hard cuts

- No PeakVue or proprietary shock-pulse claim
- No temperature without a real data source
- No general VFD speed inference
- No RUL, CNN, Transformer, autoencoder, LightGBM, or conformal guarantee
- No CMMS, MQTT, FUUZ, MaintainX, or ERBESSD claim unless wired end to end
- No literal handheld sensor claim
- No all-mechanical-fault claim
- No logs, contracts, or ticket-triage rebuild
- No "B workflows in parallel" pitch — Saturday is one sequential loop
- No unverified token-payback number on a slide

---

## 12. Door-time checklist

**Physics and data**
- [x] 2×BSF is the primary rolling-element search — `dsp.fault_frequencies` returns `BSF2`; `families.FAMILIES` has no BSF
- [x] BPFI sidebands use shaft-speed spacing — `thresholds.sideband_spacing` / `families.sideband_spacing`
- [x] Rolling-element sidebands use FTF spacing — `thresholds.sideband_spacing` / `families.sideband_spacing`
- [x] FFT-bin resolution is inside every search band — `dsp.half_width`, tested in `test_dsp.py`
- [x] Labels and future windows stay out of runtime decisions — `Engine.analyze(k)` reads only windows `1..k`; ground truth lives only in `eval/`
- [ ] Channel units verified before anyone says velocity

**Product**
- [ ] Traffic-light color always shows the deterministic state
- [ ] Red says inspection review, not replace now
- [x] Approve and reject both write a stored decision — `review.py`
- [ ] Every claim links to frequency, harmonic, sideband, window, source hash
- [x] Missing speed or geometry produces the matching task — `trust.py` + `test_engine.py`
- [x] No automatic repair scheduling or invented part number — `review._NOT_CLAIMED`

**Box**
- [ ] Kit copied to internal NVMe
- [ ] `verify_offline_kit.sh --quick` passes (not `--full` unless the drive was dropped)
- [ ] `prepare_gb10.sh` run
- [ ] Model serving — vLLM, or Ollama native `/api/chat` after 11:15
- [ ] `qwen3_coder` parser confirmed
- [ ] OpenShell egress deny during the judged demo
- [ ] Time-to-first-token written down

**Submission**
- [ ] Complete offline demo run three times
- [ ] Only measured evaluator results
- [ ] State chronological replay of real XJTU-SY measurements
- [ ] State dataset-provided speed and load setpoints
- [ ] Cut every unwired integration claim
- [ ] No private quotes, recordings, or training slides
- [ ] Original diagrams and independently verified equations only

---

## 13. Saturday schedule

| Window | What happens |
|---|---|
| 09:00–10:00 | Copy kit to NVMe, pull inference image manually, verify environment. DSP starts — features and baselines don't wait on a GPU. |
| 10:00–11:30 | Prove the environment end to end. **If the model isn't serving by 11:15, switch to Ollama rather than debug sm_121.** |
| 11:30–13:30 | Physics core. **Milestone: peaks land on the calculated lines.** |
| 13:30–15:00 | Evidence trend, calibrated threshold, refusal path. |
| 15:00–16:30 | Agent wiring — skill, heartbeat loop, work order, sandbox policy. |
| 16:30–17:30 | Interface. Non-negotiable — it is scored. |
| 17:30–18:00 | Freeze. Push. Write the submission. **Do not reboot.** |
| 18:00–20:00 | Rehearse three times, timed. |

---

## 14. Open questions

- **Bin-width tolerance is assumed, not verified.** Four academics contacted (Lei — XJTU-SY
  corresponding author and improved-kurtogram paper; Antoni — spectral kurtosis and fast
  kurtogram; Randall — 2011 bearing tutorial; Green — Georgia Tech Rotordynamics Lab). If any
  confirms, we can cite it.
- **Only one copy of the kit exists.** One drive, flying from Atlanta.
- **FP8 backup** proposed as a more-mature-support fallback. Not yet staged.
- **Pre-built code** — rules don't say publicly. Ask the organisers rather than guess.
- **Box ownership** is in flux. If it changes, the 09:00–11:30 window needs a named owner
  before doors.

---

## Reference

**Judging:** top 8 selected from **written submissions** before anyone pitches, then live
pitches decide the podium. The written submission is not an afterthought.

**The bench:** product and marketing people, not researchers. A comparable Dell/NVIDIA panel
had ten judges and zero research scientists. A rubric asked whether there is "a balanced blend
of frontend and backend" — the dashboard is scored, not decoration.

**The bar:** SF debut had 343 applications, 29 teams, **19 working demos**. A third of teams
had nothing that ran. Finishing is itself the differentiator.

---

*Most predictive-maintenance systems ask a model to recognise a failure it has seen before.
Ours computes what the machine's own physics says the failure must look like, checks whether
the machine agrees, and refuses to act when it doesn't.*
