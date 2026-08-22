import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

const run = promisify(execFile);

// Flip this to false once data/ is populated and Vinh's CLI is confirmed working
const USE_MOCK = true;

const ROOT = "data/XJTU-SY_Bearing_Datasets";
const CACHE = "eval/feature_cache";
const FIXTURES_DIR = join(__dirname, "fixtures");

async function loadFixture(name: string) {
  const raw = await readFile(join(FIXTURES_DIR, `${name}.json`), "utf-8");
  return JSON.parse(raw);
}

// picks a fixture based on record number so different windows return
// different statuses while testing, roughly matching the real detector's shape
function fixtureForRecord(record: number): string {
  if (record < 50) return "no_anomaly";
  if (record < 100) return "unconfirmed";
  return "analyst_review_required";
}

export async function analyze(
  condition: string,
  bearing: string,
  record: number,
  opts: { geometryUnverified?: boolean; speedUnverified?: boolean } = {}
) {
  if (USE_MOCK) {
    return loadFixture(fixtureForRecord(record));
  }
  const args = [
    "-m", "bearing_witness", "analyze",
    "--root", ROOT,
    "--condition", condition,
    "--bearing", bearing,
    "--record", String(record),
    "--cache-dir", CACHE,
  ];
  if (opts.geometryUnverified) args.push("--geometry-unverified");
  if (opts.speedUnverified) args.push("--speed-unverified");
  const { stdout } = await run(".venv/bin/python", args);
  return JSON.parse(stdout);
}

export async function decide(
  condition: string,
  bearing: string,
  record: number,
  decision: "APPROVE" | "REJECT" | "DEFER",
  reason: string
) {
  if (USE_MOCK) {
    const analysisId = `${bearing}-${String(record).padStart(4, "0")}-mock0000`;
    const status = decision === "APPROVE" ? "INSPECTION_APPROVED"
      : decision === "REJECT" ? "INSPECTION_REJECTED"
      : "ANALYST_REVIEW_REQUIRED";
    return {
      analysis_id: analysisId,
      status,
      human_review: { required: true, decision, reason, timestamp: new Date().toISOString() },
    };
  }
  const { stdout } = await run(".venv/bin/python", [
    "-m", "bearing_witness", "decide",
    "--root", ROOT,
    "--condition", condition,
    "--bearing", bearing,
    "--record", String(record),
    "--decision", decision,
    "--reason", reason,
    "--cache-dir", CACHE,
  ]);
  return JSON.parse(stdout);
}

export async function replay(condition: string, bearing: string, to: number) {
  if (USE_MOCK) {
    const statuses = ["NO_ANOMALY_DETECTED", "WATCH_EARLY", "ABNORMAL_LOCATION_UNCONFIRMED", "ANALYST_REVIEW_REQUIRED"];
    return Array.from({ length: to }, (_, i) => {
      const w = i + 1;
      const status = statuses[Math.min(3, Math.floor((w / to) * 4))];
      return `w${w} ${status} state=ABNORMAL onset=${w > to * 0.6 ? Math.floor(to * 0.6) : "None"} loc=- reasons=-`;
    });
  }
  const { stdout } = await run(".venv/bin/python", [
    "-m", "bearing_witness", "replay",
    "--root", ROOT, "--condition", condition, "--bearing", bearing, "--to", String(to),
  ]);
  return stdout.trim().split("\n");
}
