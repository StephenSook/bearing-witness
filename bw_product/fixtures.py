"""Real-data fixtures for the product loop (PLAN.md 2.8's development side).

Reads Bearing1_3 (35Hz12kN) directly from the offline kit (read-only) and emits
contract-shaped JSON + display series computed live from the raw CSVs. Nothing here
is a diagnostic claim: the engine lane owns diagnosis. These are display fixtures
whose numbers are honestly computed from the named source files, carried with
sha256 provenance, so the UI never renders an invented value.

Regenerate: .venv-product/bin/python -m bw_product.fixtures
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

from .contract_shape import empty_contract, locator, validate_shape

FS = 25600.0
N = 32768
CONDITION = "35Hz12kN"
BEARING = "Bearing1_3"
ASSET_ID = f"XJTU-SY/{CONDITION}/{BEARING}"
SHAFT_HZ_SETPOINT = 35.0

# PREP_PLAN verified predictions (hand-checked against LDK UER204 geometry)
PREDICTED_HZ = {"BPFO": 107.907, "BPFI": 172.093, "BSF2": 144.660, "FTF": 13.488}

# Frozen v3 thresholds, TRANSCRIBED from bearing_witness/thresholds.py (engine lane,
# landed 2026-08-21 commit 65f0478). Integration protocol: no cross-lane import before
# the 2.8 wiring gate; the seam test validates these fixtures against the real
# ResultContract instead. If the engine's freeze changes, this block changes with it.
ENV_NOISE_BAND = (5.0, 500.0)   # envelope noise floor = median amplitude in this band
F0_REL = 0.025                  # fundamental search: ±2.5% of prediction
HARM_REL = 0.015                # harmonic h half-width = max(0.5*bin, 0.015*h*f0)
HARM_SNR = 3.0                  # harmonic "above floor" iff amp >= 3x noise floor
ORD_LOCAL_SPAN = 20.0           # View A local noise: median amplitude within ±20 Hz
ORD_SNR = 3.0                   # View A peak counts iff amp >= 3x local noise
ELEMENT_MIN_HARMONICS = 3       # v3 harmonic floor: any element call needs >= 3
LOC_LAST = 5                    # family medians run over the last 5 windows
RULE_V3 = {"z_thresh": 5.0, "one_sided": True, "min_groups": 2, "persist": 3,
           "baseline_n": 10}

GEOMETRY = {
    "bearing_model": "LDK UER204", "n_balls": 8, "ball_diameter_mm": 7.92,
    "pitch_diameter_mm": 34.55, "contact_angle_deg": 0.0,
    "provenance": ("Wang, Lei, Li, Li, IEEE Trans. Reliability 69(1), 2020, "
                   "DOI 10.1109/TR.2018.2882682; Zhang et al., Entropy 25(5):737, 2023, Table 2"),
}

_DEFAULT_ROOTS = (
    Path("/Volumes/BWITNESS/BEARING_WITNESS_OFFLINE_KIT/03_DATASETS/XJTU-SY/extracted/XJTU-SY_Bearing_Datasets"),
    Path("data/XJTU-SY_Bearing_Datasets"),
)

OUT_DIR = Path(__file__).parent / "fixtures_data"


def data_root() -> Path:
    env = os.environ.get("BW_DATA_ROOT")
    candidates = (Path(env),) + _DEFAULT_ROOTS if env else _DEFAULT_ROOTS
    for root in candidates:
        if (root / CONDITION / BEARING).is_dir():
            return root
    raise FileNotFoundError(f"XJTU-SY corpus not found in {candidates}")


def record_path(k: int) -> Path:
    return data_root() / CONDITION / BEARING / f"{k}.csv"


def load_record(k: int) -> tuple[np.ndarray, str]:
    p = record_path(k)
    x = np.loadtxt(p, delimiter=",", skiprows=1, usecols=0)
    return x, hashlib.sha256(p.read_bytes()).hexdigest()


# --- display DSP (band choice per PREP_PLAN: 2-4 kHz fallback band) ------------

def ordinary_spectrum(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w = np.hanning(len(x))
    amp = np.abs(np.fft.rfft((x - x.mean()) * w)) * 2 / w.sum()
    freqs = np.fft.rfftfreq(len(x), 1 / FS)
    return freqs, amp


def envelope_spectrum(x: np.ndarray, lo: float = 2000.0, hi: float = 4000.0,
                      fmax: float = 500.0) -> tuple[np.ndarray, np.ndarray]:
    sos = butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
    xb = sosfiltfilt(sos, x - x.mean())
    env = np.abs(hilbert(xb)) ** 2
    env -= env.mean()
    amp = np.abs(np.fft.rfft(env)) * 2 / len(env)
    freqs = np.fft.rfftfreq(len(env), 1 / FS)
    keep = freqs <= fmax
    return freqs[keep], amp[keep]


def features(x: np.ndarray) -> dict[str, float]:
    rms = float(np.sqrt(np.mean(x ** 2)))
    p2p = float(x.max() - x.min())
    kurt = float(np.mean(((x - x.mean()) / x.std()) ** 4) - 3.0)
    f, a = ordinary_spectrum(x)
    hf = float(np.sum(a[(f >= 2000) & (f < 4000)] ** 2))
    _, ea = envelope_spectrum(x)
    return {"rms": rms, "p2p": p2p, "crest": float(np.max(np.abs(x)) / rms),
            "kurtosis_excess": kurt, "be_2000_4000": hf, "env_energy": float(np.sum(ea ** 2))}


def _peak_near(freqs: np.ndarray, amp: np.ndarray, target: float, half_width: float) -> tuple[float, float]:
    m = (freqs >= target - half_width) & (freqs <= target + half_width)
    i = int(np.argmax(amp[m]))
    return float(freqs[m][i]), float(amp[m][i])


def _band_noise(freqs: np.ndarray, amp: np.ndarray, lo: float, hi: float) -> float:
    sub = amp[(freqs >= lo) & (freqs <= hi)]
    return float(np.median(sub[sub > 0]))


def _bpfo_harmonics(freqs: np.ndarray, amp: np.ndarray) -> list[tuple[int, float, float]]:
    """Measured (h, freq, amp) for BPFO h1-h3 under the frozen v3 search widths:
    fundamental at prediction ±2.5%, harmonics at h*f0_measured ± max(bin/2, 1.5%*h*f0)."""
    f0_pred = PREDICTED_HZ["BPFO"]
    f0, a0 = _peak_near(freqs, amp, f0_pred, F0_REL * f0_pred)
    out = [(1, f0, a0)]
    for h in (2, 3):
        half = max(0.5 * (FS / N), HARM_REL * h * f0)
        f_m, a_m = _peak_near(freqs, amp, h * f0, half)
        out.append((h, f_m, a_m))
    return out


def _env_family_stats(x: np.ndarray) -> tuple[float, float, int]:
    """(noise, score, n_above) for the BPFO family in one window's envelope
    spectrum, per frozen v3: score = sum(amp/noise) over h1-h3, above at 3x."""
    fe, ae = envelope_spectrum(x)
    noise = _band_noise(fe, ae, *ENV_NOISE_BAND)
    harmonics = _bpfo_harmonics(fe, ae)
    score = sum(a / noise for _, _, a in harmonics)
    n_above = sum(1 for _, _, a in harmonics if a >= HARM_SNR * noise)
    return noise, score, n_above


_baseline_cache: dict | None = None


def _baseline_stats() -> dict:
    """Measured baseline over the first 10 chronological windows (v3 baseline_n):
    per-feature median and MAD, the shape the contract's AnomalyEvidence carries."""
    global _baseline_cache
    if _baseline_cache is None:
        rows = [features(load_record(k)[0]) for k in range(1, RULE_V3["baseline_n"] + 1)]
        med = {key: float(np.median([r[key] for r in rows])) for key in rows[0]}
        mad = {key: float(np.median([abs(r[key] - med[key]) for r in rows])) for key in rows[0]}
        _baseline_cache = {"windows": list(range(1, RULE_V3["baseline_n"] + 1)),
                           "median": med, "mad": mad}
    return json.loads(json.dumps(_baseline_cache))


