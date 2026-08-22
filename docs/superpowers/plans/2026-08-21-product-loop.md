# Bearing Witness: Stephen's Lane, Built Tonight (Fri 2026-08-21)

## Context

Dell x NVIDIA GB10 hackathon is tomorrow (Sat 2026-08-22, doors 9:00, submission ~18:00). PLAN.md on `StephenSook/NVIDIA-x-Dell` (private, main @ `322b035`, remote verified in sync) assigns Stephen: **MongoDB backbone, evidence UI, demo, fresh public repo, written submission** (Phase 2 tasks 2.1-2.10 + Phase 4 tasks 4.2-4.6), plus open questions Q2 (MongoDB prize, on site) and Q3 (Friday-night recon).

Grilling decisions locked with Stephen tonight:

1. **Write real code files tonight** (extends the D5 scaffold clearance to Stephen's lane; submission discloses it plainly alongside Vinh's prep).
2. **Vinh is typing his engine tonight too.** His lane stays his in PLAN.md; his commits will land on main. My code never touches his files.
3. **brew install mongodb-community@8.0** locally for real validator/time-series testing tonight.
4. **Frontend: ALL-IN.** Full haoqi.design journey including WebGL-class effects, vendored offline, kill-switchable, every HUD value real. Frontend doc prompts (start + end) read in full; all 34 pasted `image*.png` reviewed (haoqi portfolio: sticker badges, pixel-mono icon sets, mono flight-board posters). FRONTEND_DESIGN_LANGUAGE_Aug21.md is the token/steal-map source; the all-in decision overrides its Saturday-triage caps (its "cut fluid/stickers/BGM from judged surfaces" and "every value real" rules stay).
5. Fixtures-first, import-free: code consumes 14-field contract-shaped dicts; a thin adapter switches to `bearing_witness.contract` the moment Vinh's package lands on main.
6. **Vinh's new commit reviewed** (`bdf4d26` "Pre-event verification lookups", merged PR #2; remote main is now `9486095`, local pull needed at P0). Product-lane takeaways to fold in: Randall & Antoni 2011 / ISMA 2016 verbatim citations for the 1-2% slip tolerance, BPFI shaft-speed sidebands, and "envelope amplitude is not severity" (trust panel copy + submission citations); verified LDK UER204 geometry table (8 balls, 7.92 mm, pitch 34.55 mm, BPFO 107.91 confirmed) with sources for `asset_configs` provenance fields; demo-runbook reboot nuance (managed vLLM restarts, sandbox/gateway/Ollama do not; recovery `nemoclaw <name> status -> start -> rebuild --yes`; DO NOT REBOOT stays the rule); biaowang.tech is up again (README link fine).
7. **NiceGUI skill rig from Vinh:** `evnchn-nicegui/nicegui-skill` (MIT, alpha): fetch its `skill/` files (SKILL.md, ELEMENTS.md, LAYOUTS.md, STYLING.md, BEST_PRACTICES.md, TESTING.md) into the scratchpad and read before the UI build; use alongside Context7 NiceGUI docs.
8. **Icon/sticker/background generation:** kie.ai via direct API with the existing Keychain key `kie-ai-api-key` (kie MCP not wired this session), banana skill (Gemini image) as alternative, plus license-checked web-sourced photos. Style target: haoqi's sticker/badge language re-themed to bearings (race rings, instrument badges, pixel-mono chips). No new API keys needed from Stephen; Pinterest unnecessary.

Hard constraints that survive everything: traffic light is a costume (state string always printed); red = inspect, never replace; corpus never committed or re-hosted; practitioner material never leaves private surfaces; this repo never goes public (D6); no em-dashes in outward text; evaluator numbers only from frozen v3 or a fresh Saturday freeze.

## Scope

**In scope (tonight):** PLAN.md tasks 2.1-2.10 (Mongo, store, UI shell, fleet, evidence, trust, decisions, fixtures wiring, report.html, audio prep) + 4.2/4.4/4.5 skeletons (runbook, submission draft, disclosure) + Q3 recon + the files listed below.
**Out of scope:** detector/DSP/evaluator (Vinh), vLLM/box stack (Beeds), OpenClaw tools/OpenShell policy (Jadyn), every Vinh-owned path (`bearing_witness/`, `eval/`, `prep/`, `tests/`, `pyproject.toml`), the fresh public repo (Saturday 4.3), submitting anything.

