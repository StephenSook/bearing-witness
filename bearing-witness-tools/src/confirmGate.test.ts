import { describe, it, expect } from "vitest";
import confirmGate from "./confirmGate.js";

function registerAndCapture() {
  let captured: any;
  confirmGate.register({
    registerTrustedToolPolicy: (policy: any) => {
      captured = policy;
    },
  } as any);
  if (!captured) throw new Error("registerTrustedToolPolicy was not called");
  return captured;
}

describe("confirmGate", () => {
  it("requires approval before submit_decision fires", () => {
    const policy = registerAndCapture();
    const decision = policy.evaluate({
      toolName: "submit_decision",
      params: { condition: "35Hz12kN", bearing: "Bearing1_3", record: 155, decision: "APPROVE", reason: "x" },
    });
    expect(decision).toBeTruthy();
    expect(decision.requireApproval).toBeTruthy();
    expect(decision.requireApproval.allowedDecisions).toEqual(["allow-once", "allow-always", "deny"]);
    expect(decision.requireApproval.title).toContain("APPROVE");
    expect(decision.requireApproval.title).toContain("Bearing1_3");
  });

  it("does not gate the five read-only tools", () => {
    const policy = registerAndCapture();
    for (const toolName of ["diagnose_bearing", "check_blockers", "get_evidence", "test_without_geometry", "replay_timeline"]) {
      const decision = policy.evaluate({ toolName, params: {} });
      expect(decision).toBeUndefined();
    }
  });

  it("declares a stable policy id", () => {
    const policy = registerAndCapture();
    expect(policy.id).toBe("bearing-witness-confirm-submit-decision");
    expect(typeof policy.description).toBe("string");
    expect(policy.description.length).toBeGreaterThan(0);
  });
});