def _series(x: np.ndarray) -> dict:
    fo, ao = ordinary_spectrum(x)
    fe, ae = envelope_spectrum(x)
    return {
        "ordinary": [fo[::4].round(3).tolist(), ao[::4].round(5).tolist()],
        "envelope": [fe.round(3).tolist(), ae.round(5).tolist()],
    }


def _trend(windows: list[int]) -> dict:
    rows = {}
    for k in windows:
        x, _ = load_record(k)
        rows[k] = features(x)
    keys = list(next(iter(rows.values())).keys())
    return {"windows": windows, **{key: [rows[k][key] for k in windows] for key in keys}}


def _base(k: int, x: np.ndarray, sha: str, geometry_verified: bool = True) -> dict:
    r = empty_contract()
    r["analysis_id"] = f"{BEARING}-{k:04d}-{sha[:8]}"
    r["asset_id"] = ASSET_ID
    r["source_window"] = {"record": k, "file": f"{CONDITION}/{BEARING}/{k}.csv",
                          "channel": "horizontal", "n_samples": int(len(x)), "fs_hz": FS,
                          "duration_s": round(len(x) / FS, 4), "sha256": sha}
    r["input_trust"] = {
        "trust_level": "TRUSTED_FOR_REPLAY", "signal_ok": True, "blocks": [], "tasks": [],
        "speed": {"source": "dataset setpoint", "value_hz": SHAFT_HZ_SETPOINT,
                  "note": "documented setpoint, not per-window telemetry; measured 1x runs ~0.8-1.5% low (~34.7 Hz)"},
        "geometry": {**GEOMETRY, "verified": geometry_verified},
        "regime": {"condition": CONDITION, "load_kN": 12.0},
        "acquisition": {"fs_hz": FS, "n_samples": N, "records_per_minute": 1},
        "notes": ["chronological replay of real XJTU-SY measurements"],
    }
    r["machine_components"] = {
        "shaft_hz_nominal": SHAFT_HZ_SETPOINT, "shaft_hz_measured": None,
        "shaft_hz_used_for_prediction": SHAFT_HZ_SETPOINT,
        "bearing_model": GEOMETRY["bearing_model"], "geometry_verified": geometry_verified,
        "predicted_hz": PREDICTED_HZ, "explained_peaks": [],
    }
    return r


