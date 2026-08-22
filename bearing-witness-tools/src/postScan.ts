const BANNED_ALWAYS = [/\breplace\b/i];
const BANNED_UNLESS_REVIEWED = [/\bconfirmed\b/i];
const REVIEWED_STATUSES = ["ANALYST_REVIEW_REQUIRED", "INSPECTION_APPROVED"];

// Shared Contracts table, PLAN.md: {asset_id}|w{window}|{sha8}|{view}|{freq:.2f}Hz[|h{k}][|sb{m:+d}]
export const LOCATOR_RE =
  /^[^|]+\|w\d+\|[0-9a-f]{8}\|(ordinary|envelope)\|\d+\.\d{2}Hz(\|h\d+)?(\|sb[+-]\d+)?$/;

export function checkReport(text: string, status: string, refusalReasons: string[]): string {
  const banned = BANNED_ALWAYS.concat(
    REVIEWED_STATUSES.includes(status) ? [] : BANNED_UNLESS_REVIEWED
  );
  if (banned.some((re) => re.test(text))) {
    return fallbackLine(status, refusalReasons);
  }
  return text;
}

// Every result the six tools return carries real locators buried in nested
// objects/arrays (candidate_families[].locators, explained_peaks[].locator,
// spectrum peaks[].locator, inspection_draft.evidence_locators) in different
// shapes depending on which tool answered. Walking for anything matching
// LOCATOR_RE is shape-agnostic instead of hardcoding each tool's field paths.
export function collectKnownLocators(evidence: unknown): Set<string> {
  const found = new Set<string>();
  const walk = (v: unknown) => {
    if (typeof v === "string") {
      if (LOCATOR_RE.test(v)) found.add(v);
    } else if (Array.isArray(v)) {
      v.forEach(walk);
    } else if (v && typeof v === "object") {
      Object.values(v).forEach(walk);
    }
  };
  walk(evidence);
  return found;
}

// Locators never contain whitespace, so a citation attempt is any token with
// a pipe in it once common surrounding punctuation is stripped.
function extractLocatorLikeTokens(text: string): string[] {
  return text
    .split(/\s+/)
    .map((t) => t.replace(/^[("'`]+|[)"'`.,;:]+$/g, ""))
    .filter((t) => t.includes("|"));
}

// A claim citing something locator-shaped must be both well-formed AND one
// of the locators this specific result actually returned — the model can't
// cite a real-looking locator from a different window/asset, or invent one.
export function checkLocators(
  text: string,
  knownLocators: Set<string>,
  status: string,
  refusalReasons: string[]
): string {
  for (const token of extractLocatorLikeTokens(text)) {
    if (!LOCATOR_RE.test(token) || !knownLocators.has(token)) {
      return fallbackLine(status, refusalReasons);
    }
  }
  return text;
}

export function postScan(
  text: string,
  result: { status: string; refusal_reasons: string[]; [key: string]: unknown }
): string {
  const afterWords = checkReport(text, result.status, result.refusal_reasons);
  if (afterWords !== text) return afterWords;
  return checkLocators(text, collectKnownLocators(result), result.status, result.refusal_reasons);
}

function fallbackLine(status: string, refusalReasons: string[]): string {
  const reasons = refusalReasons.length ? refusalReasons.join("; ") : "No issues flagged.";
  return `Status: ${status}. ${reasons} See get_evidence for details.`;
}
