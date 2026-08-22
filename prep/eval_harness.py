"""PREP_PLAN item 5 — frozen evaluator across all 15 XJTU-SY bearings.

Implements frozen_thresholds.md EXACTLY. Thresholds were frozen before this run.
Not product code.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bw_dsp as bw

S = os.path.dirname(os.path.abspath(__file__))
DATA = "/Users/vinhle/NVIDIA-x-Dell/data/XJTU-SY_Bearing_Datasets"
FEAT_DIR = os.path.join(S, "eval_features")
os.makedirs(FEAT_DIR, exist_ok=True)

GT = json.load(open(os.path.join(S, "ground_truth.json")))["bearings"]

# ---- frozen constants (see frozen_thresholds.md) ----
Z_TH = 5.0
BASELINE_N = 10
PERSIST = 3
FAMILY_PRESENT = 9.0
MARGIN = 1.5
F0_REL = 0.025          # +/-2.5% fundamental search
HARM_HALF = 1.5         # Hz, per harmonic
LOC_LAST = 5            # median family score over last 5 windows
CAGE_MIN_HARMONICS = 3

def _feat_one(args):
    path, idx = args
    x = bw.load_h(path)
    f = bw.features(x)
    f["window"] = idx
    return f

def extract_features(bearing, cond, nfiles):
    cache = os.path.join(FEAT_DIR, f"{bearing}.csv")
    if os.path.exists(cache):
        df = pd.read_csv(cache, index_col="window")
        if len(df) == nfiles:
            return df
    d = os.path.join(DATA, cond, bearing)
    jobs = [(os.path.join(d, f"{i}.csv"), i) for i in range(1, nfiles + 1)]
    with Pool(processes=8) as p:
        rows = p.map(_feat_one, jobs, chunksize=8)
    df = pd.DataFrame(rows).set_index("window").sort_index()
    df.to_csv(cache)
    return df

def stage1_replay(df):
    """Frozen Stage-1: baseline win 1..10 median/MAD, |z|>=5, >=2 groups, 3 consecutive."""
    base = df.iloc[:BASELINE_N]
    med = base.median()
    mad = (base - med).abs().median()
    states = []          # per window: (abnormal_groups, watch_early)
    for _, row in df.iterrows():
        moved = set()
        for g, feats in bw.FEATURE_GROUPS.items():
            if any(abs(bw.robust_z(row[f], med[f], mad[f])) >= Z_TH for f in feats):
                moved.add(g)
        states.append(moved)
    onset = None
    run = 0
    for i, moved in enumerate(states):
        if len(moved) >= 2:
            run += 1
            if run >= PERSIST and onset is None:
                onset = i - PERSIST + 2  # window index (1-based) of first window of run
        else:
            run = 0
    watch_early = [i + 1 for i, m in enumerate(states)
                   if 0 < len(m) and m <= {"hf_band", "envelope"} and (onset is None or i + 1 < onset)]
    isolated = []
    run = 0
    for i, m in enumerate(states):
        if len(m) >= 2:
            run += 1
        else:
            if 0 < run < PERSIST and (onset is None or i + 1 <= onset):
                isolated.append(i + 1 - run)
            run = 0
    onset_groups = sorted(states[onset - 1]) if onset else []
    return onset, onset_groups, watch_early, isolated, med, mad

def sk_winner_band(x):
    """Compact kurtogram: SK = excess kurtosis of envelope of band-passed signal."""
    best, best_sk = None, -np.inf
    for bwidth in (4000.0, 2000.0, 1000.0):
        step = bwidth / 2
        lo = 1000.0
        while lo + bwidth <= 12200.0:
            hi = lo + bwidth
            try:
                env, _ = bw.envelope(x, (lo, hi))
                sk = bw.excess_kurtosis(env)
                if sk > best_sk:
                    best_sk, best = sk, (lo, hi)
            except Exception:
                pass
            lo += step
    return best, best_sk

def family_scores(x, band, preds):
    freqs, amp = bw.envelope_spectrum(x, band)
    noise = np.median(amp[(freqs > 5) & (freqs <= 500)])
    out = {}
    for fam, fpred in preds.items():
        f0_lo, f0_hi = fpred * (1 - F0_REL), fpred * (1 + F0_REL)
        cands = np.arange(f0_lo, f0_hi, bw.BIN_W / 2)
        best_score, best_f0, best_harm = 0.0, None, 0
        for f0 in cands:
            s, nh = 0.0, 0
            for k in (1, 2, 3):
                m = (freqs >= k * f0 - HARM_HALF) & (freqs <= k * f0 + HARM_HALF)
                if m.any():
                    pk = amp[m].max()
                    s += pk
                    if pk >= 3 * noise:
                        nh += 1
            if s > best_score:
                best_score, best_f0, best_harm = s, f0, nh
        out[fam] = {"score": float(best_score / noise) if noise > 0 else 0.0,
                    "f0": best_f0, "harmonics_above_3x": best_harm}
    return out

def localize(bearing, cond, nfiles, onset):
    """Frozen Stage-3: median family score over last LOC_LAST windows, SK winner band."""
    f_shaft = bw.CONDITIONS[cond]
    preds = bw.fault_frequencies(f_shaft)
    fam_map = {"BPFO": "outer", "BPFI": "inner", "BSF2": "ball", "FTF": "cage"}
    d = os.path.join(DATA, cond, bearing)
    per_window = []
    for i in range(max(1, nfiles - LOC_LAST + 1), nfiles + 1):
        x = bw.load_h(os.path.join(d, f"{i}.csv"))
        band, sk = sk_winner_band(x)
        scores_w = family_scores(x, band, preds)
        scores_f = family_scores(x, bw.DEMOD_BAND, preds)
        per_window.append({"window": i, "band": band, "sk": sk,
                           "winner_band_scores": {k: v["score"] for k, v in scores_w.items()},
                           "fixed_band_scores": {k: v["score"] for k, v in scores_f.items()},
                           "harmonics": {k: v["harmonics_above_3x"] for k, v in scores_w.items()}})
    med_scores = {fam: float(np.median([w["winner_band_scores"][fam] for w in per_window]))
                  for fam in preds}
    med_harm = {fam: float(np.median([w["harmonics"][fam] for w in per_window])) for fam in preds}
    ranked = sorted(med_scores.items(), key=lambda kv: -kv[1])
    top_fam, top_score = ranked[0]
    runner_score = ranked[1][1]
    call, reason = None, []
    if onset is None:
        call = "NO_ANOMALY_DETECTED"
        reason.append("STAGE1_NO_ONSET")
    elif top_score < FAMILY_PRESENT:
        call = "ABNORMAL_LOCATION_UNCONFIRMED"
        reason.append(f"TOP_FAMILY_{top_fam}_SCORE_{top_score:.1f}_BELOW_{FAMILY_PRESENT}")
    elif top_score < MARGIN * runner_score:
        call = "ABNORMAL_LOCATION_UNCONFIRMED"
        reason.append(f"NO_MARGIN_{top_fam}_{top_score:.1f}_vs_{ranked[1][0]}_{runner_score:.1f}")
    elif top_fam == "FTF":
        if med_harm["FTF"] >= CAGE_MIN_HARMONICS:
            call = "CAGE_CONSISTENT"       # never a confirmed element call
        else:
            call = "ABNORMAL_LOCATION_UNCONFIRMED"
            reason.append("FTF_TOP_BUT_INSUFFICIENT_HARMONICS")
    else:
        call = "SUSPECTED_" + fam_map[top_fam].upper()
    return {"median_scores": med_scores, "median_harmonics": med_harm,
            "call": call, "reasons": reason, "top": top_fam,
            "per_window": per_window}

def judge(bearing, call, top_fam):
    fam_map = {"BPFO": "outer", "BPFI": "inner", "BSF2": "ball", "FTF": "cage"}
    docs = GT[bearing]["elements"]
    if call.startswith("SUSPECTED_"):
        el = call.replace("SUSPECTED_", "").lower()
        return "CORRECT" if el in docs else "WRONG"
    if call == "CAGE_CONSISTENT":
        return "CORRECT_CONSISTENT" if "cage" in docs else "WRONG_CONSISTENT"
    if call == "ABNORMAL_LOCATION_UNCONFIRMED":
        return "ABSTAIN"
    if call == "NO_ANOMALY_DETECTED":
        return "MISSED" 
    return "OTHER"

def main():
    t0 = time.time()
    results = {}
    for bearing, meta in GT.items():
        cond, nfiles = meta["condition"], meta["files"]
        tb = time.time()
        df = extract_features(bearing, cond, nfiles)
        onset, ogroups, watch, isolated, med, mad = stage1_replay(df)
        loc = localize(bearing, cond, nfiles, onset)
        verdict = judge(bearing, loc["call"], loc["top"])
        lead = (nfiles - onset) if onset else None
        early_alarm = bool(onset and onset <= 0.3 * nfiles)
        results[bearing] = {
            "condition": cond, "files": nfiles, "documented": meta["elements"],
            "onset_window": onset, "onset_groups": ogroups,
            "lead_time_min": lead, "watch_early_count": len(watch),
            "isolated_abnormal_before_onset": isolated,
            "early_onset_inside_first_30pct": early_alarm,
            "call": loc["call"], "call_reasons": loc["reasons"],
            "median_family_scores": {k: round(v, 2) for k, v in loc["median_scores"].items()},
            "median_harmonics_above_3x": loc["median_harmonics"],
            "verdict": verdict,
            "loc_detail": loc["per_window"],
        }
        print(f"{bearing:12s} onset={str(onset):>5s} lead={str(lead):>5s} "
              f"call={loc['call']:32s} verdict={verdict:18s} ({time.time()-tb:.0f}s)", flush=True)
    with open(os.path.join(S, "eval_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    n = len(results)
    v = [r["verdict"] for r in results.values()]
    print("\n==== SUMMARY (frozen thresholds, no exclusions) ====")
    print(f"bearings: {n}")
    print(f"correct element calls:      {v.count('CORRECT')}")
    print(f"cage-consistent correct:    {v.count('CORRECT_CONSISTENT')}")
    print(f"abstained (unconfirmed):    {v.count('ABSTAIN')}")
    print(f"wrong element calls:        {v.count('WRONG') + v.count('WRONG_CONSISTENT')}")
    print(f"missed (no stage-1 onset):  {v.count('MISSED')}")
    leads = [r["lead_time_min"] for r in results.values() if r["lead_time_min"] is not None]
    print(f"lead time min/median/max:   {min(leads)}/{int(np.median(leads))}/{max(leads)} min")
    print(f"early-onset (first 30%):    {sum(r['early_onset_inside_first_30pct'] for r in results.values())}")
    print(f"total wall time: {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
