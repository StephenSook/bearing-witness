# Backup demo video

`backup_demo_walkthrough.webm` — silent screen capture of the live product loop,
recorded on the GB10 against the real UI (`bw_product.ui`), real MongoDB, and
the frozen v3 evaluator fixtures. This is PLAN.md 4.8's "hardwired backup
video": if the live demo dies during the pitch, cut to this without
hesitation. It has no narration — it's proof the loop works, not a substitute
for the spoken pitch script (`docs/PITCH_SCRIPT.md`).

Walk (41s, 1600x900): fleet screen (15/15 evaluated) -> W011 baseline
(green) -> W060 (yellow) -> W155 explain-the-spectrum (red, two views,
evidence locators, drafted inspection task) -> a human types a reason and
APPROVEs (decision + timestamp persist) -> W155\* refusal (unverified
geometry, no approve button anywhere, "NO APPROVAL PATH HERE"). Recorded with
`BW_FX=off` (the flat/insurance build DEMO_RUNBOOK.md already documents as
"same loop") for a deterministic, animation-free capture.

Format is WebM/VP8, not MP4/H.264: the only ffmpeg on this box is the minimal
one Playwright bundles for its own video recording, and it has no H.264
encoder built in (`--disable-everything`, only libvpx enabled) and installing
a full ffmpeg needs `sudo`, which isn't available non-interactively here.
WebM plays natively in Chrome/Firefox/Edge and in VLC on every OS, so this
wasn't worth blocking on — flag it if a judge's machine genuinely can't play
it.

## Verified, not just recorded

`record_demo.py` is both the recorder and the verification harness: every
stage asserts the exact DOM text a judge needs to see (status strings, the
evidence locator, the drafted task, the recorded decision + reason +
timestamp, the refusal's "no approval path" line, that no APPROVE button
exists on the refusal case) *before* moving to the next stage. A failing
assertion aborts the run rather than shipping a video of a broken screen. The
video file itself was also full-decode-scanned (`ffmpeg -f webm -y /dev/null`)
to catch any encoding corruption/truncation independent of the app checks.

## Regenerating it

```bash
# one-time: playwright + chromium in the product venv
/opt/bw/venv/bin/pip install playwright
/opt/bw/venv/bin/python -m playwright install chromium

# reset to clean fixtures, then bring the UI up in flat mode on 8091
# (see docs/BOX_SESSION_PRODUCT.md's bring-up order for the Mongo/corpus env vars)
BW_FX=off BW_PORT=8091 /opt/bw/venv/bin/python -m bw_product.ui &

/opt/bw/venv/bin/python docs/demo/record_demo.py
```

The script leaves the W155 case APPROVED when it finishes (that's the point —
it's exercising the real decision write). Reset before a live demo per
`docs/DEMO_RUNBOOK.md`'s reset procedure: drop `diagnostic_cases`, restart the
UI to reseed.