## File layout (zero collision with Vinh's plan)

Vinh's plan owns `bearing_witness/`, `eval/`, `prep/`, `tests/`, `pyproject.toml`. My code goes in a separate top-level package:

```
bw_product/
  __init__.py
  contract_shape.py      14-field dict shape + status/task vocab + traffic-light map + adapter:
                         try `from bearing_witness import contract` else local fallback
  store.py               Mongo: 3 collections (asset_configs immutable-versioned,
                         feature_windows time-series, diagnostic_cases validated w/ unique
                         analysis_key), $jsonSchema validators, conditional single-doc
                         task-creation update, MongoDecisionStore.record() -> HumanReview shape
  fixtures.py            builds green/yellow/red contract dicts + (freqs, amp) series from REAL
                         kit CSVs (Bearing1_3 files 2/8 vs 155; BPFO 107.03, harmonics, cage
                         sidebands; slip 34.7 vs 35.0 setpoint) - read-only from /Volumes/BWITNESS
  audio.py               native-speed 1.28 s WAV pairs (early vs late), equal loudness,
                         scipy.io.wavfile only (task 2.10 prep)
  report.py              self-contained report.html generator (inline plotly, <audio>, work order)
  ui/
    main.py              NiceGUI app entry (python -m bw_product.ui)
    theme.py             design tokens from FRONTEND_DESIGN_LANGUAGE_Aug21.md
    hud.py               persistent HUD chrome (all values real: replay meta, window counter, state chip)
    fleet.py             poster-card fleet grid, exact denominator, unevaluated = unselectable
    evidence.py          trend + two spectra side by side + expected-family dashed lines w/
                         uncertainty bands + evidence locators (click -> window/freq/hash)
    trust.py             trust/provenance panel incl. slip disclosure (35.0 setpoint vs ~34.7 measured)
    decide.py            traffic light + exact state string + approve/reject -> MongoDecisionStore
    fx/                  all-in effects, each behind BW_FX kill switch, judged loop works with FX off:
      preloader.js       warm field + thin progress bar
      pinhole.js         2D-canvas halftone dot-matrix reveal (screen + theme transitions)
      scramble.js        ASCII scramble label mount (80 ms/letter)
      spectrum3d.js      dark "wow" screen: three.js streak tunnel from real spectrum energy,
                         lime wireframe bearing-race rings, navy dashed predicted lines
    static/vendor/       three.module.js (MIT) + fonts (license-checked) - offline, no CDN
  fixtures_data/         generated JSON fixtures + WAVs + generated art (ours, committable)
  tests/                 MY tests (separate from Vinh's tests/): test_store_validators.py,
                         test_store_decisions.py, test_fixtures_validate.py, test_contract_shape.py,
                         test_report.py  (run: .venv-product/bin/python -m pytest bw_product/tests -q)
.venv-product/           venv (gitignore entry verified/added before first commit)
requirements-product.txt  (pins matched to kit 06_PACKAGES wheel versions)
docs/superpowers/plans/2026-08-21-product-loop.md   (this plan, committed for the team)
docs/DEMO_RUNBOOK.md     7-step demo script, timed, kill-switch notes, DO NOT REBOOT
docs/SUBMISSION_DRAFT.md written-submission skeleton + D5 scaffold-disclosure paragraph
```

## Phases

Time budgets (single night, doors 9:00): P0 ~45 min, P1 ~90 min, P2 ~60 min, P3 ~2 h, P4 ~3 h, P5 ~60 min, P6 ~90 min, P8 ~60 min, P9 ~30 min. **Hard preemption rule: P4 (effects) has an abort clock; when it trips, or whenever P5 (report.html/audio) and P8 (runbook/submission skeleton) are not yet done and fewer than 3 hours of working time remain, P5 + P8 preempt P4 regardless of FX state.** Tier 0 (P1-P3) is never preempted.

