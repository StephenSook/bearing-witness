# Frozen evaluator v3 — amendments over v2
Frozen 2026-08-21 23:3x EDT (Friday night, D5 extension — same disclosure as milestones 1.1–1.4;
the runbook had planned this for Saturday), AFTER diagnosing v2 (10 correct, 1 cage-consistent,
3 abstain, 1 wrong) and BEFORE any v3 run. v2 results stand as reported. Every change below is
motivated by a v2 failure mode or a spec rule v1/v2 had not yet implemented — not by a peek at v3
outcomes. No v3 evaluator exists at the time of this commit (`eval/run_eval.py` is written after it).

Values live in `bearing_witness/thresholds.py` (VERSION = "v3"); `eval/results_v3.json` embeds that
file's sha256. Anything not listed is unchanged from frozen_thresholds_v2.md / v1.

Provenance at freeze: `bearing_witness/thresholds.py` sha256
`59a9d901f9cf3fe607493a348100835c62fe24a2da8f082550809b8198701dc5`, last changed in commit `65f0478`.
A results file carrying any other sha256 is not the frozen run.

## Changes

1. ONE-SIDED STAGE-1 RULE. Feature abnormal only if modified z >= +5 (fault physics: every indicator
   rises with damage). Motivated by the Stage-1 build test: a 107.9 Hz tone at 5x RMS moved energy UP
   and shape DOWN, classifying ABNORMAL under two-sided |z|. Verified on B1_3: onset unchanged at 59.

2. HARMONIC FLOOR FOR ANY ELEMENT CALL. Top family needs median >= 3 harmonics above 3x floor to be
   named. This is the bar cage already had (CAGE_MIN_HARMONICS=3), made symmetric. Motivated by
   B2_3 (cage bearing called outer on a 2-harmonic BPFO family). NOTE: PREP_PLAN's proposed "FTF
   evidence alongside BPFO => flag cage" guard is NOT adopted: in v2 data B2_3 had FTF harmonics 0 /
   score 5.3 while B1_3 (true outer) had FTF harmonics 2 / score 11.4 — that guard would have
   blocked the right call and missed the wrong one.

3. CHARACTERISTIC SIDEBANDS SCORED (spec §2 pattern table). BPFI harmonics credit ±1x shaft
   sideband PAIRS; 2xBSF harmonics credit ±FTF pairs; BPFO and FTF get none. A pair counts only when
   BOTH sides are >= 3x floor; pair amplitude adds to the family sum. Motivated by B2_1/B3_3 (inner
   bearings, BPFI top with harmonics but no margin — energy spread into shaft-spaced sidebands the
   v2 scorer ignored).

4. EXPLAINED-PEAK EXCLUSION BETWEEN FAMILIES. Per window, after choosing the top family, bins within
   the resolution-aware half-width of k*f0_top ± m*f_shaft (k=1..5, m=0..2) are zeroed before
   competitors are re-scored. Motivated by B2_5 (BPFO + 1x shaft sideband at 153.1 Hz fell inside
   the 2xBSF fundamental window at condition 2, killing the margin). This is Stage-2 discipline
   applied inside Stage 3.

5. VIEW A GATE (spec §3 decision rule 4 — never implemented in v1/v2). A SUSPECTED_* envelope call
   becomes ANALYST_REVIEW_REQUIRED only if the ordinary spectrum (<= 1 kHz, Hann) shows >= 1
   harmonic k*f0 (k=1..5) that is >= 3x the local floor (median within ±20 Hz) AND is not already
   explained as a machine component (shaft orders 1..10). Otherwise ABNORMAL_LOCATION_UNCONFIRMED with
   reason VIEW_A_NO_SUPPORT_<family>. Evaluator counts that as ABSTAIN, not wrong.

6. STAGE 2 BEFORE STAGE 3. Shaft 1x..10x labelled in the ordinary spectrum before any family is
   scored. The 1x peak found inside the setpoint's ±2% window is refined (parabolic) and used as
   the anchor for the order labels with tight ±max(1 bin, 0.5%·k·f) windows — tight because a 2%
   window at 3x shaft (105 Hz) reaches 107.1 Hz and would label the measured BPFO (107.03 Hz) as a
   shaft harmonic. Measured shaft speed is reported (shaft_hz_measured) and NEVER used for any
   bearing-family prediction (shaft_hz_used_for_prediction = setpoint).

