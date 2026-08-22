# Bearing Witness — Plan & Coordination

> Living status doc for **Stephen Sookra**, **Vinh Le**, **Bharadhwaj (Beeds) K.**, and **Jadyn Worthington**. Updated on every task change and pushed to `main`. Single source of truth for who is working on what. **Atomic commits, never bundle a status change with code.**

**Project:** Always-on local bearing-screening agent on the Dell Pro Max with GB10. Detect the change, explain the spectrum, escalate with evidence. A human has to say yes.
**Team:** **Stephen** (leader: MongoDB, evidence UI, demo, submission), **Vinh** (evidence engine: DSP, detector, evaluator), **Beeds** (the box: kit copy, vLLM, first token), **Jadyn** (agent surface: OpenClaw tools, OpenShell policy, LLM post-scan).
**Event:** Dell x NVIDIA AI Hackathon, NYC. **Saturday 2026-08-22, doors 9:00, submission ~18:00, pitch 20:00 EDT.**
**Repo:** github.com/StephenSook/NVIDIA-x-Dell (PRIVATE, stays private). Saturday's judged artifact ships in a fresh public repo created at the event.

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⛔ blocked · ✂️ cut
**Stale lock TTL: 30 minutes** (single-day sprint). A 🟡 task without a fresh timestamp in Notes is claimable.

---

## Sources of truth (priority order)

1. **This file** for task ownership and status.
2. **`docs/superpowers/plans/2026-08-21-engine.md`** for the engine: module layout, code, tests, v3 evaluator. Review record: `docs/REVIEW_2026-08-21.md`.
3. **`PREP_PLAN.md`** for measured findings (frequencies, slip, kurtogram trap, v1/v2 evaluator history).
4. The product contract packets each of us already has (states, stages, claims discipline). Where anything conflicts, the contract packet wins on CLAIMS, the engine plan wins on CODE.
5. `README.md` is the public-facing blurb. Do not mirror this plan into it.

---

## ⏱️ Status snapshot (last sync: Friday 2026-08-21, pre-event)

Pre-event state: engine plan reviewed (SHIP WITH CHANGES, changes folded in), Rule 01 cleared as starter scaffolding with plain disclosure in the submission, all four v3 design changes approved, offline kit verified (73 wheels including pytest and pydantic, model, containers, corpus). Saturday 9:00 is first silicon. Nothing below runs on the GB10 until doors.

---

## Doors checklist (everyone, 9:00)

1. Beeds: kit → internal NVMe, `./09_VERIFY/verify_offline_kit.sh --quick`, `./09_VERIFY/prepare_gb10.sh`.
2. Everyone: `git pull` this repo, read your lane brief below, claim your first task (🟡 + timestamp + push).
3. Nobody sits in anyone else's terminal. One voice per lane on Discord: product/claims = Stephen, DSP = Vinh, box status = Beeds, tools/policy = Jadyn. Report an error once, with the exact text.
4. Stephen brings: LaCie + Cable 1, laptop, phone QR, power strip. (No physical prop; the pitch hook gestures at the bearing on screen.)
5. Stephen, before hacking starts: find the portal SUBMISSION SURFACE (did not exist pre-event) + re-check dashboard Resources for the full rubric ("shared before the event", still empty Fri night) + Q2 MongoDB side-challenge ask.

---

## Lane briefs

**Vinh, read first:** your engine plan is the build script. Start at 9:00; features and baselines do not wait on a GPU. If Beeds is stuck at 10:30 you give twenty minutes on the box, then back to DSP. Freeze thresholds before the full evaluator run. Emit the 14-field contract; everyone else builds against it.

**Beeds, read first:** you own the box end to end. Copy, load, serve, `qwen3_coder` parser confirmed, one line on Discord: "model up on localhost:8000". If vLLM is not serving by 11:15, switch to Ollama native `/api/chat` (not `/v1`) and say so once. Do not debug sm_121. "Qwen failed" is not a report; the exact error text is.

