"""Frozen evaluator v3 — all 15 XJTU-SY bearings, no exclusions, through the product Engine.

Usage: .venv/bin/python eval/run_eval.py [--root data/XJTU-SY_Bearing_Datasets]
Writes eval/results_v3.json and prints the summary table. Thresholds are read from the package and
their sha256 is embedded; if it differs from the one recorded in frozen_thresholds_v3.md's commit,
the run is not the frozen run.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bearing_witness.engine import Engine                      # noqa: E402
from bearing_witness.thresholds import THRESHOLDS, thresholds_sha256  # noqa: E402
from bearing_witness.trust import xjtu_context                # noqa: E402

EVAL = Path(__file__).resolve().parent
GT = json.loads((EVAL / "ground_truth.json").read_text())["bearings"]


def judge(documented: list[str], status: str, suspected: str | None, reasons: list[str], onset) -> str:
    if status == "ANALYST_REVIEW_REQUIRED":
        return "CORRECT" if suspected in documented else "WRONG"
    if status == "ABNORMAL_LOCATION_UNCONFIRMED":
        if "CAGE_CONSISTENT_NOT_CALLED" in reasons:
            return "CORRECT_CONSISTENT" if "cage" in documented else "WRONG_CONSISTENT"
        return "ABSTAIN"
    if onset is None:
        return "MISSED"
    return "OTHER"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(EVAL.parent / "data" / "XJTU-SY_Bearing_Datasets"))
    a = ap.parse_args()
    assert THRESHOLDS.VERSION == "v3", THRESHOLDS.VERSION
    sha = thresholds_sha256()
    t0 = time.time()
    results = {}
    for bearing, meta in GT.items():
        cond, nfiles = meta["condition"], meta["files"]
        tb = time.time()
        eng = Engine(xjtu_context(cond, bearing), Path(a.root) / cond / bearing, cache_dir=EVAL / "feature_cache")
        assert eng.n_records == nfiles, (bearing, eng.n_records, nfiles)
        r = eng.analyze(nfiles).result
        onset = r.anomaly_evidence.onset_window
        verdict = judge(meta["elements"], r.status, r.suspected_location, r.refusal_reasons, onset)
        results[bearing] = {
            "condition": cond, "files": nfiles, "documented": meta["elements"],
            "onset_window": onset, "lead_time_min": (nfiles - onset) if onset else None,
            "early_onset_inside_first_30pct": bool(onset and onset <= 0.3 * nfiles),
            "status": r.status, "suspected_location": r.suspected_location, "refusal_reasons": r.refusal_reasons,
            "view_a_supports": r.ordinary_spectrum_evidence.view_a_supports,
            "band": r.envelope_evidence.band_hz, "band_source": r.envelope_evidence.band_source,
            "families": {c.family: {"score_median": round(c.score_median, 2), "harm": c.harmonics_above_floor_median,
                                    "sb_pairs": c.sideband_pairs_median, "eligible": c.eligible, "f0": c.found_f0_hz,
                                    "excluded_hz": c.excluded_hz} for c in r.candidate_families},
            "verdict": verdict,
        }
        print(f"{bearing:12s} onset={str(onset):>5s} status={r.status:30s} loc={str(r.suspected_location):6s} "
              f"verdict={verdict:18s} reasons={','.join(r.refusal_reasons) or '-'} ({time.time()-tb:.0f}s)", flush=True)
    v = [x["verdict"] for x in results.values()]
    leads = [x["lead_time_min"] for x in results.values() if x["lead_time_min"] is not None]
    summary = {
        "correct": v.count("CORRECT"), "cage_consistent_correct": v.count("CORRECT_CONSISTENT"),
        "abstain": v.count("ABSTAIN"), "wrong": v.count("WRONG") + v.count("WRONG_CONSISTENT"),
        "missed": v.count("MISSED"), "other": v.count("OTHER"),
        "lead_min_median_max": [min(leads), int(np.median(leads)), max(leads)] if leads else None,
        "early_onset_first_30pct": sum(x["early_onset_inside_first_30pct"] for x in results.values()),
        "view_a_abstains": sum(1 for x in results.values() if any(s.startswith("VIEW_A_NO_SUPPORT") for s in x["refusal_reasons"])),
    }
    out = {"version": THRESHOLDS.VERSION, "thresholds_sha256": sha,
           "run_at": datetime.now(timezone.utc).isoformat(), "wall_s": round(time.time() - t0),
           "summary": summary, "results": results}
    (EVAL / "results_v3.json").write_text(json.dumps(out, indent=1, default=str))
    print("\n==== V3 SUMMARY (frozen before run, no exclusions) ====")
    for k_, val in summary.items():
        print(f"{k_:28s} {val}")
    print(f"thresholds sha256: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
