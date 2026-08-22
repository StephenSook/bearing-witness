import { describe, it, expect } from "vitest";
import { checkReport, checkLocators, collectKnownLocators, postScan, LOCATOR_RE } from "./postScan.js";
import { decide } from "./cli.js";

// mirrors fixtures/analyst_review_required.json's candidate_families[0].locators
const RED_RESULT = {
  status: "ANALYST_REVIEW_REQUIRED",
  refusal_reasons: [] as string[],
  candidate_families: [
    {
      family: "BPFO",
      locators: [
        "XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1",
        "XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|214.06Hz|h2",
        "XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|321.09Hz|h3",
      ],
    },
  ],
};

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

describe("LOCATOR_RE", () => {
  it("matches a well-formed harmonic locator", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1")).toBe(true);
  });

  it("matches a well-formed sideband locator", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1|sb-1")).toBe(true);
  });

  it("matches a residual peak locator with no harmonic", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|ordinary|60.00Hz")).toBe(true);
  });

  // The regex itself (verbatim from PLAN.md) does NOT encode "|sb never
  // without |h" — |h and |sb are independently optional groups. That
  // invariant is enforced where locators are generated
  // (bearing_witness/contract.py's locator() raises on sb without h), and
  // by extension via checkLocators' known-locator membership check: a
  // fabricated sb-without-h string would never be in a result's real
  // evidence, so it gets rejected there even though the regex alone allows
  // the shape.
  it("the regex alone allows a sideband without a harmonic (documented gap, not a bug)", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|sb-1")).toBe(true);
  });

  it("rejects a bad view name", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|raw|107.03Hz")).toBe(false);
  });

  it("rejects a non-hex sha8", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|zzzzzzzz|envelope|107.03Hz")).toBe(false);
  });

  it("rejects a frequency without two decimal places", () => {
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.0Hz")).toBe(false);
  });
});

describe("collectKnownLocators", () => {
  it("walks nested arrays/objects and finds every real locator", () => {
    const known = collectKnownLocators(RED_RESULT);
    expect(known.size).toBe(3);
    expect(known.has("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1")).toBe(true);
  });

  it("ignores plain strings that aren't locator-shaped", () => {
    const known = collectKnownLocators({ note: "outer race, high confidence", status: "RED" });
    expect(known.size).toBe(0);
  });
});

describe("checkLocators", () => {
  const known = collectKnownLocators(RED_RESULT);

  it("passes text citing a real locator from this result unchanged", () => {
    const text = "Outer race pattern at 107.03Hz, see XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1.";
    expect(checkLocators(text, known, "ANALYST_REVIEW_REQUIRED", [])).toBe(text);
  });

  it("passes text that cites no locator at all unchanged", () => {
    const text = "Outer race pattern, review recommended.";
    expect(checkLocators(text, known, "ANALYST_REVIEW_REQUIRED", [])).toBe(text);
  });

  it("blocks a well-formed locator that isn't in this result's evidence (fabricated or wrong window)", () => {
    const text = "See XJTU-SY/35Hz12kN/Bearing1_3|w999|deadbeef|envelope|999.99Hz|h1 for confirmation.";
    const result = checkLocators(text, known, "ANALYST_REVIEW_REQUIRED", []);
    expect(result).not.toContain("w999");
    expect(result).toContain("Status: ANALYST_REVIEW_REQUIRED");
  });

  it("blocks a malformed locator-shaped token even if the prefix looks real", () => {
    const text = "See XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.0Hz|h1 for confirmation.";
    const result = checkLocators(text, known, "ANALYST_REVIEW_REQUIRED", []);
    expect(result).not.toContain("107.0Hz");
  });

  it("blocks a sb-without-h locator the regex alone would accept, since it's not in this result's evidence", () => {
    const text = "See XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|sb-1 for confirmation.";
    expect(LOCATOR_RE.test("XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|sb-1")).toBe(true);
    const result = checkLocators(text, known, "ANALYST_REVIEW_REQUIRED", []);
    expect(result).not.toContain("sb-1");
  });
});

describe("postScan", () => {
  it("banned-word check runs first and wins even with a valid locator present", () => {
    const text = "You should replace it — see XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1.";
    const result = postScan(text, RED_RESULT);
    expect(result).not.toContain("replace it");
  });

  it("blocks a fabricated locator even when the text has no banned words", () => {
    const text = "Outer race pattern, see XJTU-SY/35Hz12kN/Bearing1_3|w999|deadbeef|envelope|999.99Hz|h1.";
    const result = postScan(text, RED_RESULT);
    expect(result).not.toContain("w999");
  });

  it("passes a clean report citing real evidence through unchanged", () => {
    const text = "Outer race pattern, see XJTU-SY/35Hz12kN/Bearing1_3|w155|3f8a91c2|envelope|107.03Hz|h1.";
    expect(postScan(text, RED_RESULT)).toBe(text);
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