**Jadyn, read first:** six narrow typed tools against Vinh's CLI/JSON, nothing else. Confirm-before-mutate on every write. OpenShell denies raw files, the dashboard, and all egress (403s are demo material). Every claim carries an evidence locator. The post-scan is Saturday core: ban `replace` always, ban `confirmed` unless the status supports it, whole-word match, on fail swap a safe line from the JSON, never retry the model.

**Stephen:** Mongo backbone, UI, demo, fresh public repo, written submission. The written submission gates the top 8; it gets drafted during the afternoon, not at 17:30.

---

## Status Dashboard

### Phase 0 — Box bring-up (Beeds, 9:00 → 11:15 hard gate)

| # | Component | Where | Owner | Status | Deps | Notes |
|---|---|---|---|---|---|---|
| 0.1 | Kit copied to internal NVMe | box | **Beeds** | ⬜ | — | Never serve weights off USB |
| 0.2 | Kit quick verify PASS on box | `09_VERIFY/` | **Beeds** | ⬜ | 0.1 | Bare exit code, no pipe |
| 0.3 | Images loaded + tagged | `prepare_gb10.sh` | **Beeds** | ⬜ | 0.2 | ARM64 only; script refuses wrong silicon by design |
| 0.4 | vLLM serving kit NVFP4 checkpoint | `localhost:8000` | **Beeds** | ⬜ | 0.3 | marlin backend, util 0.4; KV cache is the memory hog |
| 0.5 | `qwen3_coder` parser confirmed + TTFT written down | box | **Beeds** | ⬜ | 0.4 | One-line report on Discord |
| 0.6 | 11:15 parachute (only if 0.4 fails) | Ollama | **Beeds** | ⬜ | — | `qwen3.6:35b-a3b-nvfp4` or `qwen3.8:27b`, native `/api/chat`. Do not feed the kit HF tarball to Ollama |
| 0.7 | De-risk gates: python imports, mongod ping, model lists, OpenClaw sees model, OpenShell denies egress | box | **Beeds** + **Jadyn** | ⬜ | 0.4 | All five before anyone claims the stack works |

### Phase 1 — Evidence engine (Vinh, 9:00 → 15:30)

The task list IS `docs/superpowers/plans/2026-08-21-engine.md` (Tasks 0-15). Track the milestones here, tick the tasks there.

