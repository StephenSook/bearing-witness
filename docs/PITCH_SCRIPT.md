# Pitch Script v2 — Bearing Witness (5:00, top-8 live, Sat 2026-08-22 20:00)

Structure: the Sookra Pitch Arc, tuned to the OFFICIAL WEIGHTED RUBRIC
(dashboard-verified Sat 11:12): **Local-first + always-on 30%** ("the agent acts
on its own over time") · **Business value 30%** ("something a company would
actually pay for") · **Demo + pitch 30%** · Technical execution 10% ("doesn't
break"). Consequence: watch mode is a HEADLINE beat, payback math gets air,
deep tech stays compressed. Reliability IS the tech score; don't lecture it.
[MEASURED] slots fill ONLY from the frozen evaluator or the shipped suite.
Roles are per beat (table below): all four builders speak, Stephen opens and
closes, and BEEDS IS DEMO DRIVER THROUGHOUT (his box, his muscle memory, incl.
the kill/restart commands). The driver never narrates while typing. Lock the
assignments at the 16:30 freeze and rehearse the handoffs; a handoff is one
step forward and the first word, never "and now X will...". Judge routing:
identify the decision-weight judge during the day and make sure they see the
live run.

## Who says what (STAGE deck numbering, 10 slides; slide flips match the spoken order)

| Slides / beat | Voice | Why them |
|---|---|---|
| S1 · Title (hook opens on it; flip on "forty-one percent") | **Stephen** | leader opens; practitioner story is his |
| S2 · Problem (41% + once a month by hand) | **Stephen** | hook lands while its numbers are on screen |
| S3 · Blind spot ($125k + not allowed to leave; flip entering "A bearing can go from healthy to destroyed...") | **Stephen** | agitate beat, now with its own slide |
| S4 · SOLUTION reveal (dark: "lives entirely on this box" + "Nothing leaves the room.") | **Vinh** | the solution sentence gets its own slide; flip as he starts speaking |
| S5 · How it works (physics/paperwork/yes + four steps) | **Vinh** | the four steps ARE the engine, his lane |
| S6 · Always-on + switch to app | **Beeds** | his box; he speaks the ten seconds and the bridge line, executes the switch himself, then goes quiet as the demo narration starts |
| Demo steps 1, 2, 5 | **Stephen** | fleet + watch start, baseline, decision gate |
| Demo step 3 (W155 two views) | **Vinh** | the 107.03 Hz + slip beat is evaluator truth |
| Demo step 4 (audio, if verified) | **Vinh** | same evidence, second sense |
| Demo step 6 (THE REFUSAL) | **Jadyn** | his gate: the model cannot cite what is not in evidence; then UI and DB refuse above it |
| Demo step 7 (pick a window) | **Stephen** | live product path |
| Demo steps 8-9 (watch callback, kill/restart) | **Stephen** | the Mongo story is his lane; Beeds executes the kill and restart |
| S7 · Pays for the box | **Stephen** | business value, 30% axis |
| S8 · Receipts (0/0 · 99 min · 42 h) | **Vinh** | the person who built the evaluator states its numbers |
| S9 · Team + tech | **Beeds** (stack sentence), then **Stephen** (MongoDB side-challenge sentence) | Beeds built the box; Mongo is Stephen's |
| S10 · Close + mantra | **Stephen** | leader asks for the win |

Q&A routing after: engine and evaluator numbers to Vinh, box/serving/stack to
Beeds, agent tools and sandbox policy to Jadyn, business and product and
MongoDB to Stephen. Whoever is asked, answer or route in ONE sentence.

## 01 · HOOK (0:00-0:30) — named moment + sourced stat + structural tension

No prop. At "a part smaller than your fist," gesture at the bearing on screen
(the fleet screen's card grid or the title slide's bearing image carries the
visual). Do not introduce the team. Do not say "today I'll show you."

> "This month we sat down with a vibration practitioner who has spent decades
> walking plant floors. He told us how bearing failures actually get found:
> someone hears it, smells it, or the line stops. In the largest utility motor
> reliability study ever done, six thousand three hundred motors, forty-one
> percent of ALL failures came down to this:" [gesture at the screen] "a part
> smaller than your fist. And most plants still check it once a month, by hand,
> on a route."

(41% = Albrecht et al., IEEE Trans. Energy Conversion, 1986, EPRI/GE, 6,312
motors. Primary and peer-reviewed; survives a judge looking it up.)

## 02 · PROBLEM + AGITATE (0:30-1:05) — stay in the pain

> "A bearing can go from healthy to destroyed inside the gap between two of
> those monthly readings. ABB's own reliability survey of three thousand plant
> decision-makers puts the median cost of unplanned downtime at a hundred and
> twenty-five thousand dollars an hour; two-thirds of plants eat at least one
> a month. So why isn't continuous monitoring everywhere? Because the fix
> everyone sells is a cloud subscription, and the plants that need it most are
> exactly the ones whose vibration data is not allowed to leave the building.
> The people who fail here aren't lazy. They're locked out."

(Name ABB as the source out loud: pre-empts the challenge.)

## 03 · SOLUTION (1:05-1:20) — one sentence, no stack

> "Bearing Witness is an always-on screening agent that lives entirely on this
> Dell Pro Max: it watches every window of vibration, explains what it sees with
> evidence a human can check, and files the work order. Nothing leaves the room."

## 04 · DEMO (1:20-3:20) — the headline runs live; narrate outcomes

Verbal bridge (BEEDS, from slide 4, as he switches to the app himself):
"Let me show you this live, right now, on real run-to-failure data."

1. Fleet: "All fifteen bearings through the frozen evaluator; every card is a
   real verdict. Zero wrong. Zero missed." THEN press START WATCH and say:
   "And I'm turning the agent loose right now. While we talk, it will keep
   analyzing this bearing's life on its own. Watch the counter." (30% criterion,
   verbatim: the agent acts on its own over time. Let it run through the pitch.)
