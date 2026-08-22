# Frozen evaluator v2 — amendments over v1
Frozen 2026-08-21, AFTER diagnosing v1 (1 correct, 1 cage-consistent, 13 abstain, 0 wrong)
and BEFORE any v2 run. v1 results stand as reported. Rationale for each change is a v1
failure mode, not a peek at v2 outcomes.

## Changes (everything not listed is unchanged from frozen_thresholds.md)

1. BAND COHERENCE CHECK (the sanity check PREP_PLAN item 2 mandated, under-implemented
   in v1). v1 used the SK-winner band unconditionally; SK repeatedly elected 11-12 kHz
   noise bands with no harmonic family while 2-4 kHz carried BPFO at 5-10x the score.
   v2: score all families in BOTH the SK-winner band and fixed 2-4 kHz. Band coherence =
   max over families of (# harmonics above 3x noise). Use the more coherent band;
   tie -> fixed 2-4 kHz. Symmetric across families, applied only in Stage 3 (after the
   fault-agnostic Stage-1 gate).

2. RESOLUTION-AWARE HARMONIC WINDOWS. v1 used flat +/-1.5 Hz per harmonic — 11% of FTF
   (13.5 Hz), inflating FTF scores from noise; FTF then blocked the margin rule on 5+
   outer-race bearings. v2: half-width at harmonic k of f0 = max(0.5*bin, 0.015 * k*f0).
   Same shape as the spec's own search-tolerance rule.

3. MARGIN COMPETITOR SET. A family may act as margin runner-up only if it shows >= 1
   harmonic above 3x noise; FTF needs >= 3 (matching the cage-call bar — a family that
   cannot be called cannot block a call either). Families failing the bar are reported
   but excluded from the margin denominator.

## Predeclared expectation (falsifiable)
Outer-race bearings whose fixed-band BPFO scores in v1 were >20 with >2x raw margin
(B1_1, B1_3, B3_1, B3_5, B2_2*, B2_4*, B2_5) should now produce SUSPECTED_OUTER. Inner
bearings (B2_1, B3_3, B3_4) uncertain. Cage bearings should stay cage-consistent or
abstain. Wrong calls must stay at 0 — any wrong call in v2 is a step backwards and gets
reported as such. (*not inspected during diagnosis; expectation from class membership.)
