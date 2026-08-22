# Box session, product lane (Stephen): what the box must do, and what "working" looks like

Companion to `docs/BOX_SESSION_ENGINE.md` (Vinh's engine smoke). That doc proves the
engine answers; this doc proves the PRODUCT runs: Mongo up, UI up, the full loop
(engine, adapter, Mongo, UI, human decision) live on the GB10, watch mode on. Run the
engine smoke first, then this, in order. Report exact output, not summaries.

## Layout (same as the engine doc)

- Repo: `/opt/bw/engine` (clone of public `github.com/StephenSook/bearing-witness`;
  per GB10-RUNBOOK §3.3 this is a SYMLINK into the kit, staged before any sandbox)
- Venv: `/opt/bw/venv` (python3.12, offline install from the kit wheelhouse:
  `pip install --no-index --find-links $K/06_PACKAGES -r requirements-product.txt`)
- Corpus: `/opt/bw/corpus` (minimum `35Hz12kN/Bearing1_3`, 158 CSVs). Mounted
  READ-ONLY by design (RUNBOOK §3.3): locators carry a sha8 of the source, so
  nothing may be able to rewrite a measurement. Never "fix" a corpus problem by
  making it writable; fix the symlink.
- State: `/opt/bw/state` is the one writable product path (RUNBOOK §3.3);
  file-fallback decision logs belong there, never in the corpus or the repo.
- MongoDB: Community 8.0 ARM64, local only, no Atlas, no auth for the demo.
  NOTE: mongod is NOT covered by GB10-RUNBOOK (that doc is the NemoClaw/Ollama
  stack). Confirm the mongod ARM64 binary exists on the box or the kit BEFORE
  the gate; if it is missing, it needs the hotspot (Ollama-style) to fetch.
- Model actually serving on the box (RUNBOOK header): `qwen3.8:27b-q4_K_M` via
  Ollama on 127.0.0.1:11434, NemoClaw auth proxy on 11435. Say THIS model name
  to judges; the deck and pitch already match it.

Environment the product reads (defaults in parentheses; set only if paths differ):

| Var | Default | Meaning |
|---|---|---|
| `MONGODB_URI` | `mongodb://127.0.0.1:27017/bearing_witness` | Mongo connection |
| `BW_ENGINE_ROOT` | repo `data/` | corpus root; on the box: `/opt/bw/corpus` (the symlink at `/opt/bw/corpus` already resolves straight to `XJTU-SY_Bearing_Datasets/` — do not append that segment again) |
| `BW_PORT` | `8080` | UI port; the OpenShell gateway also binds 8080 on this box, so pick a free port (e.g. `8091`) if it's taken |

## Bring-up order

```bash
# 1. Mongo up (however Beeds installed it; then verify)
/opt/bw/venv/bin/python -c "from pymongo import MongoClient; \
  print(MongoClient('mongodb://127.0.0.1:27017', serverSelectionTimeoutMS=2000).admin.command('ping'))"
# expect: {'ok': 1.0}

# 2. Full suite (mongod up makes the Mongo-gated tests RUN, not skip)
cd /opt/bw/engine
/opt/bw/venv/bin/python -m pytest tests/ bw_product/tests/ -q -rs
# expect: 147 passed. With the corpus mounted the 4 corpus skips disappear too;
# any skip line PRINTS its reason, read them. Under CI=1 a down mongod is a hard
# error by design (false-green guard), locally it would just skip.

# 3. E2E through the real engine (corpus + mongod both needed)
/opt/bw/venv/bin/python -m pytest bw_product/tests/test_e2e_real_engine.py -q
# expect: 3 passed (W155 through adapter to Mongo projection). NOTE: these are
# NOT marked `slow` (that marker is only on tests/test_engine_realdata.py in the
# engine lane); they're gated by needs_corpus/needs_mongod skipif and already ran
# as part of step 2's full suite once corpus+mongod are both up.

# 4. UI up
BW_ENGINE_ROOT=/opt/bw/corpus BW_PORT=8091 \
  /opt/bw/venv/bin/python -m bw_product.ui
# then open http://127.0.0.1:8091 (8080 is taken by the OpenShell gateway on this box)
```

## What must work (walk this list in the UI, in order)

1. **HUD says MONGO, honestly.** Backend chip shows the Mongo backend. If it says
   file/degraded, Mongo is down or seeding failed; fix that before anything else.
   The HUD never lies: degraded is labeled degraded.
2. **Fleet screen.** 15 evaluator-verdict cards from `eval/results_v3.json`. Zero
   wrong, zero missed. This is the opening demo screen.
3. **Green case (W011).** Green lamp, NO_PERSISTENT_CHANGE wording. No approve
   button anywhere on a non-decidable case.
4. **Yellow case (W060).** Early-watch state.
5. **Red case (W155).** ANALYST_REVIEW_REQUIRED, suspected outer, envelope
   f0 107.03 Hz with harmonics, slip line ("1.2% low: slip" style), locators on
   every claim, INSPECTION_WORK_ORDER draft, APPROVE/REJECT/DEFER visible.
6. **Decision gates.** DEFER with a reason: case stays revisitable. APPROVE with a
   reason: final. Re-open the case: decision immutable, no second write. Empty
   reason: refused. (CAS in Mongo enforces this even against a rigged client.)
7. **Refusal case (W155 unverified geometry).** ABNORMAL_LOCATION_UNCONFIRMED,
   LOCALIZATION_BLOCKED_GEOMETRY_UNVERIFIED, task VERIFY_BEARING_GEOMETRY, and
   NO approve button. The refusal is the feature.
8. **Live analysis row.** Pick any record 1..158, analyze: a real engine
   subprocess, result lands in Mongo, dialog shows the STORED document.
9. **START WATCH.** Status ticks `WATCHING · W0NN · K ANALYZED · 0 ERR`. Cases
   land on their own. STOP mid-tick shows honest `STOPPING · FINISHING W0NN`.
10. **Kill/restart (the MongoDB side-challenge beat).** Kill the UI process while
    watch is counting. Restart, START WATCH again: status shows
    `RESUMED PAST N ON RECORD` and the counter continues from the next
    unanalyzed window, not from 1. The agent's memory is the database.

## Expected failure modes (all honest, none fatal)

- Corpus missing or symlink dangling: watch/live rows record per-window errors and
  continue; fleet and fixture cases still render. Fix the path, not the code.
- Mongod down at boot: UI falls back to file backend, LABELED degraded, decisions
  go to the local decision log. Demo needs Mongo up; this mode is the honest
  fallback, not the demo.
- Engine CLI absent: live row and watch are gated off (engine_available probe,
  30 s retry). They appear on their own once the engine answers.

## Hard rules (product lane)

1. Mongo is LOCAL ONLY. Nothing leaves the box; that is the product claim.
2. Never hand-edit `diagnostic_cases` in mongosh during or after rehearsal; the
   validators and the immutability story are judge-facing claims.
3. To reset for a fresh demo run: drop the database, restart the UI (it recreates
   collections, validators, and seeds fixtures on startup). Full sequence in
   `docs/DEMO_RUNBOOK.md`.
4. Status commits from the box are PLAN.md-only, show Stephen the diff first.
5. Do not reboot the box (inference container does not come back).

## The 12:30 gate (PLAN.md 1.5, with Vinh)

Engine smoke (Vinh's doc) then steps 1, 5, 8 above on the box = gate passed:
one real Bearing1_3 window, engine to Mongo to UI, on the GB10. Flip 1.5 in
PLAN.md per the engine doc's protocol. Then rehearse 9 and 10 for the pitch.