| # | Milestone | Owner | Status | Deps | Notes |
|---|---|---|---|---|---|
| 1.1 | Package skeleton + prep rescued into repo (plan Task 0) | **Vinh** | ✅ | — | Runs on his laptop; box not required. 2026-08-21 20:15→20:25 Vinh — Fri-night scaffold only (D5 extension, disclosed): prep/ + eval/ rescued, pyproject, pytest installed (`no tests ran` = pass) |
| 1.2 | dsp/data/features/thresholds/detect green (Tasks 1-5) | **Vinh** | ✅ | 1.1 | TDD, tests first. 2026-08-21 20:41 Vinh — Tasks 1-5 via parallel agents (Fri-night start, D5 extension, disclosed like 1.1). 22:35 Vinh — Tasks 1/2/4 pushed 21:12; Wave C (Task 3 + 6-8, 10) dispatched. 23:00 Vinh — Wave C reviewed + pushed (39 tests). 23:20 Vinh — ✅ Task 5 `detect.py` reviewed + pushed; Tasks 1-5 green, 45 tests; v3 one-sided check `v3 10 3 5.0 True` |
| 1.3 | trust/explain/families/contract/review green (Tasks 6-10) | **Vinh** | ✅ | 1.2 | Task type is `INSPECTION_WORK_ORDER`. 2026-08-21 20:41 Vinh — Task 9 `contract.py` now (Wave B), Tasks 6-8, 10 in Wave C. 22:35 Vinh — Task 9 pushed 21:12; Tasks 6-8, 10 dispatched (Wave C). 23:1x Vinh — ✅ Tasks 6-10 reviewed + pushed (23:0x), 45 tests green |
| 1.4 | Engine + CLI green (Tasks 11-12) | **Vinh** | ✅ | 1.3 | `python -m bearing_witness analyze ...` is the tool surface for Jadyn. 2026-08-21 23:1x Vinh — Task 11 `engine.py` then Task 12 CLI (Wave E; Fri-night, D5 extension, disclosed). 23:1x Vinh — Task 11 committed, 51 fast + 4 slow tests green; Bearing1_3 w158 View A branch = ANALYST_REVIEW_REQUIRED (view_a_supports BPFO, onset 59, f0 107.03); Task 12 CLI in progress. 23:2x Vinh — ✅ engine + CLI green (56 fast + 4 slow tests); E4b locator gate 38/0 bad; `--speed-unverified` now withholds order analysis (spec trust table), `--geometry-unverified` → ABNORMAL_LOCATION_UNCONFIRMED/VERIFY_BEARING_GEOMETRY, acquisition-unverified → BLOCKED_SIGNAL/RECAPTURE_SIGNAL; `review.apply_decision` red-only (matches Mongo store). → Stephen (2.8: `from bearing_witness.engine import Engine`; `.analyze(k).result`, `.series`), → Jadyn (3.1/3.4: CLI command in Shared Contracts; parse locators by prefix, 5–7 segments) |
| 1.5 | **13:15 gate: one real Bearing1_3 window through engine → Mongo → UI** | **Vinh** + **Stephen** | ⬜ | 1.4, 2.2 | Plain screens fine. If missed: cut localization work until detection is causal and visible |
| 1.6 | Freeze v3 (or fresh Saturday freeze) BEFORE evaluator (Task 13 step 1-2) | **Vinh** | ✅ | 1.4 | Freeze doc committed before the run. No touching thresholds after. 2026-08-21 23:3x Vinh — writing `eval/frozen_thresholds_v3.md` (Wave F; Fri-night, D5 extension, disclosed); thresholds.py sha256 59a9d901 at 65f0478. 23:4x Vinh — ✅ freeze pushed at `3bda3b7` before `eval/run_eval.py` exists; View A expectation cites the B1_3 RED branch. **`bearing_witness/thresholds.py` is read-only for everyone from 3bda3b7 on** |
| 1.7 | Evaluator over all 15, results committed verbatim (Task 13) | **Vinh** | ✅ | 1.6 | Exact denominator. Wrong calls reported in the first sentence. 2026-08-21 23:4x Vinh — Wave G: writing `eval/run_eval.py` (Task 13 step 3), then the frozen run over 15 (Fri-night, D5 extension, disclosed) | 23:4x Vinh — ✅ frozen run at `978f025` (sha 59a9d901 = freeze): **0 wrong** / 10 correct / 1 cage-consistent / 4 abstain / 0 missed over 15/15, View A abstains 0; 7 onsets moved later under one-sided z (reported in freeze doc, no lead time quoted until 1.8). PREP_PLAN v3 column `348ccf1`. → Stephen (2.8, 4.4): numbers in `eval/results_v3.json` / `eval/run_v3_output.txt`
| 1.8 | Onset semantics reconciliation + B3_5/B3_1 inspection (Task 14) | **Vinh** | ✅ | 1.7 | v2 "window 9" is unreproducible under v3; no lead time quoted before this. 2026-08-21 23:5x Vinh — Wave H: Task 14 step 0 (v2-vs-v3 onset reconciliation) + `eval/inspect_onsets.py` (Fri-night, D5 extension, disclosed). 00:1x Vinh — ✅ reconciled in `eval/onset_inspection.md` (`00fc7bd`): v2 scored baseline windows 1–10 under two-sided \|z\| (B3_5 onset 9 = artifact); v3 never evaluates 1–10, one-sided, earliest 11. Verdicts: **B3_5 baseline contaminated → onset 11 is the floor, no B3_5 lead time quoted**; B3_1 baseline clean → onset 19 genuine. **Quotable now** (v3 semantics, files − onset, 15/15): min 11 / median 99 / max 2519 min (B3_5 counted at its floor value 103; excluding it median 98, min/max unchanged — say which); 8 onsets identical under both rules, 7 taken from v3, v2 aggregate dropped (PREP_PLAN). → Stephen (4.4): fill `docs/SUBMISSION_DRAFT.md:62-62` from this line + `eval/results_v3.json`; no RUL claim. → Stephen, Jadyn: engine hand-off in PREP_PLAN.md (top section, Task 15); spec §12 physics/product rows ticked with proof pointers; full suite 56 fast + 4 slow green |