2. W011 baseline: green lamp. "It refuses to call this healthy; it says no
   persistent change. Words matter here."
3. W155: two views. PAUSE HERE (the killer feature; let judges absorb):
   > "The envelope spectrum shows 107.03 hertz and its harmonics: the outer-race
   > signature of THIS bearing's geometry. Prediction said 107.9. Measurement
   > runs 0.8 percent low. That's real shaft slip; the app shows it instead of
   > hiding it."
4. Audio beat (if room-speaker-verified): "Same bearing, first hour vs last
   hour. You can hear what the spectrum shows."
5. Decision: reason typed, APPROVE. "The work order is a MongoDB document with
   the evidence pinned to it. The agent drafts. A human says yes."
6. THE REFUSAL BEAT (slow down; this is the shouldn't-be-possible moment):
   > "Now watch what it will NOT do. Same waveform, but the bearing's geometry
   > is unverified. No location call. And look: no approve button. The UI cannot
   > approve an untrusted case, and neither can the database; the decision write
   > is compare-and-set on the review state. An agent you can trust is one that
   > refuses when it should."
7. Only if 2.8 ran green in all three rehearsals: "Pick a window. Any of the
   158." Analyze it live. "That analysis is not a recording; nothing here is."
8. THE WATCH CALLBACK (do not skip; it closes the 30% always-on loop): point at
   the status line running since step 1. "While we talked, it analyzed [N] more
   windows by itself, wrote every case to the database, and refused the ones it
   couldn't prove. Nobody touched it. That is what always-on means."
9. KILL/RESTART BEAT (optional, ONLY if the MongoDB judge is at the table AND
   it ran clean in all three rehearsals): kill the app mid-count, restart it,
   point at "RESUMED PAST [N] ON RECORD". "I just killed the agent. It came
   back and resumed where the DATABASE says it left off, not from zero. Its
   memory is MongoDB, not the process. A JSON file cannot do that." (Their
   slide's three criteria in one screen; their kicker answered verbatim.)

## 05 · IMPACT (3:20-3:50) — the After + the numbers

> "Who pays for this? Every plant that already refuses cloud monitoring: legal,
> pharma, defense, food, any OT-isolated floor. The maintenance planner's
> morning changes: instead of a monthly route and a guess, a screening queue
> with evidence, and a work order already in the system of record. At ABB's
> median rate of a hundred twenty-five thousand dollars an hour, catching ONE
> failure inside that monthly blind spot pays for this box the first time it
> happens. The numbers, from an
> evaluation whose thresholds were frozen and committed BEFORE it ran: all
> fifteen run-to-failure bearings, onset detected on every single one, eleven
> element calls, ten exact plus one cage-consistent, ZERO wrong, and four
> honest abstentions where the evidence didn't clear the three-harmonic floor.
> Median warning: ninety-nine minutes before end of life. The best case,
> forty-two hours. When this system doesn't know, it says so. That's the
> entire point."
> (Lead-time semantics reconciled in eval/onset_inspection.md; if pressed:
> median 98 excluding the one bearing whose baseline was contaminated, we
> state it both ways.)

## 06 · TEAM + TECH (3:50-4:20) — stack lands HERE, once, wired-or-cut

> "Four builders, four lanes, one day: [stack as ACTUALLY wired at freeze, 2-3
> of NemoClaw / OpenClaw / OpenShell + MongoDB + SciPy, one sentence]. Full
> disclosure: the core engine and its frozen evaluation were prepared ahead as
> our disclosed starter scaffold, timestamped in the repo, as the rules allow;
> today is everything that makes it a product on this box: the bring-up, the
> wiring, the agent tools, and the demo you just watched. [If side challenge confirmed:]
> And for the MongoDB side challenge: the database IS the safety mechanism
> AND the agent's memory; immutable geometry versions, a compare-and-set
> human gate, a work order that cannot exist without its evidence, and a
> watch agent that survives being killed because it resumes from the record,
> not from the process. If a JSON file would do, we wouldn't need any of it."

