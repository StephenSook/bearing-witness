const BANNED_ALWAYS = [/\breplace\b/i];
const BANNED_UNLESS_REVIEWED = [/\bconfirmed\b/i];
const REVIEWED_STATUSES = ["ANALYST_REVIEW_REQUIRED", "INSPECTION_APPROVED"];

export function checkReport(text: string, status: string, refusalReasons: string[]): string {
  const banned = BANNED_ALWAYS.concat(
    REVIEWED_STATUSES.includes(status) ? [] : BANNED_UNLESS_REVIEWED
  );
  if (banned.some((re) => re.test(text))) {
    return fallbackLine(status, refusalReasons);
  }
  return text;
}

function fallbackLine(status: string, refusalReasons: string[]): string {
  const reasons = refusalReasons.length ? refusalReasons.join("; ") : "No issues flagged.";
  return `Status: ${status}. ${reasons} See get_evidence for details.`;
}