def build_green(k: int = 11) -> tuple[dict, dict]:
    """W11: the first judged window AFTER the 10-window baseline. Verified
    against the live engine 2026-08-22: `analyze --record 11` returns
    NO_ANOMALY_DETECTED / stage1 NORMAL (W8 would be BLOCKED_BASELINE: the
    engine refuses to judge while learning, and the fixture must tell the same
    story the engine tells)."""
    x, sha = load_record(k)
    r = _base(k, x, sha)
    r["status"] = "NO_ANOMALY_DETECTED"
    r["anomaly_evidence"] = {"stage1_state": "NORMAL", "persistent": False,
                             "onset_window": None, "run_length": 0, "moved_groups": [],
                             "z": {}, "features": features(x), "baseline": _baseline_stats(),
                             "rule": {**RULE_V3,
                                      "note": "first judged window after the baseline"}}
    return r, _series(x)


def build_yellow(k: int = 60) -> tuple[dict, dict]:
    """W60: the second abnormal window, NOT yet persistent (v3 persist=3), so
    WATCH_EARLY. Verified against the live engine 2026-08-22: W59-60 =
    WATCH_EARLY persistent=False; by W61 persistence lands and the engine moves
    on. W62's old fixture claimed WATCH_EARLY+persistent, a pair the engine
    never emits."""
    x, sha = load_record(k)
    r = _base(k, x, sha)
    r["status"] = "WATCH_EARLY"
    r["anomaly_evidence"] = {"stage1_state": "ABNORMAL", "persistent": False,
                             "onset_window": None, "run_length": 2,
                             "moved_groups": ["energy", "hf_band"], "z": {},
                             "features": features(x), "baseline": _baseline_stats(),
                             "rule": {**RULE_V3,
                                      "note": "abnormal, not yet persistent: keep trending"}}
    r["refusal_reasons"] = ["single-view evidence only; keep trending"]
    return r, _series(x)