## 07 · CLOSE (4:20-4:40) — proof-of-concept close + hook callback + the line

(Guide rules: never close on "thank you" or a summary; name what you want,
call back to the hook, leave ONE line in the room.)

> "That practitioner we talked to checks bearings the way plants have for
> forty years: monthly, by hand, hoping the failure waits. What you just
> watched became a product today, on this box, on real run-to-failure data,
> and it never guessed once. Give us the win and this goes from a hackathon
> table to a plant floor. Detect the change. Explain the spectrum. Escalate
> with evidence. A human has to say yes."

Final slide: QR to the public repo. 20 seconds of buffer held. Do NOT say
"thank you" as the last word; the mantra is the last word.

## Slide cues (deck = docs/deck/Bearing_Witness_Pitch_Deck.pdf, 10 slides)

LIVE STAGE VARIANT: present from docs/deck/Bearing_Witness_Stage_Deck.pdf
(10 slides). Differences from the portal deck, all deliberate: the title
slide carries no tagline or mantra (the hook stays a mystery; the mantra
debuts at the close), the old stats slide is SPLIT so the flips match the
spoken order (S2 = 41% + once-a-month-by-hand for the hook; S3 = $125k + the
lockout for the agitate), a dark SOLUTION reveal slide sits at S4 ("lives
entirely on this box" / "Nothing leaves the room."), and the evidence/refusal
screenshots are removed because the live app IS those slides. Arrow keys walk
the exact pitch order with zero skipping: 1 Title, 2 Problem, 3 Blind spot,
4 Solution, 5 How it works, 6 Always-on (switch to the app here), demo in the
app, then 7 Pays-for-the-box, 8 Receipts, 9 Team+Tech, 10 Close. The portal
PDF stays the submission so pre-eval readers get the tagline up front and the
evidence and refusal screens without a narrator.

| Script beat | On screen |
|---|---|
| 01 Hook | Slide 1 (title + real bearing) → Slide 2 on "forty-one percent" |
| 02 Agitate | Slide 2 stays ($125k + monthly-by-hand are on it) |
| 03 Solution | Slide 3 (the one sentence + four steps) |
| 04 Demo | Slide 4 (ALWAYS-ON) for ten seconds, THEN SWITCH TO THE LIVE APP and stay there for all demo steps — slides 6/7 exist so the PDF stands alone for pre-eval readers; live, the app IS those slides |
| 05 Impact | Back to slides: Slide 5 (pays for the box) → Slide 8 (0/0 · 99 min · 42 h) |
| 06 Team+Tech | Slide 9 |
| 07 Close | Slide 10 (the mantra; it's the last thing on screen) |

One rule from the guide: slides tell, the demo shows. The moment the app is up,
nobody looks back at the deck until the numbers.

## Q&A prep (part of the pitch; three-move rule on risk questions)

- "What were the challenges?" -> the honest one: sm_121 silicon day-one, the
  11:15 Ollama parachute decision, and keeping claims measured under deadline.
- "What would you build next?" -> SK band selection over the fixed 2-4 kHz
  demod band; more bearings into the fleet; the analyst-review queue for teams.
- "Business value?" -> ABB $125k/hour median (named as ABB's survey), the
  monthly blind spot, one catch pays for the box.
- "Who are your users?" -> reliability/vibration teams in OT-isolated plants;
  built from a real practitioner conversation this month.
- "What makes this different?" -> physics owns diagnosis (SciPy, deterministic,
  auditable); the model explains and files paperwork; and the system refuses
  without trust. Most demos add AI; ours constrains it.
- Prevention-frame questions (accuracy, false alarms): acknowledge -> answer
  with the frozen-thresholds + verbatim-evaluator evidence -> advance to the
  human-gate design. Never leave the room in a risk frame.

## Delivery rules

- Rehearse x3 timed after the 16:30 freeze; memorize the hook COLD.
- RECORD one full rehearsal as the hardwired backup video (screen + voice);
  if the live demo dies, cut to it without hesitation (Golden Rule 12).
- Use the provided monitor, not a laptop screen; judges cluster.
- Never say a number that is not on a screen, in the frozen evaluator output,
  or in the sourced-stat list above.
- No em-dashes, no AI-tone words on slides or in speech notes.
