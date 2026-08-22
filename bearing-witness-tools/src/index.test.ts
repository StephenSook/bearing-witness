import { describe, it, expect } from "vitest";
import { checkReport } from "./postScan.js";
import { decide } from "./cli.js";

describe("checkReport", () => {
  it("passes 'location unconfirmed' on ABNORMAL_LOCATION_UNCONFIRMED", () => {
    const result = checkReport("location unconfirmed", "ABNORMAL_LOCATION_UNCONFIRMED", []);
    expect(result).toBe("location unconfirmed");
  });

  it("passes 'recommend replacement' since replacement is not replace", () => {
    const result = checkReport("we recommend replacement", "WATCH_EARLY", []);
    expect(result).toBe("we recommend replacement");
  });

  it("blocks 'replace' on a non-reviewed status", () => {
    const result = checkReport("you should replace it", "WATCH_EARLY", ["EARLY_INDICATORS"]);
    expect(result).not.toContain("replace it");
    expect(result).toContain("Status: WATCH_EARLY");
  });

  it("blocks 'confirmed' on NO_ANOMALY_DETECTED", () => {
    const result = checkReport("pattern is confirmed", "NO_ANOMALY_DETECTED", []);
    expect(result).not.toContain("pattern is confirmed");
  });

  it("allows 'confirmed' on ANALYST_REVIEW_REQUIRED", () => {
    const result = checkReport("pattern is confirmed", "ANALYST_REVIEW_REQUIRED", []);
    expect(result).toBe("pattern is confirmed");
  });

  it("blocks 'replace' even on ANALYST_REVIEW_REQUIRED", () => {
    const result = checkReport("replace the bearing now", "ANALYST_REVIEW_REQUIRED", []);
    expect(result).not.toContain("replace the bearing");
  });
});

describe("decide", () => {
  it("approves and returns an updated status plus a recorded human review", async () => {
    const r = await decide("35Hz12kN", "Bearing1_3", 155, "APPROVE", "pattern matches; schedule visual");
    expect(r.status).toBe("INSPECTION_APPROVED");
    expect(r.human_review.decision).toBe("APPROVE");
    expect(r.human_review.reason).toBe("pattern matches; schedule visual");
    expect(r.analysis_id).toContain("Bearing1_3");
  });

  it("rejects and still returns a recorded human review", async () => {
    const r = await decide("35Hz12kN", "Bearing1_3", 155, "REJECT", "sensor was bumped");
    expect(r.status).toBe("INSPECTION_REJECTED");
    expect(r.human_review.decision).toBe("REJECT");
  });

  it("defers without changing status", async () => {
    const r = await decide("35Hz12kN", "Bearing1_3", 155, "DEFER", "waiting on second channel");
    expect(r.status).toBe("ANALYST_REVIEW_REQUIRED");
    expect(r.human_review.decision).toBe("DEFER");
  });
});
