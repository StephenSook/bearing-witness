"""Audio beat prep (PLAN.md 2.10): two native-speed 1.28 s records, early vs late.

25.6 kHz sampling gives a 12.8 kHz Nyquist, so the raw samples become a WAV with
no pitch shift. Loudness is MEASURED, never ear-tested: each clip is gained to a
target integrated loudness via ffmpeg ebur128, the pair delta is bounded, and
`verify()` re-measures the SHIPPED files (the shipped-media rule). If the pair
cannot make the room speaker work on Saturday, the beat is cut without mourning.

Generate + gate: .venv-product/bin/python -m bw_product.audio
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .fixtures import FS, load_record

OUT_DIR = Path(__file__).parent / "fixtures_data"
TARGET_LUFS = -16.0
ACCEPT = (-18.0, -14.0)
MAX_PAIR_DELTA = 1.0
PEAK_CEILING = 0.89  # about -1 dBFS

# source records MUST match the labels every consumer prints (UI: "EARLY (W8)",
# report: "EARLY · WINDOW 8" / "LATE · WINDOW 155")
CLIPS = {"beat_early.wav": 8, "beat_late.wav": 155}


def _measure_lufs(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path), "-filter:a", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?\d+\.?\d*) LUFS", proc.stderr)
    if not m:
        raise RuntimeError(f"ebur128 gave no integrated loudness for {path}")
    return float(m[-1])


def _write(path: Path, x: np.ndarray) -> None:
    wavfile.write(path, int(FS), (np.clip(x, -1, 1) * 32767).astype(np.int16))


def generate(out_dir: Path = OUT_DIR) -> dict[str, float]:
    out_dir.mkdir(parents=True, exist_ok=True)
    gains: dict[str, np.ndarray] = {}
    for name, k in CLIPS.items():
        x, _ = load_record(k)
        x = x / np.max(np.abs(x))
        _write(out_dir / name, x * 0.5)               # provisional
        lufs = _measure_lufs(out_dir / name)
        gain_db = TARGET_LUFS - lufs
        gains[name] = x * 0.5 * (10 ** (gain_db / 20))
    # protect the ceiling with ONE shared reduction so the pair stays equal-loud
    peak = max(float(np.max(np.abs(g))) for g in gains.values())
    trim = min(1.0, PEAK_CEILING / peak)
    results = {}
    for name, g in gains.items():
        _write(out_dir / name, g * trim)
        results[name] = _measure_lufs(out_dir / name)
    (out_dir / "audio_loudness.json").write_text(json.dumps(results, indent=1))
    return results


def verify(out_dir: Path = OUT_DIR) -> dict[str, float]:
    """Re-measure the SHIPPED files; raise if the gate fails."""
    results = {name: _measure_lufs(out_dir / name) for name in CLIPS}
    values = list(results.values())
    for name, v in results.items():
        if not (ACCEPT[0] <= v <= ACCEPT[1]):
            raise AssertionError(f"{name} integrated loudness {v} outside {ACCEPT}")
    if abs(values[0] - values[1]) > MAX_PAIR_DELTA:
        raise AssertionError(f"pair delta {abs(values[0]-values[1]):.2f} LU > {MAX_PAIR_DELTA}")
    return results


if __name__ == "__main__":
    print("generated:", generate())
    print("verified:", verify())