**P0 Setup.** Serena activate; `git pull` (watch for Vinh's commits); claim tasks in PLAN.md (status commit per protocol: `status: 2.1 🟡 ...`, push; osxkeychain fallback `git -c credential.helper='!gh auth git-credential' push`). Python venv at root; read kit `06_PACKAGES` wheel versions (read-only) and pin nicegui/pymongo/plotly/numpy/scipy/pydantic to match; pip install + pytest. `brew tap mongodb/brew && brew install mongodb-community@8.0`, bind 127.0.0.1, `mongosh ping`. **Mongo fallback ladder:** brew fails -> Docker `mongo:8.0` (ARM image); Docker unavailable too -> code the store anyway, mark mongod-dependent tests `@pytest.mark.needs_mongod` (skip locally, MUST run on the box Saturday before any Mongo claim ships). Vendor three.js + fonts (verify Geist Mono OFL / Departure-Mono-class license before committing; else system mono). Commit convention: atomic, named paths only, no `git add -A`, no Co-Authored-By (repo convention per engine plan).

**P1 Mongo backbone (2.1, 2.2).** `store.py` + real tests against local mongod: validators reject bad status/task vocab (`INSPECTION_WORK_ORDER` vocabulary), time-series insert, immutable asset_config versioning, conditional single-document update = no work order without its evidence record, unique `analysis_key`, approve AND reject both persist, evidence retained on reject. TDD.

**P2 Real fixtures.** `fixtures.py` reads Bearing1_3 from the kit (read-only): early files (green baseline), mid WATCH_EARLY, file 155 red with BPFO family + cage sidebands. Emit contract dicts + series arrays + sha256 locators using the real measured numbers from PREP_PLAN. These drive the UI until Vinh's engine lands. **Verification gate: `pytest bw_product/tests/test_fixtures_validate.py`, exit 0 — every fixture dict passes `contract_shape` vocab checks AND inserts cleanly into `diagnostic_cases` under the live $jsonSchema validators.** Contract source of truth: `contract_shape.py` fields and status/task vocab are TRANSCRIBED from Vinh's plan (`docs/superpowers/plans/2026-08-21-engine.md`, Task 9 `ResultContract` + `EMPTY` dict) and PLAN.md's Shared Contracts table — never recalled from memory; if his `contract.py` is on main by then, transcribe from the code itself.

**P3 UI Tier 0 (2.3-2.7).** HUD shell, fleet, evidence, trust panel, traffic light + approve/reject writing through MongoDecisionStore. Plain, complete, honest. This is the 13:15-gate insurance: the loop exists before any effect.

**P4 UI all-in (haoqi journey).** First read the `evnchn-nicegui/nicegui-skill` rig (fetched to scratchpad) + Context7 NiceGUI docs. Then: preloader, pinhole halftone reveal, scramble labels, editorial interstitials (DETECT. / EXPLAIN. / ESCALATE.), poster fleet cards with lime state chips, dark WebGL spectrum screen (real spectrum data in, rings echo bearing races), demo choreography = amendment's 7 steps mapped onto their scroll arc. `BW_FX=off` renders the same screens flat. Generated art (bearings-themed badges, sticker-style chips, backgrounds in haoqi's badge language): kie.ai direct API using Keychain key `kie-ai-api-key`, model `google/nano-banana-pro` (fallback flux), **max 12 images, spend ceiling $3**; banana skill or higgsfield MCP as alternates (higgsfield: check `balance` first), license-checked web photos as a third source.

**P5 report.html + audio (2.9, 2.10).** `report.py` emits the self-contained insurance page (inline plotly, cinematic CSS freedom, audio tags, drafted work order). `audio.py` writes the early/late WAV pair. **Loudness is measured, not ear-tested: `ffmpeg -filter:a ebur128` per WAV, integrated loudness target -16 LUFS (accept -14 to -18), pair delta <= 1 LU, checked on the shipped files** (shipped-media hard rule); then an audibility listen on the Mac, room speaker Saturday, cut without mourning if unclear.

**P6 Verification.** pytest green (bare exit, no pipes); Playwright MCP click-through: fleet -> evidence -> red -> approve persists -> reject persists -> geometry-unverified refusal renders; screenshots both themes, FX on and off (ui-self-heal loop on visual defects); then a Codex adversarial pass over the full diff (background companion runtime), iterating until a clean round, per the second-model hard rule.

**P7 Vinh integration (2.8 early).** When his `contract.py`/`engine.py` land on main: pull, flip the adapter, run one real `Engine.analyze()` window through store -> UI, **then re-run the full P6 gate (pytest + the Playwright 7-step walk) in adapter mode — the shipped state must equal the verified state.** If his package hasn't landed by end of night, fixtures remain, and Saturday's 2.8 proceeds as planned. Never edit his files; coordinate via PLAN.md.

