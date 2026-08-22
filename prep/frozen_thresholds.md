# Frozen evaluator thresholds — Bearing Witness prep
Frozen 2026-08-21, BEFORE the 15-bearing evaluator run. Per PREP_PLAN §5 and spec §10,
these may not be tuned after seeing results. If they prove wrong, we report that they
were wrong — we do not carve.

## Stage 1 — detection (fault-agnostic)
- Features: bw_dsp.features (rms, p2p, crest, excess kurtosis, 4 fixed band energies, envelope energy)
- Baseline: first 10 chronological windows of the same bearing+condition; median + MAD
- Feature abnormal: |modified z| >= 5  (z = 0.6745·(x−med)/MAD)
- Groups: energy{rms,p2p} · shape{crest,kurt} · hf_band{4 bands} · envelope{env_energy}
- Window ABNORMAL: >= 2 groups abnormal (any member triggers its group)
- Persistent: 3 consecutive ABNORMAL windows; onset = first window of first such run
- WATCH_EARLY: only hf_band and/or envelope groups moved
- Replay discipline: window k may use only windows 1..k. Never lifecycle-normalized.

## Stage 3 — localization (envelope family scoring, applied only after Stage-1 onset)
- Demodulation band: kurtogram winner per window; fallback fixed 2–4 kHz (relative to
  condition; band frozen as absolute Hz since resonances are structural)
- Family fundamental search: f0 in ±2.5% of prediction (per-condition shaft speed setpoint)
- Family score: sum of envelope-spectrum amplitude at {f0, 2f0, 3f0}, each ±1.5 Hz,
  divided by median amplitude in 5–500 Hz (SNR-like, unitless)
- Family present: score >= 9 (≈ three harmonics each 3× the noise floor)
- Clear margin: top family score >= 1.5 × runner-up, else BEARING_PATTERN_LOCATION_UNCONFIRMED
- Cage (FTF) may NEVER be called from a single peak: requires >= 3 FTF harmonics AND is
  reported only as "cage-consistent", never as a confirmed element, per spec §2
- BSF searched at 2×BSF primary. BPFI supported by shaft-speed sidebands when present
  (sidebands score as bonus, not gate)
- Localization window: median family scores over the last 5 windows ending at the
  evaluation point (not the single terminal record)

## Measured outcomes (defined before running)
- Warning lead time: (terminal window index − Stage-1 onset index) minutes; terminal =
  last file of the bearing
- Abstention: bearing where Stage-1 fired but no family met score+margin → counted with
  reason code, NOT as wrong
- Wrong call: named element not in the documented failure mode for that bearing
- Correct call: named element ∈ documented elements (multi-element bearings: any documented
  element counts, noted as partial when the dominant one is missed)
- False alarm: Stage-1 persistent onset inside the first 30% of life on a bearing whose
  documented failure appears only at end of life — reported as count, judged per-bearing
- No exclusions: all 15 bearings run; short-life bearings (< 13 windows: baseline 10 +
  persistence 3) reported as BLOCKED_BASELINE, counted in abstentions