### Phase 2 — Product loop (Stephen, 9:00 → 17:00)

| # | Component | Where | Owner | Status | Deps | Notes |
|---|---|---|---|---|---|---|
| 2.1 | MongoDB up locally, three collections + validators | box | **Stephen** | ✅ | 0.7 | `asset_configs` (immutable versioned geometry), `feature_windows` (time-series), `diagnostic_cases` (embedded task). Port bound to localhost only. 2026-08-21 18:25 Fri-night scaffold on Mac (D5 extension, disclosed); box wiring Sat |
| 2.2 | Repository layer + `MongoDecisionStore` | code | **Stephen** | ✅ | 2.1 | Implements Vinh's `DecisionStore.record()` protocol. Task creation is a conditional single-document update: no work order without its evidence record. 2026-08-21 18:25 scaffold in `bw_product/` (zero overlap with engine paths) |
| 2.3 | NiceGUI shell + HUD frame | code | **Stephen** | ✅ | — | Design language doc (local, gitignored): mono telemetry chrome, every HUD value real. 2026-08-21 18:25 Fri-night scaffold |
| 2.4 | Fleet screen (completed bearings only, exact denominator) | code | **Stephen** | ✅ | 2.3 | Judge can select only evaluated bearings |
| 2.5 | Evidence screen: trend, two spectra side by side, expected-family lines with uncertainty bands | code | **Stephen** | ✅ | 2.3, 1.4 | Consumes `Engine.analyze()` series dict |
| 2.6 | Trust/provenance panel incl. slip disclosure | code | **Stephen** | ✅ | 2.5 | Setpoint 35.0 vs measured ~34.7 Hz, shown, never used for prediction |
| 2.7 | Traffic light + exact state string + approve/reject writing stored decisions | code | **Stephen** | ✅ | 2.2 | Red says inspection review, never replace. Both buttons persist. 2026-08-21 19:00 UI-level REJECT verified into Mongo (evidence retained) |
| 2.8 | Fixtures → real engine, everywhere | code | **Stephen** | 🟡 | 1.7 | **SEAM RAN END-TO-END ON MAC Fri ~23:55**: real CLI → engine_adapter (double-validated) → gated Mongo → UI. Live W155 = ANALYST_REVIEW_REQUIRED/outer, f0 107.03125, score 30.10 (matches fixture's independent 30.1); live refusal = ABNORMAL_LOCATION_UNCONFIRMED + VERIFY_BEARING_GEOMETRY; WATCH MODE burst w1-5 all BLOCKED_BASELINE (v3 baseline honesty). LIVE ANALYSIS + START WATCH self-revealed in the UI. Saturday: re-run this exact gate ON THE BOX + swap fleet/evidence defaults to engine output after 1.7; 15:30 rule stands |
| 2.9 | `report.html` insurance page | code | **Stephen** | 🟡 | 2.8 | Self-contained, inline plotly; the demo survives a NiceGUI failure |
| 2.10 | Optional audio beat tested on the room speaker, or explicitly dropped | demo | **Stephen** | 🟡 | — | Native-speed 1.28 s clips, equal loudness. Inaudible = cut without mourning. 2026-08-21 19:00 claimed |

### Phase 3 — Agent surface (Jadyn, 9:00 → 16:30)

| # | Component | Where | Owner | Status | Deps | Notes |
|---|---|---|---|---|---|---|
| 3.1 | Six typed OpenClaw tools against the CLI/JSON | code | **Jadyn** | ⬜ | 1.4 | Disable toolSearch: the model sees six tools, not a catalog |
| 3.2 | Confirm-before-mutate on every write | code | **Jadyn** | ⬜ | 3.1 | No mutation without a human confirmation |
| 3.3 | OpenShell deny-by-default policy | policy | **Jadyn** | ⬜ | 0.7 | 403 on raw files, dashboard, all egress. The denied request is a demo beat |
| 3.4 | Evidence locators on every model claim | code | **Jadyn** | ⬜ | 3.1 | `asset|window|sha8|view|freq|harmonic[|sideband]` format from the contract |
| 3.5 | LLM draft post-scan | code | **Jadyn** | ⬜ | 3.1 | Ban `replace` always; ban `confirmed` unless status is `ANALYST_REVIEW_REQUIRED` or `INSPECTION_APPROVED`; whole words; fail = swap safe JSON line; NO retry |
| 3.6 | One eval pass of the agent surface | code | **Jadyn** | ⬜ | 3.5 | So "it works" is a number, not a vibe |

### Phase 4 — Freeze, demo, submission (16:30 → 18:00)

| # | Component | Owner | Status | Deps | Notes |
|---|---|---|---|---|---|
| 4.1 | Feature freeze; claim-correcting changes only | **All** | ⬜ | 1.7, 2.8, 3.6 | |
| 4.2 | Full offline demo run three times, timed | **Stephen** | ⬜ | 4.1 | Seven steps, ends on decision + evidence + task, never a lone spectrum |
| 4.3 | Fresh PUBLIC repo: create, push named paths only, verify tree | **Stephen** | ⬜ | 4.1 | `git ls-files` eyeball + secret scan before public. THIS repo stays private |
| 4.4 | Written submission from measured results only | **Stephen** | ⬜ | 1.7 | Drafted during the afternoon. Wired-or-cut sweep: grep the shipped code for every named tool before any claim ships |
| 4.5 | Scaffold disclosure paragraph in the submission | **Stephen** | ⬜ | 4.4 | Prep disclosed plainly per D5 |
| 4.6 | Submit, then rehearse 18:00-20:00 | **All** | ⬜ | 4.4 | **DO NOT REBOOT THE BOX.** The inference container does not come back |
| 4.7 | Pitch slides, DUE 19:30 via URL (event timeline) | **Stephen** | 🟡 | 4.4 | Skeleton PRE-BUILT Fri night (`docs/SLIDES_SKELETON.md`): Saturday afternoon only fills [MEASURED] slots + rehearsal screenshots into Google Slides. Rubric axes: technical execution, usefulness, local-first design, pitch quality. Generated art (kie.ai) allowed HERE only; the product UI stays code-drawn, zero raster assets, every value real |
| 4.8 | Pitch script rehearsed x3 timed + backup video recorded | **Stephen** | 🟡 | 4.2 | v2 DRAFTED Fri night (`docs/PITCH_SCRIPT.md`), full Sookra Pitch Arc: sourced-stat hook (EPRI 41% / ABB $125k named), agitate, stack lands in step 06 not 02, Q&A prep incl. three-move rule, demo-driver role. RECORD one full rehearsal as the hardwired backup video; if the live demo dies, cut to it without hesitation. Refusal beat = the differentiator; pick-any-window flex ONLY if 2.8 green x3 |
| 4.9 | Public repo ships with honest CI | **Stephen** | ⬜ | 4.3 | GitHub Actions running the kit-free tests (contract shape, locators, casedata file-store) so the judged repo has a real green badge; kit/mongo tests documented as box-verified. NO false-green skips: workflow runs only tests that actually execute |
| 4.10 | MongoDB side-challenge entry | **Stephen** | 🟡 | Q2 | Prepared answer WRITTEN Fri night (SUBMISSION_DRAFT, every clause greppable in store.py). On site: confirm self-managed Community qualifies + entry mechanism, then submit the paragraph |

---

## Abandon ladder (pre-decided, nobody argues at 14:00)

| Trip | Action |
|---|---|
| Model not serving by 11:15 | Ollama native `/api/chat`, immediately. No sm_121 debugging |
| Mongo unreachable by 11:15 | Staged kit artifact; if still down, file-backed fallback AND cut every MongoDB claim from the submission |
| No Stage-1 result by 13:15 | Cut localization work until detection is causal and visible |
| Physics evidence not landing by 14:00 | Ship abnormal-unlocalized with an analyst task. Never force an element call |
| Any library wants a source build | CPU equivalent. Never fight a compiler on event day |
| UI on fixtures at 15:30 | Stop polish, wire real output |
| Evaluator cannot finish all 15 | Publish the exact completed denominator, disable the rest in the UI |
| Model down at noon | The evidence JSON exists anyway. Demo narrows; it does not die |

---

## Shared Contracts

> Drift = integration bugs. Modify only after pinging every consumer. `⚠️ CONTRACT` prefix on the commit.

| Contract | Owner | Consumers | Definition |
|---|---|---|---|
| `ResultContract`, 14 fields, fixed order | Vinh | All | `bearing_witness/contract.py` (engine plan Task 9) |
| Status vocabulary | Vinh | Stephen (UI), Jadyn (post-scan) | `BLOCKED_SIGNAL, BLOCKED_BASELINE, NO_ANOMALY_DETECTED, WATCH_EARLY, ABNORMAL_LOCATION_UNCONFIRMED, ANALYST_REVIEW_REQUIRED, INSPECTION_APPROVED, INSPECTION_REJECTED` |
| Task types | Vinh | Stephen (Mongo validators) | `INSPECTION_WORK_ORDER, MEASURE_SHAFT_SPEED, VERIFY_BEARING_GEOMETRY, RECAPTURE_SIGNAL, ANALYST_REVIEW` |
| `DecisionStore` protocol | Vinh | Stephen (Mongo impl) | `record(analysis_id, decision, reason) -> HumanReview`; APPROVE/REJECT/DEFER; evidence retained on reject |
| CLI invocation | Vinh | Jadyn (tools) | `python -m bearing_witness analyze --root ... --condition ... --bearing ... --record N` prints contract JSON; `--geometry-unverified` for demo step 7; add `--cache-dir eval/feature_cache` — the cold path recomputes windows 1..N (≈15 ms/window; B3_1 w2538 ≈40 s per call). `python -m bearing_witness decide … --record N --decision APPROVE\|REJECT\|DEFER --reason "…" [--decisions-path data/decisions.json]` re-runs the analysis and applies the decision via `JsonDecisionStore` (red-only guard applies), printing the updated contract |
| Evidence locator format | Vinh | Stephen, Jadyn | `{asset_id}\|w{window}\|{sha8}\|{view}\|{freq:.2f}Hz[\|h{k}][\|sb{m:+d}]` — `\|h` absent only for unexplained residual peaks; `\|sb` never without `\|h`. Consumers parse by prefix (`w`/`h`/`sb`), 5–7 segments, never by position. |
| Traffic-light mapping | Stephen | All | green=`NO_ANOMALY_DETECTED`; yellow=`WATCH_EARLY`/`ABNORMAL_LOCATION_UNCONFIRMED`/`BLOCKED_*`; red=`ANALYST_REVIEW_REQUIRED`. State string always printed under the lamp |
| Mongo collections | Stephen | Vinh (evaluator reads), Jadyn (task tool) | `asset_configs` (immutable versions), `feature_windows` (time-series, append-only), `diagnostic_cases` (embedded task, unique analysis_key) |
| Thresholds freeze | Vinh | All | One frozen dataclass, VERSION + file sha256 embedded in evaluator output. Nobody edits after the freeze commit |

Locator regex for consumers (kept outside the table so the pipes render verbatim): `^[^|]+\|w\d+\|[0-9a-f]{8}\|(ordinary|envelope)\|\d+\.\d{2}Hz(\|h\d+)?(\|sb[+-]\d+)?$` — `|sb` never without `|h`.

### Integration protocol (proposed by Beeds, adopted 2026-08-21)

Until lanes merge, nobody imports another lane's code. Each lane builds against **placeholders shaped exactly like the contracts above** (fixtures, stub returns, transcribed dataclasses), tests its own part in isolation, and only then wires the real thing and runs integration tests at the seam.

- **Stephen** already runs this: `bw_product/contract_shape.py` is a transcription of Vinh's Task-9 contract, fixtures stand in for the engine, and task 2.8 is the wire-up + full re-gate.
- **Vinh**: engine tests run on kit CSVs alone; nothing imports `bw_product` or Jadyn's tools.
- **Jadyn**: OpenClaw tools mock the CLI contract (canned contract JSON) until the real `python -m bearing_witness analyze` exists on the box; then swap and re-run the tool tests against the live CLI.
- **Beeds**: box bring-up proves vLLM/first-token with a bare prompt, no dependence on anyone's code.
- **Integration order at wiring time:** engine CLI green alone → Stephen's adapter flip (2.8) → Jadyn's tools against live CLI → end-to-end demo walk. Each seam gets its own test pass before the next seam opens.
- A placeholder that drifts from the contract table is a contract change: ping consumers, `⚠️ CONTRACT` commit, same rule as above.

---

## Decisions

### D1 — Detect first, explain second, corroborate third, human last
The evidence hierarchy is locked: fault-agnostic trend detection against the asset's own early baseline, machine-frequency explanation, two-view corroboration, human approval before any work order. Calculated fault frequencies support localization; they are not the detector. **Locked 2026-08-19 by the team after practitioner review.**

### D2 — SciPy owns diagnosis; the model explains and acts through typed tools
Delete the LLM and the detector, evidence, database, and human decision still work. The model never writes diagnostic fields, invents part numbers, or schedules repairs. Do not tell a judge that RMS needs Blackwell. **Locked 2026-08-18.**

### D3 — vLLM opening bid, Ollama at 11:15
NemoClaw managed vLLM on the kit NVFP4 checkpoint is NVIDIA's own default for this box. The 11:15 cut to Ollama native `/api/chat` is pre-decided and shame-free. The submission names whichever actually served. **Locked 2026-08-19, research-confirmed 2026-08-20.**

### D4 — Self-managed MongoDB Community, local only, wired or cut
No Atlas, no cloud. Mongo is load-bearing (versioned geometry gates localization) or it is cut from the claims entirely. **Locked 2026-08-18.**

### D5 — Prep is starter scaffolding, disclosed plainly
Per the event page ("starter scaffolds and existing libraries are fine"), the pre-event engine prep is treated as scaffolding. The submission discloses it in plain language. Evaluator numbers quoted anywhere judge-facing come from the frozen v3 run or a fresh Saturday freeze, never from v1/v2 history. **Locked 2026-08-21 by Stephen.**

### D6 — This repo stays private; the judged artifact ships in a fresh public repo
Pre-event history and internal docs never become a judge-facing surface. The public repo is created Saturday, named paths only, secret-scanned before the flip. **Locked 2026-08-21 by Stephen.**

### D7 — The four v3 engine changes
One-sided Stage-1 z rule; harmonic floor (>= 3 harmonics) for any element call; View A ordinary-spectrum gate; measured shaft speed anchors Stage-2 labels only while every prediction uses the documented setpoint. Rationale and provenance in `docs/REVIEW_2026-08-21.md`. **Locked 2026-08-21 by Stephen.**

### D8 — The traffic light is a costume
Green is not "healthy," red is not "replace it now." The deterministic state string, evidence links, and refusal reasons always render next to the color. **Locked 2026-08-19.**

### D9 — Replay honesty everywhere
Chronological replay of real XJTU-SY run-to-failure measurements with dataset-provided setpoints. Never "live sensors," never "15 industrial machines," never a claim outside the dataset's scope. The corpus is never committed or re-hosted. **Locked 2026-08-18.**

### D10 — Manual coordination, no hooks
No `.githooks`, no `scripts/plan`, no CLI helper. Everyone types in the Notes column. Mirrors Throughline and Hometown-Pathway-Atlas. **Locked 2026-08-21 by Stephen.**

---

## Open Questions

- [x] **Q1 (Beeds):** RESOLVED 2026-08-21 night. Platform roster (authenticated dashboard): Vinh Le, Beeds K, Jadyn Worthington, Stephen Sookra (leader), 4/4 max. Beeds confirmed; he is actively coordinating the build (proposed the Integration protocol above, adopted) and has a pending collaborator invite to this repo (`beedsneeds`). Box stays Beeds' lane; 20-minute escalation rule stands. Leftover housekeeping: 2 pending platform join requests could not be accepted at 4/4.
- [ ] **Q2 (Stephen, on site):** CONFIRMED on the authenticated event page 2026-08-21: "side challenge with best use of MongoDB, stay tuned." Remaining ask on site: does self-managed Community qualify (no Atlas in our runtime), and what the side-challenge judging looks like. Claim nothing until answered.
- [x] **Q3 (Stephen, Friday night):** recon done 2026-08-21 evening. Public surfaces (BuilderBase public page, Luma, DevCuration Aug 19, GarysGuide): NO judge roster and NO rubric weights published anywhere public; submission is a working demo through the BuilderBase portal before the deadline, demo must run on the box; top 8 pitch live the same evening; prizes 1st = GB10 per team, 2nd/3rd Dell laptop. OpenShell releases: latest v0.0.111, stay pinned 0.0.106 (NemoClaw blueprint hard-pins, per LOOKUPS). RESOLVED from the authenticated event page: doors 9:00, mingle to 9:50, hacking starts 10:00, pizza 13:00, SUBMISSIONS CLOSE 18:00 (pre-eval selects top 8), SLIDES DUE 19:30 via URL, pitches 20:00 (5 min, live judging, top-3 feedback on stage), wrap 21:00. RUBRIC AXES (rules p.08): technical execution, usefulness, local-first design, pitch quality; full rubric 'shared before the event'. Rules: teams 3-4 (rosters lock at kickoff); stack minimum 2 of 3 (NemoClaw/OpenClaw/OpenShell); business/corporate use case required; Rule-01 wording verbatim: 'Starter scaffolds and existing libraries are fine, but the agent/system itself must be built during the event. Anything materially built before doors open is disqualified.'
- [ ] **Q4 (Vinh):** if a DGX Spark materializes Friday, you need the LaCie in hand that day; coordinate with Stephen.
- [x] **Q5 (Stephen, Friday night):** authenticated dashboard sweep 2026-08-21 ~21:00 ET. Resources tab EMPTY (0 codes, 0 files): the "shared before the event" rubric is not posted yet, re-check Saturday morning. No submission form exists on the dashboard pre-event (tabs are Overview / My Team / Resources / My QR Code / Help Desk only); the portal submission surface presumably appears on the day, budget time to find it before 18:00. Overview says "Check-in opens tomorrow at 11:00" alongside "Starts in 13h": treat 11:00 as the QR check-in feature time, NOT doors; arrive for 9:00 per the confirmed timeline. QR code ready on the My QR Code tab (have it on phones).

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Model never serves | D3 parachute at 11:15; demo narrows to the deterministic path (evidence JSON + UI + Mongo still work) |
| Beeds leaves | Vinh owns the box, escalation rule void, roster stays legal at 2+ |
| Evaluator incomplete at freeze | Exact completed denominator published; unevaluated bearings unselectable |
| Baseline-contaminated lead times quoted | Task 14 reconciliation gate; no lead time quoted before its verdict line is filled |
| Claiming an unwired integration | Wired-or-cut grep of shipped source before README, video, and submission text |
| Kit is a single physical copy | Corpus also exists on Vinh's machine (HF mirror pull); model exists only on the LaCie, which Stephen carries with qualified Cable 1 |
| Contract drift between four lanes | Shared Contracts table + `⚠️ CONTRACT` commits + one voice per lane |
| PLAN.md drift | Atomic status commits, 30-minute stale-lock TTL |

---

## Coordination Protocol

1. **Before starting a task:** set 🟡, add a timestamp in Notes, commit PLAN.md only, push. That is your lock.
2. **After finishing:** flip ✅, commit, push.
3. **Blocked:** ⛔ plus a one-line reason, ping the owner of the dependency.
4. **Before starting ANY task:** `git pull`, re-read this file. Overlapping 🟡 means coordinate first.
5. **Hotfixes skip the protocol.** Commit the fix, update PLAN.md after.
6. **Status commits are atomic:** `status: 2.5 🟡 wiring evidence screen`.
7. **Contract changes:** announce in Shared Contracts BEFORE committing, `⚠️ CONTRACT` prefix.
8. **Handoffs:** `→ Name` in Notes.
9. **Stale locks:** 30 minutes without a commit = claimable by anyone; replace owner + timestamp and ping.

---

_Last updated: 2026-08-21 (Friday, pre-event) by Stephen. Doors in the morning. Detect the change. Explain the spectrum. Escalate with evidence._
