# Written Submission: Working Draft (skeleton, numbers land Saturday)

> Drafted Friday night per PLAN.md 4.4/4.5. Every `[MEASURED]` slot is filled ONLY
> from the frozen v3 evaluator run or a fresh Saturday freeze. Nothing ships with
> an empty slot: fill it or cut the sentence. Wired-or-cut sweep at the bottom
> runs before this text goes anywhere.

## One-liner

Bearing Witness watches real vibration trends locally, explains the machine's
known frequencies, and drafts an inspection only when two signal views agree. A
human has to say yes.

## What it does (the four jobs, in order)

1. **Detect** a persistent change from the same asset's early, condition-matched
   baseline: fault-agnostic indicators, persistence across adjacent windows, more
   than one feature group moving.
2. **Explain** known machine frequencies before treating any remaining pattern as
   bearing evidence.
3. **Corroborate** across the ordinary spectrum and the envelope spectrum; BPFO /
   BPFI / 2xBSF / FTF families support localization, they are not the detector.
4. **Escalate with evidence**: a drafted inspection work order that a human
   approves or rejects on screen. The decision is stored with the immutable
   evidence record in local MongoDB. Red means inspect, never replace.

Deterministic SciPy owns diagnosis. The local model explains tool results and
issues typed actions through narrow tools; it never writes diagnostic fields.
Delete the model and the detector, evidence, database, and human decision still
work.

## Honest proof boundary

Chronological replay of real XJTU-SY run-to-failure measurements (15 bearings,
25.6 kHz, 32,768 points / 1.28 s, one record per minute) with dataset-provided
speed and load setpoints. Not live sensors, not plant-wide validation, no RUL, no
severity grading, no non-bearing fault coverage. The corpus is not redistributed;
obtain it from the source and cite Wang, Lei, Li, Li, IEEE Trans. Reliability
69(1), 2020, DOI 10.1109/TR.2018.2882682.

The trust gate is load-bearing: unverified geometry blocks localization on the
same waveform and creates `VERIFY_BEARING_GEOMETRY`; the detector stays abnormal.
The slip finding is shown live in the trust panel: the documented 35.0 Hz
setpoint vs the measured ~34.7 Hz (0.8-1.5% low), which is why the search windows
are uncertainty-aware (Randall & Antoni 2011: bearing frequencies typically
deviate 1-2% from calculated values and wander around the mean).

## Measured results (frozen v3 evaluator run, Fri 2026-08-21 ~23:5x, no exclusions)

Source: `eval/results_v3.json` + `eval/run_v3_output.txt`, thresholds sha256
`59a9d901...01dc5` embedded in the output; thresholds frozen and committed
BEFORE the run.

- Zero wrong element calls and zero missed detections. Onset detected on all
  15 of 15 run-to-failure bearings.
- Suspected-location performance: 10 exact correct + 1 cage-consistent correct
  / 4 abstained / 0 wrong.
- Every abstention carries its machine reason: BEARING_PATTERN_LOCATION_UNCONFIRMED
  + INSUFFICIENT_HARMONICS_{BPFO,BPFI}_2_NEED_3 (the frozen 3-harmonic floor
  refusing an element call on two harmonics of evidence).
- Inner-race calls verified too (Bearing3_3, Bearing3_4), not only outer.
- Warning lead time (QUOTABLE after Task 14 reconciliation, `eval/onset_inspection.md`):
  15/15 onsets; lead 11 to 2519 minutes, median 99 over all 15 (98 over the 14
  bearings excluding B3_5, whose contaminated baseline makes its onset a
  structural floor rather than a measurement; we state both). Onset = first of
  3 consecutive one-sided abnormal windows after the 10-window baseline. The
  longest warning, Bearing3_1, was 2,519 minutes: forty-two hours of notice.
- End-to-end throughput on the GB10: [MEASURED Saturday on the box].

## Stack (name only what actually served)

Dell Pro Max GB10, fully local. NemoClaw + OpenClaw + OpenShell (deny-by-default
egress; denied requests are shown, not hidden). Local model: [WHICHEVER ACTUALLY
SERVED: kit `nvidia/Qwen3.6-35B-A3B-NVFP4` via vLLM | Ollama fallback], named
honestly. Self-managed MongoDB Community 8 on the box: versioned asset geometry,
time-series feature windows, schema-validated diagnostic cases with the embedded
task; task creation is a conditional single-document update, so no work order
exists without its evidence record. Python: SciPy, NumPy, NiceGUI, PyMongo.

## Scaffold disclosure (D5, plain language)

