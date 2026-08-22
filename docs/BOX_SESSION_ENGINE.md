# Box session — engine lane (Vinh), Saturday 2026-08-22

> Paste-free context for a Claude session opened **on the GB10**. That session has no memory of the
> laptop sessions; everything it needs is here plus the repo. Read this, then `PLAN.md` rows 1.5 / 2.8,
> then `GB10-RUNBOOK.md` §3.3 and §6.3.

## Lineage

This doc's `/opt/bw/{corpus,engine,venv,state}` layout and smoke sequence are **downstream of
`GB10-RUNBOOK.md` §3.3** (workspace staging) and **§6.3** (the sandbox data-path test) — that's where
the layout and the `$K/06_PACKAGES` wheelhouse install were first specified. Read §3.3/§6.3 before this
file's "Box staging performed" section below if the two ever disagree; this file records what actually
happened on top of that spec, not a replacement for it.

`GB10-RUNBOOK.md`'s own top-of-file deviations log says 3.3 and 6.3 were **skipped** during the Aug-22
onboarding run — "no corpus or `/mnt/nvme/kit` found on the box." That was true at onboarding time; it
was staged later the same day (see below) once the kit was located on a different volume than the
runbook assumed. Anyone re-reading `GB10-RUNBOOK.md` in isolation should know §3.3/§6.3 read as
"skipped" but were completed retroactively — this file is the record of that.

## Who / what / where

- **You are working for Vinh** (engine lane: `bearing_witness/`, `tests/`, `eval/`, `pyproject.toml`).
  Stephen owns `bw_product/` + docs/pitch; Jadyn owns `bearing-witness-tools/` + OpenShell policy;
  Beeds owns the box (kit, vLLM, NemoClaw).
- **Repo on the box:** public `github.com/StephenSook/bearing-witness`, cloned/staged at `/opt/bw/engine`
  (GB10-RUNBOOK §3.3). The box holds Beeds' GitHub credentials with push rights — **a push from the box
  lands on public `main` directly.** Set `git config user.name vinhbin` and `user.email` before any commit
  so authorship is Vinh's even though the credential is Beeds'.
- **Review flow the team agreed this morning:** anything more than a one-line box fix is authored on
  Vinh's Mac → private repo (`StephenSook/NVIDIA-x-Dell`) → Stephen reviews → public → box pulls.
  From the box, commit only (a) PLAN.md status lines for 1.5 and (b) a box-specific fix if one is
  unavoidable — and **show Vinh the diff before committing, and wait for his "push".**
- **Corpus:** `/opt/bw/corpus` → `XJTU-SY_Bearing_Datasets/{35Hz12kN,37.5Hz11kN,40Hz10kN}/Bearing*_*/N.csv`.
  Minimum for today: `35Hz12kN/Bearing1_3` (158 CSVs, ~200 MB). Full corpus ≈ 11 GB, 9 216 files.
  `data/` is gitignored; the corpus is never committed. **Also symlink it at the repo-relative path**
  `/opt/bw/engine/data/XJTU-SY_Bearing_Datasets` — `tests/conftest.py`'s `requires_data`/`-m slow` skip
  check reads `data/` under the repo root, not `--root`/`/opt/bw/corpus`; the two are independent and
  neither `GB10-RUNBOOK.md` §3.3 nor the smoke sequence below mentioned this until the box run found it.
- **Venv:** `/opt/bw/venv` (`python3.12`), built offline from the kit wheelhouse
  (`pip install --no-index --find-links $K/06_PACKAGES -r requirements-product.txt`; pytest and pydantic
  are in the wheelhouse — 73 wheels). The engine itself needs only numpy, scipy, pydantic (+ pytest).
  Laptop ran Python 3.14; the box is 3.12 — the first import is the real compatibility check.
  On the Aug-22 box, `$K` resolved to `/media/dell/BWITNESS/BEARING_WITNESS_OFFLINE_KIT` (a mounted SSD,
  not `/mnt/nvme/kit`), and the wheels live one level deeper, at `$K/06_PACKAGES/python-wheels/linux-aarch64`
  with `requirements-linux-aarch64.txt` alongside — the repo's own `requirements-product.txt` is a subset
  of that file's pins and is what was actually installed.

