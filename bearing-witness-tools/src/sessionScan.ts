import type { OpenClawPluginApi } from "openclaw/plugin-sdk/plugin-entry";
import { postScan } from "./postScan.js";

// postScan.ts existed, was unit-tested, and was never called anywhere in the
// live pipeline -- task 3.5 was built but not wired, the same shape of bug
// confirmGate.ts had (see its own NOTE). This module is the wiring.
//
// The scan has to run on the assistant's own drafted prose, which isn't
// available inside any tool's execute() -- that only sees the tool's OWN
// JSON return value, not what the model later writes about it. The two hook
// points that bracket that gap are `after_tool_call` (captures the
// diagnostic result the report will be drafted from) and
// `reply_payload_sending` (the last point before the reply actually goes
// out, and the only one whose result type lets a plugin substitute text
// outright -- `before_agent_finalize` only supports "continue"/"revise" with
// a retry instruction, which asks the model to try again; task 3.5's own
// spec is "swap safe JSON line, NO retry", so that hook is the wrong shape
// for this even though it fires earlier).
//
// Correlating the two hooks by sessionKey, not runId: OpenClaw's own
// hook-types comments say reply_payload_sending's runId is "not yet plumbed
// through the outbound delivery path" and name sessionKey as the field
// plugins should rely on for exactly this after_tool_call -> outbound
// correlation.
const lastDiagnosticResult = new Map<string, { status: string; refusal_reasons: string[]; [key: string]: unknown }>();

function looksLikeDiagnosticResult(
  value: unknown
): value is { status: string; refusal_reasons: string[]; [key: string]: unknown } {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).status === "string" &&
    Array.isArray((value as Record<string, unknown>).refusal_reasons)
  );
}

export function registerSessionScan(api: OpenClawPluginApi): void {
  api.on("after_tool_call", (event, ctx) => {
    if (!ctx.sessionKey) return;
    // only diagnose_bearing/check_blockers/submit_decision/test_without_geometry
    // return a full-shaped result (get_evidence and replay_timeline don't carry
    // status/refusal_reasons) -- the type guard, not a toolName allowlist, is
    // what actually decides this, so it stays correct if a tool's shape changes
    if (looksLikeDiagnosticResult(event.result)) {
      lastDiagnosticResult.set(ctx.sessionKey, event.result);
    }
  });

  api.on("reply_payload_sending", (event, ctx) => {
    if (!ctx.sessionKey) return;
    const result = lastDiagnosticResult.get(ctx.sessionKey);
    if (!result) return; // nothing this turn touched a diagnostic result -- nothing to score the report against
    lastDiagnosticResult.delete(ctx.sessionKey); // single-use: one drafted report per captured result, never stale-reused
    const text = event.payload.text;
    if (!text) return;
    const scanned = postScan(text, result);
    if (scanned === text) return;
    return { payload: { ...event.payload, text: scanned } };
  });
}