Per the event's "starter scaffolds and existing libraries are fine": our
Friday-night preparation went further than the word scaffolding suggests, and
we state it with timestamps rather than have anyone discover it. Prepared ahead
and logged as such in PLAN.md's status notes: the research plan, a signal-
processing prep study on the public XJTU-SY dataset, and, on Friday night, the
evidence engine and its CLI, the threshold freeze (Fri 23:37), the evaluation
run every number above comes from (Fri 23:44), the MongoDB store, and the UI
shell. Built on Saturday, on site, on the GB10: the box bring-up, the live
engine-to-MongoDB-to-UI wiring on real corpus data, the OpenClaw agent tools
and their locator-citation gate, the watch loop's resume-from-record, the
egress hardening and its live proof, and the demo itself, all visible in
Saturday's commit history.

## What we learned (fill Saturday; never write "the AI did it" or "no challenges")

- [What broke and how we recovered: e.g. the 11:15 model parachute decision,
  a validator surprise, the projector test.]
- [The physics lesson: kurtosis-ranked bands anti-correlated with demodulation
  quality; harmonic coherence beats spectral kurtosis rank.]
- [The product lesson: refusal-with-a-task reads stronger than a forced call.]

## Rubric mapping (event rules p.08: the four judged axes, in the rubric's own words)

- **Technical execution:** deterministic five-stage evidence pipeline on real
  run-to-failure data; frozen-before-run evaluation with the exact denominator;
  schema-validated MongoDB evidence store where a work order cannot exist without
  its evidence record; the whole loop demonstrated live, including refusal.
- **Usefulness:** an operations workflow (continuous bearing screening) that ends
  in a reviewable inspection work order, not a chat answer. The human decision is
  stored with the evidence; rejected drafts keep their evidence for the analyst.
- **Local-first design:** raw waveforms, asset geometry, evidence, and decisions
  never leave the box; deny-by-default egress is shown live (a denied request is
  part of the demo); the model, database, and UI all run on the GB10. Local is
  the product's requirement (plant OT isolation), not a constraint we tolerated.
- **Pitch quality:** five minutes, seven rehearsed steps, ends on the decision +
  evidence + task. Slides due 19:30 via URL (drafted in the afternoon).

MongoDB side challenge ("best use of MongoDB", confirmed on the event page):
ask on site whether self-managed Community qualifies before claiming entry.
Prepared answer, every clause greppable in the shipped store (hardened through a
10-round adversarial gate, 2026-08-21):

> MongoDB is not our persistence afterthought; it is the safety mechanism. Three
> collections carry the product's guarantees: `asset_configs` holds bearing
> geometry as immutable insert-only versions (unique compound index, retry-safe
> version allocation), the auditable record of what geometry the system was
> configured with; `feature_windows` is a native time-series collection that
> every LIVE analysis streams its window's measured features into, with source
> file and sha256 provenance; `diagnostic_cases` is
> `$jsonSchema`-validated (collMod re-enforced on every startup, so a stale
> collection can never dodge validation) with a unique analysis id. The two
> gates that make the agent trustworthy are Mongo write-shapes: a work order can
> only attach through a conditional single-document update that requires the
> gate status AND no existing draft, and the human decision is a compare-and-set
> filtering on status, task type, and prior decision, so a refusal case can
> never become INSPECTION_APPROVED and a recorded decision can never be
> silently overwritten, even by concurrent writers. Approve and reject both
> persist; rejection keeps the evidence. The database IS the audit trail.

## Wired-or-cut sweep (run BEFORE submitting; grep the shipped code)

| Claim | Grep in shipped source | Status |
|---|---|---|
| MongoDB (collections + validators + decisions) | `pymongo`, `create_collection`, `MongoDecisionStore` | [ ] |
| vLLM served the kit model | serve command in runbook/history + endpoint hit | [ ] |
| Ollama (only if the parachute fired) | `api/chat` caller | [ ] |
| OpenClaw typed tools | tool definitions in Jadyn's lane | [ ] |
| OpenShell deny-by-default | policy file + a shown 403 | [ ] |
| NemoClaw orchestration | onboard/config artifacts | [ ] |
| SciPy/NumPy diagnosis | `scipy.signal` imports in the engine | [ ] |
| NiceGUI UI | `nicegui` imports | [ ] |
| LLM draft post-scan | post-scan module in Jadyn's lane | [ ] |
| No claim of: RUL, deep learning, CMMS/MQTT, live sensors, 15/15 unless frozen-earned | text sweep | [ ] |

Also: em-dash sweep, AI-tone blocklist sweep, fictional-persona sweep (none
exist), synthetic-data sweep (fixtures are real Bearing1_3 records with sha256
provenance), operator-anonymity check (n/a), practitioner-privacy check (no
name, no recording, no slides anywhere in this text).