**P8 Docs + recon (Q3, 4.4/4.5 skeletons).** DEMO_RUNBOOK.md (incl. the LOOKUPS reboot-recovery nuance); SUBMISSION_DRAFT.md with the D5 disclosure paragraph, the Randall & Antoni / ISMA 2016 / dataset DOI citations from LOOKUPS, and a wired-or-cut checklist (every named tech greppable in shipped code before any claim); trust-panel copy cites "late-stage impacts broaden and overlap" per the verified wording, never a standard that does not say it. Friday-night recon: re-check event page/rubric weights/judge roster/submission fields/OpenShell releases via firecrawl/exa/WebSearch + Stephen's logged-in Chrome for BuilderBase (results into PLAN.md notes, claims into nothing until verified).

**P9 Close-out.** PLAN.md status flips (✅, atomic, pushed). Repo snapshot copied to kit `02_SOURCE` ONLY with the full triplet: copy + manifest rehash + `verify_offline_kit.sh --quick` bare-exit PASS (kit-sync hard rule; Cable 1). Memory writes to BOTH stores: Obsidian vault (`Claude Memory/` session summary + any decision notes) AND auto-memory dir (update `project_repo_and_decisions.md`, new `project_product_loop_built.md`, MEMORY.md index lines). Verify-what-a-commit-contains check on the final push.

## Verification (end-to-end)

1. `pytest` green locally, bare exit code.
2. `mongosh` shows 3 collections with validators; bad-vocab insert rejected; task-creation update refuses without gate state.
3. NiceGUI serves; Playwright walk of all 7 demo steps on fixtures; approve/reject rows visible in Mongo afterward.
4. `report.html` opens from file:// with charts + audio, no network.
5. FX kill switch: same walk passes with `BW_FX=off`.
6. Codex adversarial rounds until clean.
7. `git show HEAD:<path>` spot-checks that pushed commits contain what they claim.
8. P8 docs exist and are committed: DEMO_RUNBOOK.md, SUBMISSION_DRAFT.md (with disclosure paragraph + citations), recon notes in PLAN.md.
9. P9 done: PLAN.md statuses flipped and pushed; kit-sync triplet ends in bare-exit PASS; memory written to BOTH Obsidian vault and auto-memory dir.

## Exhaustive tool inventory (every skill, MCP, plugin, agent, connector reviewed)

**USE tonight**
- Skills: grilling (done); superpowers:writing-plans (this plan); superpowers:test-driven-development, verification-before-completion, requesting-code-review, executing-plans/subagent-driven-development (build discipline); karpathy-guidelines; frontend-design + frontend-design:frontend-design (UI quality); dataviz (spectra/trend chart craft); ui-ux-pro-max + ux-expert (design passes); ui-self-heal (screenshot-fix loop); banana (image gen); github; filesystem; session-memory (memory writes); caveman (output mode, active); three-brain (routing: Codex review mandatory on risky diff); codex:setup + codex:rescue + codex result-handling skills (adversarial pass); qa-systematic (golden-path smoke); theme-factory (optional token polish); regex-builder/test-harness (as needed); hackathon-project-flow (already governing this project); team-plan (PLAN.md system exists, protocol followed not re-scaffolded).
- MCP servers: serena (symbol nav/edits); claude.ai Context7 (NiceGUI/pymongo/plotly/three.js docs); plugin_playwright (UI verification); chrome-devtools / claude-in-chrome (BuilderBase recon in Stephen's logged-in Chrome, UI debugging); firecrawl + exa + tavily skill + WebSearch/WebFetch + apify rag-web-browser (Q3 recon; apify proven by Vinh's lookup pass); higgsfield (premium image gen alt); kie.ai direct API via Keychain (icons/backgrounds); ide (diagnostics if VS Code attached).
- External reference rig: `evnchn-nicegui/nicegui-skill` (MIT) skill files, fetched read-only to scratchpad before the UI build.
- Agents: Explore (fan-out searches), general-purpose (parallel side tasks), Plan (used in planning), plan-gap-scanner (this plan gets scanned before execution), codex:codex-rescue (second model), pr-review-toolkit:code-reviewer + silent-failure-hunter + code-simplifier and feature-dev:code-reviewer (review passes), cc-gemini-plugin:gemini-agent (optional large-context sweep).
- Saturday-reserved (in repo docs, not tonight): repo-sentinel + hackathon-pre-deploy (pre-public-repo audit), grade-rivals (on site), hard-rule-harvest + engineering-retro (post-event), devpost MCP only if recon shows a Devpost surface (event is BuilderBase/Luma).

