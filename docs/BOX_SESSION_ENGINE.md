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

## OpenClaw plugin / sandbox track (bearing-witness-tools) — Aug 22, continued

> **Downstream of `GB10-RUNBOOK.md` §04** (Install NemoClaw) **and §6.3** (Prove the sandbox
> sees what it should) — the same relationship this file's engine-lane section above has to
> §3.3/§6.3. Scope here is `bearing-witness-tools/` + OpenShell/NemoClaw sandbox policy —
> **Jadyn's and Beeds' area**, not the Vinh engine-lane content above. Recorded in this file for
> continuity between the two tracks, since both live on the same box session.

### What was found

- The plugin install steps (`npm run build`, `openclaw plugins install --link`, `enable`) target
  the **host's** OpenClaw instance (`~/.openclaw/openclaw.json`). The `hack-agent` sandbox that
  `nemoclaw hack-agent agent --agent main` actually talks to is a separate Docker container
  (`openshell-default--hack-agent-*`) with its own isolated config at
  `/sandbox/.openclaw/openclaw.json` **inside** the container, and its own `plugins.allow` hard
  allowlist. Installing on the host never reaches it.
- `GB10-RUNBOOK.md` §6.3's own `openclaw sandbox explain --agent main --json` step must be run
  **inside** the sandbox (`nemoclaw hack-agent connect` first) — running it from the host queries
  an unrelated agent/profile and gives a misleading result.

### Fixes applied (inside the `hack-agent` container, `/sandbox/.openclaw`)

1. Copied the built plugin (`dist/`, `openclaw.plugin.json`, `package.json`, `node_modules` for
   the `typebox` runtime dep) into `/sandbox/plugins/bearing-witness-tools`.
2. `openclaw plugins install --link /sandbox/plugins/bearing-witness-tools` +
   `openclaw plugins enable bearing-witness-tools`, run as the `sandbox` user **inside** the
   container — its own `openclaw` binary, its own config, not the host CLI.
3. `openclaw config set plugins.allow '["nemoclaw","bearing-witness-tools"]' --strict-json` —
   appended; `nemoclaw` was not removed.
4. Copied `src/fixtures/*.json` into `dist/fixtures/` — `tsc` does not copy static JSON fixtures
   on `npm run build`, and `cli.ts`'s `FIXTURES_DIR = join(__dirname, "fixtures")` resolves to
   `dist/fixtures`, which is otherwise never created. **This is a real gap in the plugin's own
   build, present on the host too** — worth a `postbuild` copy step, not something specific to
   the container.
5. Gateway restart was initially rejected (`GATEWAY_UNSAFE_CONFIG_PATH` →
   `invalid-restart-posture`): the OpenClaw CLI's own config writer left `/sandbox/.openclaw` at
   `0700` and `openclaw.json` at `0600`, but NemoClaw's tamper-detection guard
   (`openclaw-config-guard.py`) requires exactly `2770`/`0660` `sandbox:sandbox` (matching the
   sibling `.config-hash`) to accept a restart as legitimate "mutable posture" rather than
   tampering. Fixed via `chmod 2770 .openclaw && chmod 660 openclaw.json` — permissions only, no
   content touched.
