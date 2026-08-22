"""Frozen evaluator v2 — see frozen_thresholds_v2.md. Reuses v1 feature cache."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bw_dsp as bw
import eval_harness as v1   # reuse: extract_features, stage1_replay, sk_winner_band, judge

S = os.path.dirname(os.path.abspath(__file__))
GT = json.load(open(os.path.join(S, "ground_truth.json")))["bearings"]
FAM_MAP = {"BPFO": "outer", "BPFI": "inner", "BSF2": "ball", "FTF": "cage"}

def family_scores_v2(x, band, preds):
    freqs, amp = bw.envelope_spectrum(x, band)
    noise = np.median(amp[(freqs > 5) & (freqs <= 500)])
    out = {}
    for fam, fpred in preds.items():
        cands = np.arange(fpred * (1 - v1.F0_REL), fpred * (1 + v1.F0_REL), bw.BIN_W / 2)
        best = (0.0, None, 0)
        for f0 in cands:
            s, nh = 0.0, 0
            for k in (1, 2, 3):
                hw = max(0.5 * bw.BIN_W, 0.015 * k * f0)      # v2 change 2
                m = (freqs >= k * f0 - hw) & (freqs <= k * f0 + hw)
                if m.any():
                    pk = amp[m].max()
                    s += pk
                    if pk >= 3 * noise:
                        nh += 1
            if s > best[0]:
                best = (s, f0, nh)
        out[fam] = {"score": float(best[0] / noise) if noise > 0 else 0.0,
                    "f0": best[1], "harm": best[2]}
    return out

def localize_v2(bearing, cond, nfiles, onset):
    f_shaft = bw.CONDITIONS[cond]
    preds = bw.fault_frequencies(f_shaft)
    d = os.path.join(v1.DATA, cond, bearing)
    per_window = []
    for i in range(max(1, nfiles - v1.LOC_LAST + 1), nfiles + 1):
        x = bw.load_h(os.path.join(d, f"{i}.csv"))
        band_sk, sk = v1.sk_winner_band(x)
        sc_sk = family_scores_v2(x, band_sk, preds)
        sc_fx = family_scores_v2(x, bw.DEMOD_BAND, preds)
        coh_sk = max(v["harm"] for v in sc_sk.values())
        coh_fx = max(v["harm"] for v in sc_fx.values())
        use_fixed = coh_fx >= coh_sk                          # v2 change 1 (tie -> fixed)
        sc = sc_fx if use_fixed else sc_sk
        per_window.append({"window": i, "band": list(bw.DEMOD_BAND) if use_fixed else list(band_sk),
                           "band_source": "fixed" if use_fixed else "sk",
                           "scores": {k: round(v["score"], 2) for k, v in sc.items()},
                           "harm": {k: v["harm"] for k, v in sc.items()}})
    med = {f: float(np.median([w["scores"][f] for w in per_window])) for f in preds}
    medh = {f: float(np.median([w["harm"][f] for w in per_window])) for f in preds}
    # margin competitor set — v2 change 3
    def eligible(f):
        return medh[f] >= (v1.CAGE_MIN_HARMONICS if f == "FTF" else 1)
    ranked = sorted(med.items(), key=lambda kv: -kv[1])
    top_fam, top = ranked[0][0], ranked[0][1]
    if not eligible(top_fam):
        return med, medh, per_window, "ABNORMAL_LOCATION_UNCONFIRMED", [f"TOP_{top_fam}_FAILS_COHERENCE"], top_fam
    comp = [s for f, s in ranked[1:] if eligible(f)]
    runner = max(comp) if comp else 0.0
    call, reasons = None, []
    if onset is None:
        call = "NO_ANOMALY_DETECTED"; reasons.append("STAGE1_NO_ONSET")
    elif top < v1.FAMILY_PRESENT:
        call = "ABNORMAL_LOCATION_UNCONFIRMED"; reasons.append(f"TOP_{top_fam}_{top:.1f}_BELOW_{v1.FAMILY_PRESENT}")
    elif runner > 0 and top < v1.MARGIN * runner:
        call = "ABNORMAL_LOCATION_UNCONFIRMED"; reasons.append(f"NO_MARGIN_{top_fam}_{top:.1f}_vs_{runner:.1f}")
    elif top_fam == "FTF":
        call = "CAGE_CONSISTENT"
    else:
        call = "SUSPECTED_" + FAM_MAP[top_fam].upper()
    return med, medh, per_window, call, reasons, top_fam

def main():
    t0 = time.time()
    results = {}
    for bearing, meta in GT.items():
        cond, nfiles = meta["condition"], meta["files"]
        df = v1.extract_features(bearing, cond, nfiles)          # cached from v1
        onset, ogroups, watch, isolated, _, _ = v1.stage1_replay(df)
        med, medh, pw, call, reasons, top = localize_v2(bearing, cond, nfiles, onset)
        verdict = v1.judge(bearing, call, top)
        results[bearing] = {
            "condition": cond, "files": nfiles, "documented": meta["elements"],
            "onset_window": onset, "lead_time_min": (nfiles - onset) if onset else None,
            "call": call, "call_reasons": reasons,
            "median_family_scores": {k: round(x, 2) for k, x in med.items()},
            "median_harmonics": medh, "verdict": verdict, "loc_detail": pw,
        }
        bands = [w["band_source"] for w in pw]
        print(f"{bearing:12s} onset={str(onset):>5s} call={call:32s} verdict={verdict:18s} "
              f"bands={'/'.join(bands)}", flush=True)
    json.dump(results, open(os.path.join(S, "eval_results_v2.json"), "w"), indent=1, default=str)
    v = [r["verdict"] for r in results.values()]
    print("\n==== V2 SUMMARY (frozen before run, no exclusions) ====")
    print(f"correct element calls:      {v.count('CORRECT')}")
    print(f"cage-consistent correct:    {v.count('CORRECT_CONSISTENT')}")
    print(f"abstained (unconfirmed):    {v.count('ABSTAIN')}")
    print(f"wrong element calls:        {v.count('WRONG') + v.count('WRONG_CONSISTENT')}")
    print(f"missed:                     {v.count('MISSED')}")
    print(f"wall: {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