def build_red(k: int = 155) -> tuple[dict, dict]:
    x, sha = load_record(k)
    r = _base(k, x, sha)
    bpfo = PREDICTED_HZ["BPFO"]

    # View B (envelope): measured BPFO harmonics under the frozen v3 widths/floor
    fe, ae = envelope_spectrum(x)
    noise, score_current, n_above = _env_family_stats(x)
    env_harmonics = _bpfo_harmonics(fe, ae)
    peaks, locs = [], []
    for h, f_m, a_m in env_harmonics:
        loc = locator(ASSET_ID, k, sha, "envelope", f_m, h)
        peaks.append({"freq_hz": round(f_m, 3), "amp": round(a_m, 5),
                      "label": f"BPFO h{h}", "locator": loc, "harmonic": h})
        locs.append(loc)

    # family medians per frozen v3: over the last LOC_LAST windows (<= current)
    per_window = [_env_family_stats(load_record(w)[0]) for w in range(k - LOC_LAST + 1, k + 1)]
    score_median = float(np.median([s for _, s, _ in per_window]))
    harmonics_median = float(np.median([n for _, _, n in per_window]))

    r["status"] = "ANALYST_REVIEW_REQUIRED"
    r["suspected_location"] = "outer"
    r["anomaly_evidence"] = {"stage1_state": "ABNORMAL", "persistent": True,
                             "onset_window": 59, "run_length": k - 59 + 1,
                             "moved_groups": ["energy", "hf_band", "shape"], "z": {},
                             "features": features(x), "baseline": _baseline_stats(),
                             "rule": {**RULE_V3,
                                      "note": "fixture: late-life window, outer-race family visible"}}
    r["envelope_evidence"] = {"band_hz": [2000.0, 4000.0], "band_source": "fixed",
                              "sk": None, "noise_floor": round(noise, 6), "peaks": peaks,
                              "notes": ("2-4 kHz demod band per prep; harmonics measured from "
                                        "this file under the frozen v3 widths and 3x floor")}

    # View A (ordinary spectrum): measured corroboration under the frozen v3 rule,
    # each peak against its LOCAL noise (median amplitude within ±20 Hz)
    fo, ao = ordinary_spectrum(x)
    o_noise_global = _band_noise(fo, ao, 5.0, 1000.0)
    o_peaks, o_above = [], 0
    for h, f_env, _ in env_harmonics:
        half = max(0.5 * (FS / N), HARM_REL * h * env_harmonics[0][1])
        f_m, a_m = _peak_near(fo, ao, h * env_harmonics[0][1], half)
        local = _band_noise(fo, ao, f_m - ORD_LOCAL_SPAN, f_m + ORD_LOCAL_SPAN)
        above = a_m >= ORD_SNR * local
        o_above += int(above)
        o_peaks.append({"freq_hz": round(f_m, 3), "amp": round(a_m, 5),
                        "label": f"BPFO h{h}", "harmonic": h,
                        "locator": locator(ASSET_ID, k, sha, "ordinary", f_m, h)})
    view_a_supports = "BPFO" if o_above == len(env_harmonics) else None
    r["ordinary_spectrum_evidence"] = {
        "max_hz": float(fo[-1]), "noise_floor": round(o_noise_global, 6),
        "peaks": o_peaks, "view_a_supports": view_a_supports,
        "notes": ("measured from this file: BPFO harmonics each >= 3x their local "
                  "(±20 Hz) median floor; the engine's View-A gate replaces this when wired")}

    # this builder CLAIMS a two-view red state; it does not decide it (the engine
    # owns diagnosis, D2). So it must refuse to emit the claim when its own
    # measurements do not back it: a red fixture built from an unsupporting
    # window is fabricated evidence, and generation fails loudly instead.
    # "Two views agree" additionally requires the two views to find the SAME
    # fundamental (within one FFT bin), not merely any in-band peaks above floor.
    fundamentals_agree = abs(o_peaks[0]["freq_hz"] - peaks[0]["freq_hz"]) <= FS / N
    if view_a_supports is None or n_above < ELEMENT_MIN_HARMONICS or not fundamentals_agree:
        raise ValueError(
            f"red fixture for window {k} not supported by measurement "
            f"(view_a_supports={view_a_supports}, harmonics_above_floor={n_above}, "
            f"fundamentals_agree={fundamentals_agree}); "
            "pick a window whose data backs the claim or build a non-red fixture")
    r["candidate_families"] = [{
        "family": "BPFO", "element": "outer", "predicted_hz": bpfo,
        "found_f0_hz": peaks[0]["freq_hz"],
        "score_median": round(score_median, 2), "score_current": round(score_current, 2),
        "harmonics_above_floor_median": harmonics_median,
        # v3 sideband table defines spacings for BPFI (shaft) and BSF2 (FTF) only;
        # BPFO (stationary outer race) has none, so the measured count is 0
        "sideband_pairs_median": 0.0,
        "eligible": harmonics_median >= ELEMENT_MIN_HARMONICS,
        "excluded_hz": [], "locators": locs,
    }]
    r["inspection_draft"] = {
        "task_type": "INSPECTION_WORK_ORDER",
        "title": f"Inspect outer race, {BEARING}",
        "asset_id": ASSET_ID, "suspected_element": "outer",
        "evidence_locators": locs,
        "recommended_action": "Schedule a visual inspection of the outer race; correlate with the trend evidence before any intervention.",
        "not_claimed": ["RUL", "severity grading", "root cause"],
    }
    r["human_review"] = {"required": True, "decision": None, "reason": None, "timestamp": None}
    return r, _series(x)


