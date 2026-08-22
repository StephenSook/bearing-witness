"""CLI. This is what the OpenClaw skill shells out to on the box.

  python -m bearing_witness analyze --root data/XJTU-SY_Bearing_Datasets --condition 35Hz12kN --bearing Bearing1_3 --record 155
  python -m bearing_witness replay  --root ... --condition ... --bearing ... --to 158
  python -m bearing_witness decide  --root ... --condition ... --bearing ... --record 155 --decision APPROVE --reason "..."
  add --geometry-unverified / --speed-unverified to exercise the trust gate (demo step 7)

  decide re-runs the same deterministic analysis (there is no standalone case store
  outside Mongo) and applies the decision via JsonDecisionStore, printing the
  updated contract JSON. --decisions-path defaults to data/decisions.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import Engine
from .review import JsonDecisionStore, apply_decision
from .trust import with_unverified, xjtu_context


def _engine(a) -> Engine:
    ctx = xjtu_context(a.condition, a.bearing)
    if a.geometry_unverified:
        ctx = with_unverified(ctx, "geometry")
    if a.speed_unverified:
        ctx = with_unverified(ctx, "speed")
    return Engine(ctx, Path(a.root) / a.condition / a.bearing, cache_dir=a.cache_dir)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bearing_witness")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "replay", "decide"):
        s = sub.add_parser(name)
        s.add_argument("--root", required=True)
        s.add_argument("--condition", required=True)
        s.add_argument("--bearing", required=True)
        s.add_argument("--cache-dir", default=None)
        s.add_argument("--geometry-unverified", action="store_true")
        s.add_argument("--speed-unverified", action="store_true")
    sub.choices["analyze"].add_argument("--record", type=int, required=True)
    sub.choices["replay"].add_argument("--to", type=int, required=True)
    sub.choices["decide"].add_argument("--record", type=int, required=True)
    sub.choices["decide"].add_argument("--decision", choices=("APPROVE", "REJECT", "DEFER"), required=True)
    sub.choices["decide"].add_argument("--reason", required=True)
    sub.choices["decide"].add_argument("--decisions-path", default="data/decisions.json")
    a = p.parse_args(argv)
    eng = _engine(a)
    if a.cmd == "analyze":
        sys.stdout.write(eng.analyze(a.record).result.model_dump_json(indent=2) + "\n")
        return 0
    if a.cmd == "decide":
        result = eng.analyze(a.record).result
        store = JsonDecisionStore(a.decisions_path)
        updated = apply_decision(result, a.decision, a.reason, store)
        sys.stdout.write(updated.model_dump_json(indent=2) + "\n")
        return 0
    for k in range(1, a.to + 1):
        r = eng.analyze(k).result
        loc = r.suspected_location or "-"
        print(f"w{k} {r.status} state={r.anomaly_evidence.stage1_state} onset={r.anomaly_evidence.onset_window} "
              f"loc={loc} reasons={','.join(r.refusal_reasons) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