## Unchanged (for the record)
Baseline 10 / persist 3 / >= 2 groups · demod band 2–4 kHz vs SK winner by harmonic coherence (tie ->
fixed) · f0 ±2.5% · harmonic half-width max(0.5 bin, 1.5% k f0) · family_present 9 · margin 1.5 ·
runner-up eligibility (>= 1 harmonic; FTF >= 3) · localization = median over last 5 windows <= terminal.

The evaluator runs every bearing through the product `Engine` under `xjtu_context(condition, bearing)`
(geometry and setpoint speed trusted for replay), so the trust-block paths (BLOCKED_SIGNAL,
LOCALIZATION_BLOCKED_*) are not exercised by this run; they are covered by the engine tests and the
CLI `--*-unverified` flags only.

## Predeclared expectation (falsifiable — write the actual outcome underneath after the run)
- Wrong calls must be 0. Any wrong call is a step backwards and is reported as such.
- B2_3 -> ABSTAIN (harmonic floor). B2_4 and B3_2 (correct in v2 with 2-harmonic top families) are
  EXPECTED TO BECOME ABSTAIN under the same floor — two correct calls knowingly traded for removing
  the only wrong call. B2_5 -> SUSPECTED_OUTER if exclusion works as diagnosed. B2_1/B3_3 -> improve
  margin via sidebands; may or may not clear 1.5.
- View A is the unknown: B1_3's branch, recorded from the Task 11 real-data regression run (engine at
  commit `99d5edc`, window 158): RED — status ANALYST_REVIEW_REQUIRED, refusal_reasons [],
  view_a_supports BPFO, onset window 59, BPFO harmonics 3.0, f0 107.03 Hz; i.e. the ordinary spectrum
  corroborates the envelope call on the one bearing we have looked at. Any v2-correct bearing that fails
  View A becomes ABSTAIN with reason VIEW_A_NO_SUPPORT. If that count is large, that is a finding about
  late-stage XJTU ordinary spectra, reported as such — not tuned away.
- Detection (Stage 1 onsets) unchanged from v2 except where one-sided z moves an onset; report diffs.
  Onset semantics differ from v2 (v3 cannot place an onset before window 11); no lead time is quoted
  until Task 14's reconciliation (PLAN.md 1.8).

## Actual outcome
Run 2026-08-21 23:43 EDT (2026-08-22T03:43:33Z) by `eval/run_eval.py` at thresholds sha256
`59a9d901…` (matches the provenance line above — this is the frozen run). 15/15 bearings evaluated,
no exclusions, wall 7 s (feature cache warm). Output of `eval/run_v3_output.txt`, verbatim:

```
Bearing1_1   onset=   30 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing1_2   onset=   37 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing1_3   onset=   59 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing1_4   onset=   57 status=ABNORMAL_LOCATION_UNCONFIRMED  loc=None   verdict=CORRECT_CONSISTENT reasons=CAGE_CONSISTENT_NOT_CALLED (0s)
Bearing1_5   onset=   32 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing2_1   onset=  453 status=ABNORMAL_LOCATION_UNCONFIRMED  loc=None   verdict=ABSTAIN            reasons=BEARING_PATTERN_LOCATION_UNCONFIRMED,INSUFFICIENT_HARMONICS_BPFI_2_NEED_3 (0s)
Bearing2_2   onset=   47 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing2_3   onset=  128 status=ABNORMAL_LOCATION_UNCONFIRMED  loc=None   verdict=ABSTAIN            reasons=BEARING_PATTERN_LOCATION_UNCONFIRMED,INSUFFICIENT_HARMONICS_BPFO_2_NEED_3 (0s)
Bearing2_4   onset=   31 status=ABNORMAL_LOCATION_UNCONFIRMED  loc=None   verdict=ABSTAIN            reasons=BEARING_PATTERN_LOCATION_UNCONFIRMED,INSUFFICIENT_HARMONICS_BPFO_2_NEED_3 (0s)
Bearing2_5   onset=  122 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing3_1   onset=   19 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)
Bearing3_2   onset=  169 status=ABNORMAL_LOCATION_UNCONFIRMED  loc=None   verdict=ABSTAIN            reasons=BEARING_PATTERN_LOCATION_UNCONFIRMED,INSUFFICIENT_HARMONICS_BPFI_2_NEED_3 (0s)
Bearing3_3   onset=  342 status=ANALYST_REVIEW_REQUIRED        loc=inner  verdict=CORRECT            reasons=- (0s)
Bearing3_4   onset= 1418 status=ANALYST_REVIEW_REQUIRED        loc=inner  verdict=CORRECT            reasons=- (0s)
Bearing3_5   onset=   11 status=ANALYST_REVIEW_REQUIRED        loc=outer  verdict=CORRECT            reasons=- (0s)

==== V3 SUMMARY (frozen before run, no exclusions) ====
correct                      10
cage_consistent_correct      1
abstain                      4
wrong                        0
missed                       0
other                        0
lead_min_median_max          [11, 99, 2519]
early_onset_first_30pct      7
view_a_abstains              0
thresholds sha256: 59a9d901f9cf3fe607493a348100835c62fe24a2da8f082550809b8198701dc5
```