**REVIEWED, NOT USED (with reason)**
- Cloud/deploy MCPs: vercel, netlify, railway, render, neon, supabase, cf-bindings, cloudflare-docs, aws-docs: product is fully local/offline by rule; no cloud in the runtime path.
- Data/PM connectors: Airtable, Notion, Linear, Gmail, Google Calendar/Drive, Microsoft 365, Atlassian Rovo, Slack (team uses Discord): no task tonight needs them.
- apify, huggingface (corpus already on kit; HF range-pull only as fallback), deepwiki, socket (deps are pinned wheels from the kit), sentry (no prod telemetry), lightpanda-browser (Playwright covers).
- Media/video skills: demo-video, demo-video-studio, remotion-video, remotion-best-practices, video-gen, concept-to-video, youtube-analysis, youtube-search, notebooklm: live demo, no video deliverable unless recon says otherwise.
- Docs/writing skills not needed tonight: adr-writer (decisions already in PLAN.md D1-D10), api-docs-generator, changelog-composer, copy-editing, copywriting (submission drafts written by hand for claims discipline; humanize/em-dash rules applied manually), linkedin-post-style, marp-slides, html-presentation, md-to-pdf, to-markdown, doc-condenser, literature-review, manuscript-provenance, manuscript-review, paper-to-skill, research-critique, graphify, knowledge-graph-3d, canvas-design, concept-to-image (banana covers), drawio-skill, architecture-diagram (steal-map + runbook suffice), figma:* and 21st:* and design/DesignSync (code-direct tonight), artifact-design/artifact-diagramming/artifact-capabilities + Artifact tool (competitive-moat material stays local; nothing published).
- Analysis/strategy skills already consumed or out of scope tonight: sookra-council, sookra-ideate, claude-council, devils-advocate, divergent-ideation, idea-validator, feasibility-assessor, estimate-calibrator, boil-the-ocean, auto-research, ab-test-setup, benchmark-runner, gpu-optimizer (no GPU code in my lane), sql-optimizer (Mongo not SQL), rag-auditor, prompt-lab, surrogate-verifier, task-decomposer (phases above), sequential-thinking (native reasoning suffices), last30days + web-research-analyst (recon uses firecrawl/exa directly; escalate if murky), agent-builder, mcp-to-skill, skill-distiller, skill-library, skill-update, scan-skill, memory-lint, morning-brief, distill-imports, usage-audit, immune, improve, code-refiner, codebase-design, debug-investigator + superpowers:systematic-debugging (invoked only if a bug appears), dependency-audit, migration-risk-analyzer, package-evaluator, env-validator, pr-review, pre-landing-review, printing-press family (API CLI generator, n/a), security-audit/security-review/claude-security:* (repo-sentinel covers Saturday; no auth surface tonight), ship-workflow, commit-commands:* (manual atomic commits per protocol), code-review:code-review + /simplify (Codex + pr-review-toolkit chosen instead), claude-md-management:*, claude-api skill (no Anthropic API code), update-config, keybindings-help, fewer-permission-prompts, loop/schedule/CronCreate (no recurring jobs; no busy-wait per hard rule), EnterWorktree (single-writer repo tonight), statusline-setup, claude-code-guide, vercel:ai-architect/deployment-expert/performance-optimizer, playground, EndConversation, Workflow (no explicit ultracode opt-in; Agent tool covers parallelism), superpowers:brainstorming (product long since locked), superpowers:using-git-worktrees/finishing-a-development-branch (work on main per team protocol), superpowers:receiving-code-review (applies when feedback arrives), caveman:compress, cc-gemini-plugin:gemini (agent variant preferred), 21st plugins, supabase skills, vercel skills (all), figma skills (all), init, run (custom NiceGUI launch documented in runbook).

## Risks

- Vinh commits tonight may add `pyproject.toml`/`tests/`: my package touches neither; only `requirements-product.txt` and `bw_product/` are mine. Pull before every task claim.
- WebGL on the GB10's browser Saturday is unproven: kill switch + Tier 0 loop first is the mitigation; report.html is the second parachute.
- Kit writes: ONLY via the copy+rehash+verify triplet, Cable 1, eject before unplug.
- Anything judge-facing quotes numbers only from measured runs (fixtures carry their provenance).
