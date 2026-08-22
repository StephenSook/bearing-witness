# Slides Skeleton — Bearing Witness (due Sat 19:30 via URL)

Assemble in Google Slides Saturday afternoon (fast, gives a shareable URL, the
submission form wants a link). This file is the content; the afternoon only
fills [MEASURED] slots from the frozen evaluator + drops in screenshots taken
during rehearsal. Design language: paper/graphite, Archivo-style heavy caps,
mono captions, lime accents; generated art (kie.ai/Higgsfield) allowed HERE only.

Rule: every number on a slide must exist on a screen or in the frozen evaluator
output. No em-dashes. Blocklist-clean.

## 1. Title
- BEARING WITNESS (huge). Team Hermit Crab. One line: "An always-on bearing
  screening agent that runs where the data lives."
- Art slot: poster-style bearing render (generate Saturday).

## 2. The problem (usefulness) — sourced stats only
- "41% of all motor failures are bearings" (Albrecht et al., IEEE Trans. Energy
  Conversion 1986, EPRI/GE, 6,312 motors — primary, peer-reviewed).
- "$125,000: median cost of one hour of unplanned downtime" (ABB Value of
  Reliability survey 2023, n=3,215 — NAME ABB on the slide).
- "Most plants still check bearings monthly, by hand" (route-based norm; the
  blind spot IS the wedge).
- The blocker: vibration data cannot leave the plant; cloud AI cannot come in.
- Bearing image (generated art slot; this slide carries the "part smaller than
  your fist" visual since there is no physical prop).

## 3. What it is (one diagram)
- Waveform in -> SciPy diagnosis -> MongoDB evidence -> model explains + files
  typed work orders (OpenClaw) -> human approves. OpenShell cage: no egress.
- Caption: "SciPy owns diagnosis. The model explains and acts through typed
  tools. A human has to say yes."

## 4. Local-first is the product (local-first design)
- Everything on the GB10: model (kit NVFP4 via NemoClaw-managed vLLM), MongoDB
  Community, UI. Zero cloud in the runtime path.
- The denied-egress 403 screenshot from the live demo.

## 5. The evidence screen (technical execution)
- Rehearsal screenshot: W155, two views, harmonics called out.
- "107.03 Hz measured against 107.91 predicted: 0.8 percent low. That is real
  shaft slip, shown, never hidden."

## 6. The refusal (the differentiator)
- Rehearsal screenshot: refusal screen, NO APPROVAL PATH HERE visible.
- "No approve button exists for an untrusted case. Neither the UI nor the
  database will accept it (compare-and-set decision gate)."

## 7. Numbers (technical execution)
- Frozen v3 evaluator, all 15 run-to-failure bearings: 0 WRONG · 0 MISSED ·
  10 exact + 1 cage-consistent calls · 4 honest abstentions (big type, this is
  the slide's whole job).
- "When it doesn't know, it says so": abstention reasons printed verbatim.
- "MEDIAN WARNING: 99 MINUTES. BEST CASE: 42 HOURS." (Task 14 reconciled;
  footnote: 98 excluding B3_5's structural floor, stated both ways.)
- 145+ tests green across both lanes; thresholds frozen BEFORE the evaluator,
  freeze sha embedded in the output.
- Disclosure line: Friday-night scaffolding per the rules, documented; the
  engine, wiring, agent, and analysis built today on the box.

## 8. Business case (usefulness)
- The maintenance planner's morning: screening queue -> evidence -> work order
  in the system of record. Deploys as exactly what you saw: one box, Community
  MongoDB, no cloud dependency.
- [If confirmed on site] MongoDB side challenge paragraph condensed to 3 bullets.

## 9. Close
- "Detect the change. Explain the spectrum. Escalate with evidence. A human has
  to say yes."
- QR code to the public repo (generate after 4.3 creates it).
