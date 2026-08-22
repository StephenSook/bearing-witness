import json
import subprocess
import sys

import numpy as np

from bearing_witness.dsp import FS, N_EXPECTED
from tests.synth import synth_fault, white

BPFO35 = 107.907


def _write(dirpath, k, x):
    dirpath.mkdir(parents=True, exist_ok=True)
    np.savetxt(dirpath / f"{k}.csv", np.column_stack([x, np.zeros_like(x)]), delimiter=",",
               header="Horizontal_vibration_signals,Vertical_vibration_signals", comments="")


def test_cli_analyze_prints_contract_json(tmp_path):
    d = tmp_path / "35Hz12kN" / "BearingC_1"
    for k in range(1, 13):
        _write(d, k, white(0.2, seed=k))
    out = subprocess.run([sys.executable, "-m", "bearing_witness", "analyze", "--root", str(tmp_path),
                          "--condition", "35Hz12kN", "--bearing", "BearingC_1", "--record", "12"],
                         capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["status"] in ("NO_ANOMALY_DETECTED", "WATCH_EARLY") and r["asset_id"] == "XJTU-SY/35Hz12kN/BearingC_1"
    assert r["suspected_location"] is None and r["candidate_families"] == []
    assert len(r) == 14


def test_cli_replay_prints_one_line_per_window(tmp_path):
    d = tmp_path / "35Hz12kN" / "BearingC_2"
    for k in range(1, 13):
        _write(d, k, white(0.2, seed=k))
    out = subprocess.run([sys.executable, "-m", "bearing_witness", "replay", "--root", str(tmp_path),
                          "--condition", "35Hz12kN", "--bearing", "BearingC_2", "--to", "12"],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()
    assert len(out) == 12 and out[0].startswith("w1 ") and "BLOCKED_BASELINE" in out[0]
    assert "onset=None" in out[-1] and "loc=-" in out[-1]


def _decidable_asset(tmp_path):
    d = tmp_path / "35Hz12kN" / "BearingC_3"
    t = np.arange(N_EXPECTED) / FS
    shaft = 0.3 * np.sin(2 * np.pi * 35.0 * t)
    for k in range(1, 15):
        _write(d, k, white(0.2, seed=k) + shaft)
    for k in range(15, 23):
        x = synth_fault(BPFO35, amp=2.0, noise=0.2, seed=k) + shaft
        x += 0.05 * np.sin(2 * np.pi * BPFO35 * t) + 0.03 * np.sin(2 * np.pi * 2 * BPFO35 * t)
        _write(d, k, x)
    return tmp_path


def _decide(tmp_path, decision, reason, decisions_path):
    return subprocess.run(
        [sys.executable, "-m", "bearing_witness", "decide", "--root", str(tmp_path),
         "--condition", "35Hz12kN", "--bearing", "BearingC_3", "--record", "22",
         "--decision", decision, "--reason", reason, "--decisions-path", str(decisions_path)],
        capture_output=True, text=True, check=True).stdout


def test_cli_decide_approves_and_records_to_decisions_path(tmp_path):
    root = _decidable_asset(tmp_path / "root")
    decisions_path = tmp_path / "decisions.json"
    out = _decide(root, "APPROVE", "pattern matches; schedule visual", decisions_path)
    r = json.loads(out)
    assert r["status"] == "INSPECTION_APPROVED" and r["human_review"]["decision"] == "APPROVE"
    assert r["inspection_draft"] is not None
    rows = json.loads(decisions_path.read_text())
    assert len(rows) == 1 and rows[0]["decision"] == "APPROVE" and rows[0]["analysis_id"] == r["analysis_id"]


def test_cli_decide_rejects_non_red_case(tmp_path):
    d = tmp_path / "root" / "35Hz12kN" / "BearingC_4"
    for k in range(1, 13):
        _write(d, k, white(0.2, seed=k))
    result = subprocess.run(
        [sys.executable, "-m", "bearing_witness", "decide", "--root", str(tmp_path / "root"),
         "--condition", "35Hz12kN", "--bearing", "BearingC_4", "--record", "12",
         "--decision", "APPROVE", "--reason", "x", "--decisions-path", str(tmp_path / "decisions.json")],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / "decisions.json").exists()