### Predeclared expectation vs actual
- Wrong calls: **0** (predeclared: must be 0). ✓ — v2's one wrong call (B2_3 cage→outer) is gone.
- B2_3 → ABSTAIN ✓ (`INSUFFICIENT_HARMONICS_BPFO_2_NEED_3`, the harmonic floor, as predeclared).
- B2_4 and B3_2 → ABSTAIN ✓, both on the same floor (`BPFO_2_NEED_3`, `BPFI_2_NEED_3`) — the two
  v2-correct calls knowingly traded, exactly as predeclared.
- B2_5 → CORRECT outer ✓ (predeclared: SUSPECTED_OUTER if exclusion works as diagnosed).
- B2_1 / B3_3 (predeclared: sidebands may or may not clear margin): B3_3 → CORRECT inner ✓;
  B2_1 → ABSTAIN, but on the harmonic floor (`BPFI_2_NEED_3`), not on margin.
- View A: **0** abstains with `VIEW_A_NO_SUPPORT_*`. Every SUSPECTED_* call passed the ordinary-
  spectrum gate (B1_3 RED branch as recorded at E3). Not the large-count finding we allowed for.
- Net vs v2 (10 / 1 / 3 / 1 wrong): **10 correct / 1 cage-consistent / 4 abstain / 0 wrong / 0 missed**
  — same correct count, the wrong call removed, one more abstain. Correct set changed: −B2_4, −B3_2,
  +B2_5, +B3_3.

### Stage-1 onset diffs vs v2 (predeclared: "report diffs")
Onset window (record index), v2 two-sided |z| → v3 one-sided z ≥ +5 (both: baseline 1–10, persist 3).
Eight unchanged (B1_1 30, B1_3 59, B1_4 57, B1_5 32, B2_4 31, B3_1 19, B3_2 169, B3_3 342).
Seven moved, **all later**:

| bearing | v2 | v3 | files |
|---|---|---|---|
| B1_2 | 32 | 37 | 161 |
| B2_1 | 100 | 453 | 491 |
| B2_2 | 24 | 47 | 161 |
| B2_3 | 26 | 128 | 533 |
| B2_5 | 21 | 122 | 339 |
| B3_4 | 52 | 1418 | 1515 |
| B3_5 | 9 | 11 | 114 |

Reading: under two-sided |z| v2 fired on features moving *down* (shape/crest/kurtosis falling), which
the one-sided rule no longer counts as damage; v3 waits for a rise. B3_4 (52 → 1418 of 1515) and
B2_1 (100 → 453 of 491) are the largest moves and are a finding about those bearings' early
trends, reported as such — not tuned. B3_5 9 → 11 is the Codex finding confirmed: v3 structurally
cannot fire before window 11. **No lead time is quoted from either column until Task 14's
reconciliation (PLAN.md 1.8).** The `lead_min_median_max` line in the verbatim summary above is
the script's raw `files − onset`; it is not a claim.
