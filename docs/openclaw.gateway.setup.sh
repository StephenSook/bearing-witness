#!/usr/bin/env bash
# Gateway/sandbox config for the OpenClaw agent running Bearing Witness's
# six tools. NOT run automatically — this is the reference for applying our
# agent-surface config on the GB10 box, once OpenClaw/NemoClaw is confirmed
# installed there (GB10-RUNBOOK.md, §04 onboard done, §05 hardened).
#
# We originally wrote this as a JSON5 blob meant to be hand-pasted into
# ~/.openclaw/openclaw.json. That doesn't match how config actually gets
# changed on this box: GB10-RUNBOOK.md never edits openclaw.json directly —
# every config change goes through `nemoclaw <sandbox> config set`, e.g.
# its §05.2 memory-search example. Rewritten to match that pattern.
#
# Sandbox name is "hack-agent", agent id is "main", per GB10-RUNBOOK.md.
# Substitute if either changes on the box.
#
# Untested against a live sandbox — dry-run mentally by reading each value
# back after setting it (see "Verify" section at the bottom), and don't
# trust this file over what the box actually reports.

set -euo pipefail

SANDBOX=hack-agent

# --- every session sandboxed, agent reads the workspace read-only ----------
nemoclaw "$SANDBOX" config set --config-accept-new-path \
  --key agents.defaults.sandbox \
  --value '{"mode":"all","scope":"session","backend":"openshell","workspaceAccess":"ro"}' \
  --restart

# --- openshell plugin entry (remote mode = lower per-turn overhead) --------
# Egress itself is NOT closed here — that's GB10-RUNBOOK.md §05.1:
#   nemoclaw hack-agent policy exclude nvidia --yes
#   nemoclaw hack-agent policy remove  openclaw-pricing --yes
# (optionally also: nemoclaw hack-agent policy remove huggingface --yes)
nemoclaw "$SANDBOX" config set --config-accept-new-path \
  --key plugins.entries.openshell \
  --value '{"enabled":true,"config":{"from":"openclaw","mode":"remote","autoProviders":true,"timeoutSeconds":60}}' \
  --restart

# --- tool allowlist: everything not listed here is auto-blocked ------------
nemoclaw "$SANDBOX" config set --config-accept-new-path \
  --key tools.sandbox.tools \
  --value '{"allow":["diagnose_bearing","check_blockers","get_evidence","submit_decision","test_without_geometry","replay_timeline"],"deny":["group:fs","group:web","group:runtime"]}' \
  --restart

# --- Verify. Don't just trust this file. ------------------------------------
#   nemoclaw "$SANDBOX" policy list
#   openclaw sandbox list
#   openclaw sandbox explain --agent main --json
#     -> confirm the six tools show under tools.allow and the three
#        group:* entries under tools.deny, sourced from config (not default)
#   nemoclaw "$SANDBOX" status | grep -E 'integrate\.api\.nvidia\.com|openrouter\.ai' \
#     && echo "STILL EXPOSED" || echo "clean"
#     -> confirms GB10-RUNBOOK.md §05.1's exclude/remove actually landed