6. Restarted via `nemoclaw hack-agent gateway restart` (the host-gated path) — the in-container
   restart-request channel is root-only by design
   (`/run/nemoclaw/gateway-control`, comment in `nemoclaw-start`: "sandbox processes cannot
   submit or alter them"). Never send a signal/kill into the container directly for this.
7. Step 5 (`openclaw sandbox explain`) was reporting OpenClaw's own internal exec-sandbox tool
   profile (default "coding" profile, unrelated to the plugin's tools) with `source: "default"`.
   Set the intended surface via `openclaw config patch`:
   ```json5
   { tools: { sandbox: { tools: {
     allow: ["diagnose_bearing","check_blockers","get_evidence","submit_decision","test_without_geometry","replay_timeline"],
     deny: ["group:fs","group:web","group:runtime"]
   } } } }
   ```
   No restart needed (hot-reloadable). `sandbox explain` now shows the six tools under `allow`,
   the expanded group members (`read`/`write`/`edit`/`apply_patch`,
   `web_search`/`web_fetch`/`x_search`, `exec`/`process`/`code_execution`) under `deny`, both
   sourced `"global"` — matches §6.3's expectation.

### Root cause of task 3.2 (found and proven, Aug 22 ~17:00) — `confirmGate.js` never loads

Step 3 (`diagnose_bearing`) returns `ANALYST_REVIEW_REQUIRED` cleanly. Step 4 (`submit_decision`)
does **not** pause — it writes `INSPECTION_APPROVED` immediately, every time, regardless of
invocation mode. An earlier pass through this file guessed this was a one-shot-CLI /
no-approval-channel gap (OpenClaw's `requireApproval` only truly blocks when it can route to a
live human). **That theory was wrong** — proven wrong by instrumenting the actual running code:

- `package.json` declares two plugin entry points: `"openclaw": {"extensions":
  ["./dist/index.js", "./dist/confirmGate.js"]}`.
- `openclaw plugins inspect bearing-witness-tools --runtime --json` (and `plugins list --json`)
  both report `"source": ".../dist/index.js"` only — `confirmGate.js` is never named as a loaded
  module anywhere in the runtime record. `"hookCount": 0`, `"typedHooks": []` — nothing is
  registered.
- The `trustedToolPolicies`/`tools` array that *does* show up under `inspect`'s `"contracts"` key
  is a **static echo of `openclaw.plugin.json`'s own `contracts` field** (word-for-word), not
  proof of live registration — that manifest file self-declares what the plugin *claims* to
  provide, and `doctor`/`inspect` surface it whether or not the code backing it actually ran.
  This is what made the wiring look correct in steps 1–2 of the original smoke test.
- Definitive proof: added an unconditional `appendFileSync` trace at the top of `confirmGate.js`
  (fires the instant the ES module is evaluated, before any function call) and reinstalled +
  restarted the gateway. The trace file was **never created** — the module is never imported.
  Reverted this instrumentation after confirming; `confirmGate.js` in the repo is unchanged.

**Fix needed (Jadyn's file, needs review per this doc's process):** `./dist/confirmGate.js` as a
second `package.json` `openclaw.extensions` entry does not get loaded by this OpenClaw version's
plugin loader for a path-installed (`--link`) plugin — only the first listed entry loads. The
robust fix is to stop relying on a second entry point: merge the trusted-tool-policy registration
into `index.ts`'s single `register`/`defineToolPlugin` flow (import `confirmGate.ts`'s
`api.registerTrustedToolPolicy(...)` call and invoke it from the same entry that registers the
six tools), then drop `./dist/confirmGate.js` from `package.json`'s `extensions` array. Until
that lands, task 3.2 does not function on this build — no invocation mode (CLI, dashboard,
channel) will trigger it, since the code that would ask for approval never runs.

### Workflow: testing interactively via the dashboard

Even after the fix above lands, the `nemoclaw hack-agent agent -m` one-shot CLI call still won't
be able to answer a real approval prompt (it's channel-less, so `requireApproval` has nowhere to
route the question to a human) — use the sandbox's own web dashboard instead, where a human is
present to click Allow/Deny:

```bash
nemoclaw hack-agent dashboard-url
# -> http://127.0.0.1:18790/#token=<token>   (treat the URL like a password)
```

Open that URL in a browser (SSH-tunnel it first if not on the box:
`ssh -L 18790:127.0.0.1:18790 user@gb10`), start a chat with agent `main`, and ask it to call
`submit_decision` the same way step 4 does. A working confirm-before-mutate gate should show an
approval card in the UI and block until answered.

### Note: `openclaw config set`/`patch` resets the mutable-posture file modes every time

Each CLI config write (not just the first) leaves `/sandbox/.openclaw` at `0700` and
`openclaw.json` at `0600` instead of NemoClaw's required `2770`/`0660`. Hit this twice — once
after the original `plugins.allow` edit, again after the step-5 `tools.sandbox` patch. Before any
`nemoclaw hack-agent gateway restart`, re-check/fix: `chmod 2770 /sandbox/.openclaw && chmod 660
/sandbox/.openclaw/openclaw.json`, or the restart fails with `GATEWAY_UNSAFE_CONFIG_PATH` /
`invalid-restart-posture`.

**Not port 8080.** `127.0.0.1:8080` is OpenShell's own internal control-plane gateway (JSON-RPC/WS
orchestration API used by `nemoclaw`/`openshell` themselves to manage sandboxes — every page
route 404s, it is not a browsable UI). `18789` is the **host's** general-purpose OpenClaw gateway
(unrelated to this plugin, since it was never installed there for the sandbox to use). `18790` is
the one that matters here — `hack-agent`'s own gateway, forwarded to the host by OpenShell
(`openshell forward list` shows it), and it's where agent `main` — with the bearing-witness
plugin now actually loaded — really lives.

### Still untouched

`/opt/bw` corpus/engine mount into the sandbox (`GB10-RUNBOOK.md` §3.3/§6.3 data-path test) —
separate, deeper issue; §3.3 says sandbox mounts lock at `nemoclaw onboard` time, and `/opt/bw`
didn't exist yet when this box's onboarding ran (see "Box staging performed" above), so the
running container was never given that mount. Fixing it means recreating the sandbox, which is
riskier than anything above and wasn't attempted here.

---

## Where the facts live (when a judge or teammate asks)

- Engine rules, constants, status tree, Q&A: `TECHNICAL_REFERENCE.md` §9, §11, **§12, §13**.
- Hand-off API for UI/tools: top of `PREP_PLAN.md` ("Engine hand-off (Aug 21)").
- Contract / CLI / locator / status vocabulary: `PLAN.md` Shared Contracts (incl. the `decide` subcommand).
- Freeze + results: `eval/frozen_thresholds_v3.md`, `eval/results_v3.json`, `eval/run_v3_output.txt`.
- Onset semantics + verdicts: `eval/onset_inspection.md`.
- Decisions D1–D10 and the abandon ladder: `PLAN.md`.
- OpenClaw plugin / NemoClaw sandbox state (bearing-witness-tools, confirm-gate, dashboard
  workflow): "OpenClaw plugin / sandbox track" section above.