## Box staging performed (2026-08-22, this session)

`/opt/bw` did not exist at session start — §3.3 had been skipped per `GB10-RUNBOOK.md`'s deviations log.
Staged it against the kit found on the mounted SSD, not `/mnt/nvme/kit`:

```bash
# root-owned /opt needed a human to run this once; everything after is unprivileged
sudo mkdir -p /opt/bw/{corpus,engine,state} && sudo chown -R $USER:$USER /opt/bw

K=/media/dell/BWITNESS/BEARING_WITNESS_OFFLINE_KIT
ln -sfn "$K/03_DATASETS/XJTU-SY/extracted/XJTU-SY_Bearing_Datasets" /opt/bw/corpus
ln -sfn /home/dell/bearing-witness /opt/bw/engine

python3.12 -m venv /opt/bw/venv
/opt/bw/venv/bin/pip install --no-index \
  --find-links "$K/06_PACKAGES/python-wheels/linux-aarch64" \
  -r /opt/bw/engine/requirements-product.txt

# needed separately for `-m slow` — see the Corpus bullet above
mkdir -p /home/dell/bearing-witness/data
ln -sfn /opt/bw/corpus /home/dell/bearing-witness/data/XJTU-SY_Bearing_Datasets
```

`/opt/bw/state` was left as a plain writable dir (no symlink needed — nothing pre-exists there).
Full smoke sequence passed after this; the only value that didn't match the doc verbatim was the full
`pytest -q` count (58 passed, not 56 — 4 deselected in both; two tests were added to the suite since this
doc's `56` was recorded, not a regression). Everything else — the 4 slow tests, the w155 verdict, `38
locators, 0 bad`, the geometry-unverified refusal, and the thresholds sha — matched exactly.

## Hard rules (do not negotiate these on the box)

1. **Never edit `bearing_witness/thresholds.py`.** Frozen v3; `sha256sum` must start `59a9d901`.
2. **Never re-run `eval/run_eval.py`** "to see". `eval/results_v3.json` (run `978f025` in the private
   repo; sha embedded) is the number. Wrong calls: 0 / correct 10 / cage-consistent 1 / abstain 4 /
   missed 0 over 15/15.
3. **No lead time for Bearing3_5.** Its baseline is contaminated; onset 11 is the structural floor.
   Quotable: v3, files − onset, 15/15: min 11 / median 99 / max 2519 min (median 98 without B3_5 — say
   which). No RUL claim. Source: `eval/onset_inspection.md`, TECHNICAL_REFERENCE §11.
4. **Contract changes** need a `⚠️ CONTRACT` commit and a ping to Stephen + Jadyn. None are planned today.
5. **Status commits are PLAN.md-only** (`status: 1.5 🟡 …`), never bundled with code.
6. **Do not reboot the box.** The inference container does not come back.

## Smoke sequence (run in this order; report exact output, not summaries)

```bash
cd /opt/bw/engine
ls data/XJTU-SY_Bearing_Datasets/35Hz12kN/Bearing1_3 >/dev/null || \
  ln -sfn /opt/bw/corpus data/XJTU-SY_Bearing_Datasets   # -m slow reads this repo-relative path, not --root
/opt/bw/venv/bin/python -c "import numpy, scipy, pydantic; import bearing_witness; print('import ok')"
/opt/bw/venv/bin/python -m pytest -q                       # expect: passed count may creep above 56 as tests are added; 4 deselected must hold
/opt/bw/venv/bin/python -m pytest -q -m slow               # expect: 4 passed (needs Bearing1_3 via data/XJTU-SY_Bearing_Datasets above)
/opt/bw/venv/bin/python -m bearing_witness analyze --root /opt/bw/corpus --condition 35Hz12kN \
  --bearing Bearing1_3 --record 155 --cache-dir eval/feature_cache > /tmp/w155.json; echo "exit=$?"
/opt/bw/venv/bin/python - <<'EOF'
import json,re; r=json.load(open('/tmp/w155.json'))
print(len(r),'fields |',r['status'],'|',r['suspected_location'],'| onset',r['anomaly_evidence']['onset_window'],'| task',(r['inspection_draft'] or {}).get('task_type'))
rx=re.compile(r'^[^|]+\|w\d+\|[0-9a-f]{8}\|(ordinary|envelope)\|\d+\.\d{2}Hz(\|h\d+)?(\|sb[+-]\d+)?$')
locs=[l for f in r['candidate_families'] for l in f['locators']]+((r.get('inspection_draft') or {}).get('evidence_locators') or [])+[p['locator'] for p in r['machine_components']['explained_peaks']]+[p['locator'] for p in r['ordinary_spectrum_evidence']['peaks']]+[p['locator'] for p in r['envelope_evidence']['peaks']]
bad=[l for l in locs if not rx.match(l) or ('|sb' in l and '|h' not in l)]
print(len(locs),'locators,',len(bad),'bad')
EOF
/opt/bw/venv/bin/python -m bearing_witness analyze --root /opt/bw/corpus --condition 35Hz12kN \
  --bearing Bearing1_3 --record 155 --cache-dir eval/feature_cache --geometry-unverified \
  | /opt/bw/venv/bin/python -c "import json,sys; r=json.load(sys.stdin); print(r['status'], r['refusal_reasons'], (r['inspection_draft'] or {}).get('task_type'))"
sha256sum bearing_witness/thresholds.py
```

Expected: `14 fields | ANALYST_REVIEW_REQUIRED | outer | onset 59 | task INSPECTION_WORK_ORDER`;
`38 locators, 0 bad` (count may differ by a few; **bad must be 0**);
`ABNORMAL_LOCATION_UNCONFIRMED ['LOCALIZATION_BLOCKED_GEOMETRY_UNVERIFIED'] VERIFY_BEARING_GEOMETRY`;
sha starts `59a9d901`. Cold first run without `--cache-dir` is fine too — ≈15 ms/window, so w155 ≈ 2–3 s.

If anything fails: it is almost always (a) a missing wheel → install from the wheelhouse, never the network;
(b) the corpus path → fix the symlink, not the code; (c) an aarch64 numpy/scipy ABI issue → report the exact
traceback to Vinh; do not patch the engine on the box.

## The 1.5 gate (the one ⬜ engine milestone)

PLAN.md 1.5: *"13:15 gate: one real Bearing1_3 window through engine → Mongo → UI"*, Vinh + Stephen.
Stephen already ran the full seam on his Mac Friday (PLAN.md 2.8 notes: real CLI → `engine_adapter` →
Mongo → UI, W155 = ANALYST_REVIEW_REQUIRED/outer, f0 107.03125, score 30.10). The gate is the same thing
**on the box**.

1. `git pull` in `/opt/bw/engine`; `git config user.name vinhbin && git config user.email <Vinh's email>`.
2. Claim: PLAN.md row 1.5 → 🟡, Notes `HH:MM Vinh → Stephen — box gate`; commit
   `status: 1.5 🟡 box gate — one real Bearing1_3 window engine → Mongo → UI`; **show Vinh; push on his word.**
3. Sit with Stephen: engine (smoke above) → his adapter → Mongo → UI shows W155 as ANALYST_REVIEW_REQUIRED /
   outer with the locators. Plain screens are fine.
4. Flip: 1.5 → ✅ with what was seen (`w155 … on the box`), `→ Stephen (2.8)`; commit, show, push on his word.
5. If the gate is missed (abandon ladder): cut localization polish; Stage-1 visible in the UI first; do
   not fake it forward.

After 1.5: **support mode** — answer Jadyn's CLI/locator questions (consumers parse locators by prefix,
5–7 segments), pair with Stephen if 2.8 slips past 15:30, claim-correcting edits only after 16:30,
submissions close 18:00.

## Where the facts live (when a judge or teammate asks)

- Engine rules, constants, status tree, Q&A: `TECHNICAL_REFERENCE.md` §9, §11, **§12, §13**.
- Hand-off API for UI/tools: top of `PREP_PLAN.md` ("Engine hand-off (Aug 21)").
- Contract / CLI / locator / status vocabulary: `PLAN.md` Shared Contracts (incl. the `decide` subcommand).
- Freeze + results: `eval/frozen_thresholds_v3.md`, `eval/results_v3.json`, `eval/run_v3_output.txt`.
- Onset semantics + verdicts: `eval/onset_inspection.md`.
- Decisions D1–D10 and the abandon ladder: `PLAN.md`.