def build_refusal(k: int = 155) -> tuple[dict, dict]:
    """Demo step 7: same waveform, geometry unverified -> localization refuses."""
    x, sha = load_record(k)
    r = _base(k, x, sha, geometry_verified=False)
    r["analysis_id"] += "-unverified"
    r["status"] = "ABNORMAL_LOCATION_UNCONFIRMED"
    r["anomaly_evidence"] = {"stage1_state": "ABNORMAL", "persistent": True,
                             "onset_window": 59, "run_length": k - 59 + 1,
                             "moved_groups": ["energy", "hf_band", "shape"], "z": {},
                             "features": features(x), "baseline": _baseline_stats(),
                             "rule": {**RULE_V3,
                                      "note": "detector unchanged; localization blocked by trust gate"}}
    # aligned to the LIVE engine's refusal output (verified 2026-08-22:
    # analyze --geometry-unverified): trust_level UNVERIFIED, block LOCALIZATION,
    # machine reason string. The '-unverified' id suffix stays DELIBERATELY
    # (engine ids do not encode trust, so without it this fixture would collide
    # with the trusted red case; reported to the engine lane).
    r["input_trust"]["trust_level"] = "UNVERIFIED"
    r["input_trust"]["blocks"] = ["LOCALIZATION"]
    r["input_trust"]["tasks"] = ["VERIFY_BEARING_GEOMETRY"]
    r["refusal_reasons"] = ["LOCALIZATION_BLOCKED_GEOMETRY_UNVERIFIED"]
    r["inspection_draft"] = {
        "task_type": "VERIFY_BEARING_GEOMETRY",
        "title": f"Verify installed bearing geometry, {BEARING}",
        "asset_id": ASSET_ID, "suspected_element": None,
        "evidence_locators": [locator(ASSET_ID, k, sha, "envelope", PREDICTED_HZ["BPFO"], 1)],
        "recommended_action": "Confirm the installed bearing's internal geometry and provenance, then re-run localization.",
        "not_claimed": ["element call without verified geometry"],
    }
    # engine truth: a refusal is not awaiting a human decision; the remediation
    # task is the output (verified live 2026-08-22: required=False)
    r["human_review"] = {"required": False, "decision": None, "reason": None, "timestamp": None}
    return r, _series(x)


def generate(out_dir: Path = OUT_DIR) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # every scenario window MUST be present so the chart marker never has to
    # substitute a neighbor; baseline 1-10 dense so the green screen has a real region
    trend_windows = sorted(set(range(1, 159, 4)) | set(range(1, 12))
                           | set(range(50, 71)) | set(range(148, 159)) | {11, 60, 155})
    written: dict[str, Path] = {}
    for name, (result, series) in {
        "green": build_green(), "yellow": build_yellow(),
        "red": build_red(), "refusal": build_refusal(),
    }.items():
        problems = validate_shape(result)
        if problems:
            raise ValueError(f"fixture {name} does not conform: {problems}")
        p = out_dir / f"fixture_{name}.json"
        p.write_text(json.dumps({"result": result, "series": series}, indent=1))
        written[name] = p
    t = out_dir / "trend.json"
    t.write_text(json.dumps(_trend(trend_windows)))
    written["trend"] = t
    return written


if __name__ == "__main__":
    for name, path in generate().items():
        print(f"{name}: {path} ({path.stat().st_size // 1024} KB)")
