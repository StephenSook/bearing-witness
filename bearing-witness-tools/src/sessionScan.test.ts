import { describe, it, expect, beforeEach } from "vitest";
import { registerSessionScan } from "./sessionScan.js";

const RED_RESULT = {
  status: "ANALYST_REVIEW_REQUIRED",
  refusal_reasons: [] as string[],
  candidate_families: [{ locators: ["asset|w155|abc12345|envelope|107.03Hz|h1"] }],
  inspection_draft: { evidence_locators: [] as string[] },
};

function register() {
  const handlers: Record<string, Function> = {};
  registerSessionScan({
    on: (name: string, handler: Function) => {
      handlers[name] = handler;
    },
  } as any);
  if (!handlers.after_tool_call || !handlers.reply_payload_sending) {
    throw new Error("both hooks were not registered");
  }
  return handlers;
}

describe("sessionScan", () => {
  let handlers: Record<string, Function>;
  beforeEach(() => {
    handlers = register();
  });

  it("passes a report through untouched when it stays inside the evidence", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, { sessionKey: "s1" });
    const text = "Persistent outer-race signature, analyst review pending.";
    const out = handlers.reply_payload_sending({ payload: { text } }, { sessionKey: "s1" });
    expect(out).toBeUndefined();
  });

  it("swaps a banned-word report for the deterministic fallback", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, { sessionKey: "s2" });
    const text = "The fault is confirmed, replace the bearing immediately.";
    const out = handlers.reply_payload_sending({ payload: { text } }, { sessionKey: "s2" });
    expect(out).toBeTruthy();
    expect(out.payload.text).not.toContain("replaced");
    expect(out.payload.text).toContain("ANALYST_REVIEW_REQUIRED");
  });

  it("swaps a fabricated-locator claim even with no banned words", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, { sessionKey: "s3" });
    const text = "See locator asset|w999|deadbeef|envelope|999.00Hz|h9 for the source measurement.";
    const out = handlers.reply_payload_sending({ payload: { text } }, { sessionKey: "s3" });
    expect(out).toBeTruthy();
    expect(out.payload.text).not.toContain("w999");
  });

  it("does nothing for a session that never touched a diagnostic result", () => {
    const out = handlers.reply_payload_sending(
      { payload: { text: "replace the whole gearbox, fault confirmed" } },
      { sessionKey: "never-analyzed" }
    );
    expect(out).toBeUndefined();
  });

  it("does nothing when sessionKey is missing on either side", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, {});
    const out = handlers.reply_payload_sending({ payload: { text: "replace it now" } }, {});
    expect(out).toBeUndefined();
  });

  it("ignores tool results that aren't diagnostic-shaped (get_evidence, replay_timeline)", () => {
    handlers.after_tool_call(
      { toolName: "get_evidence", result: { candidate_families: [] } },
      { sessionKey: "s4" }
    );
    const out = handlers.reply_payload_sending(
      { payload: { text: "replace it now, fault confirmed" } },
      { sessionKey: "s4" }
    );
    expect(out).toBeUndefined();
  });

  it("is single-use: a second reply in the same session after the same tool call is not re-scanned", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, { sessionKey: "s5" });
    handlers.reply_payload_sending({ payload: { text: "replace it now" } }, { sessionKey: "s5" });
    const second = handlers.reply_payload_sending(
      { payload: { text: "replace it now" } },
      { sessionKey: "s5" }
    );
    expect(second).toBeUndefined();
  });

  it("preserves the rest of the payload when substituting text", () => {
    handlers.after_tool_call({ toolName: "diagnose_bearing", result: RED_RESULT }, { sessionKey: "s6" });
    const out = handlers.reply_payload_sending(
      { payload: { text: "replace it now", mediaUrls: ["a.png"], replyToId: "42" } },
      { sessionKey: "s6" }
    );
    expect(out.payload.mediaUrls).toEqual(["a.png"]);
    expect(out.payload.replyToId).toBe("42");
  });
});
