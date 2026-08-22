# Demo Runbook: Bearing Witness (Saturday 2026-08-22)

Five minutes. Seven steps. The final screen is the decision, the evidence, and the
approved task. Never a lone spectrum.

## Launch

```bash
cd <repo>
.venv/bin/python -m bw_product.ui                 # full experience (FX on)
BW_FX=off .venv/bin/python -m bw_product.ui      # flat insurance mode, same loop
```

- Port: 8080 (`BW_PORT` overrides). Browser: `http://127.0.0.1:8080/`.
- Mongo down? The HUD says `MONGO OFFLINE · FILE FALLBACK` and decisions log to a
  local JSON file. If that chip is showing, CUT every MongoDB claim from the pitch
  (abandon ladder rule).
- NiceGUI itself misbehaving on the projector? Open
  `bw_product/fixtures_data/report.html` from disk. Regenerate any time with
  `.venv/bin/python -m bw_product.report`.
- Keyboard: `F` fleet · `E` evidence · `T` theme.

## The seven steps (amendment order)

1. **Fleet screen.** 15 bearings, exact denominator printed. Only evaluated
   bearings are selectable; the dead cards SAY not evaluated. Open Bearing1_3.
2. **W011 · BASELINE.** First judged window AFTER the 10-window baseline (the
   engine itself calls W1-10 `BLOCKED_BASELINE`: it refuses to judge while
   learning, say that out loud); green lamp with `NO_ANOMALY_DETECTED` and the
   "not a verified healthy label" line. Point at the replay-clip note: window k
   sees only 1..k. (Yellow moved to W060 for the same reason: it is the window
   where the engine actually says WATCH_EARLY.)
3. **Trust panel.** Documented replay speed 35.0 Hz vs measured ~34.7 Hz (the slip
   line, highlighted). Geometry provenance with the DOI. `TRUSTED_FOR_REPLAY` is
   not `TRUSTED_MEASURED`; the uncertainty windows exist because of exactly this.
4. **W155 · EXPLAIN THE SPECTRUM.** Known machine frequencies first (Stage 2
   table). Then the two views side by side: ordinary + envelope, navy dashed
   predictions with uncertainty bands, measured harmonics called out (107.03 /
   214.06 / 321.09). Optional wow beat: ENTER CORROBORATION VIEW (WebGL tunnel
   built from the real envelope bins).
5. **Red lamp.** `ANALYST_REVIEW_REQUIRED` with "inspect, never replace" spoken
   aloud. Click an evidence locator: every claim resolves to asset|window|sha|
   view|freq|harmonic.
6. **A human says yes.** Type a reason, APPROVE. The lamp flips to
   `INSPECTION_APPROVED`, the decision + timestamp render, and the work order is
   a MongoDB document (mongosh one-liner ready below if a judge wants proof).
7. **W155\* · REFUSE WITHOUT TRUST.** Same waveform, same sha on screen; geometry
   flips to unverified; detector stays abnormal; localization refuses;
   `VERIFY_BEARING_GEOMETRY` task drafted. This is the honesty beat. Say it:
   **"There is no approve button on this screen. The UI cannot approve an
   untrusted case, and neither can the database: the decision write is
   compare-and-set on the review state, so even a hand-crafted request is
   refused."** (Both halves are true and tested; the screen prints NO APPROVAL
   PATH HERE.)

Optional audio beat (separate, after step 4): two native-speed 1.28 s records,
equal loudness measured at -16.0 LUFS each. Test on the room speaker BEFORE the
demo; if unclear in the room, cut without mourning and never mention it.

Proof one-liner if asked:

```bash
mongosh --quiet bearing_witness --eval \
  'db.diagnostic_cases.find({}, {analysis_id:1, status:1, "human_review.decision":1, _id:0}).toArray()'
```

## Reset between rehearsals

```bash
mongosh --quiet bearing_witness --eval 'db.diagnostic_cases.deleteMany({})'
# restart the app; it reseeds the fixture cases on boot
```

The restart is REQUIRED, not cosmetic: a wiped store without a restart leaves
every case's decisions disabled by design (a vanished record must not make the
undecided fixture actionable). The screen says so if it happens.

## Traps (verified 2026-08-21, LOOKUPS)

- **DO NOT REBOOT THE BOX after freeze.** Nuance: the managed vLLM container has
  `--restart unless-stopped` and does come back, but the sandbox, OpenShell
  gateway, and any user-run Ollama do NOT. Recovery if it happens anyway:
  `nemoclaw <name> status` -> `start` -> `rebuild --yes`. The rule stays: don't.
- The demo does not depend on the model. If vLLM/Ollama is down, Vinh's JSON and
  this UI still run the whole loop; the demo narrows, it does not die.
- Timing target: steps 1-7 in under 4:30, leaving 30 s for the close. Rehearse
  three times, timed, after the 16:30 freeze (PLAN.md 4.2).

## Walk verification (Fri 2026-08-21 night, post-hardening)

Playwright walk against the shipped code after the 10-round adversarial gate
closed CLEAN: green (replay clip "1-8", rms in g, honest lamp copy), red (both
views, h1-h3 called out, 3 locators, reason + REJECT persisted to Mongo with
draft and evidence retained, decision chip + timestamp on re-render, HUD flips
to INSPECTION_REJECTED), refusal (VERIFY task card, NO approval controls, NO
APPROVAL PATH HERE printed). 57 pytest green. Demo state reset afterwards.
On this Mac the venv is `.venv-product/`; the runbook's `.venv/` paths are for
the box's fresh venv on Saturday.
