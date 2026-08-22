"""Engine — one asset, replay discipline, the status decision, and the contract.

analyze(k): window k sees only records 1..k. Features are cached per asset (CSV, same format as
eval/feature_cache). Stage 3 runs only after Stage 1 is persistent and trust allows localization.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .contract import (AnomalyEvidence, CandidateFamily, EnvelopeEvidence, HumanReview, InputTrust,
                       InspectionDraft, MachineComponents, OrdinarySpectrumEvidence, ResultContract,
                       SourceWindow, SpectrumPeak, locator)
from .data import Record, count_records, load_record
from .detect import ReplayDetector, Stage1Result, Stage1State
from .dsp import FAMILIES, FS, ordinary_spectrum
from .explain import ExplainResult, explain_ordinary, ordinary_supports
from .families import ELEMENT, WindowLocalization, aggregate, decide, localize_window
from .features import FEATURE_NAMES, compute_features
from .review import draft_task
from .thresholds import THRESHOLDS, Thresholds
from .trust import AssetContext, TrustLevel, TrustResult, evaluate_trust


class FeatureCache:
    """CSV with header 'window,<FEATURE_NAMES...>'. Same file format as prep eval_features/*.csv."""

    def __init__(self, path: Path | None):
        self.path = path
        self.rows: dict[int, dict[str, float]] = {}
        self._dirty = False
        if path is not None and path.exists():
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    self.rows[int(row["window"])] = {n: float(row[n]) for n in FEATURE_NAMES}

    def get(self, window: int) -> dict[str, float] | None:
        return self.rows.get(window)

    def put(self, window: int, feats: dict[str, float]) -> None:
        self.rows[window] = feats
        self._dirty = True

    def flush(self) -> None:
        if self.path is None or not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["window", *FEATURE_NAMES])
            for k in sorted(self.rows):
                w.writerow([k, *[self.rows[k][n] for n in FEATURE_NAMES]])
        self._dirty = False


@dataclass
class Analysis:
    result: ResultContract
    series: dict   # "ordinary": (freqs, amp) · "envelope": (freqs, amp)|None · "stage1": list[Stage1Result]


class Engine:
    def __init__(self, ctx: AssetContext, record_dir, th: Thresholds = THRESHOLDS,
                 cache_dir=None, fs: float = FS):
        self.ctx = ctx
        self.record_dir = Path(record_dir)
        self.th = th
        self.fs = fs
        self.n_records = count_records(self.record_dir)
        self.preds = ctx.fault_frequencies()
        self.cache = FeatureCache(Path(cache_dir) / f"{self.record_dir.name}.csv" if cache_dir else None)
        self._loc: dict[int, WindowLocalization] = {}

    # ---- inputs -------------------------------------------------------------------------------
    def _record(self, k: int, overrides: dict[int, np.ndarray]) -> Record:
        if k in overrides:
            return Record(index=k, path=str(self.record_dir / f"{k}.csv"), x=np.asarray(overrides[k], float),
                          fs=self.fs, sha256="INJECTED")
        return load_record(self.record_dir / f"{k}.csv", k, self.fs)

    def _features(self, k: int, overrides: dict[int, np.ndarray]) -> dict[str, float]:
        if k in overrides:
            return compute_features(overrides[k], self.fs)
        f = self.cache.get(k)
        if f is None:
            f = compute_features(self._record(k, {}).x, self.fs)
            self.cache.put(k, f)
        return f

    def _stage1_to(self, k: int, overrides: dict[int, np.ndarray]) -> tuple[ReplayDetector, list[Stage1Result]]:
        det = ReplayDetector(self.th)
        out = [det.push(w, self._features(w, overrides)) for w in range(1, k + 1)]
        return det, out

    def _localization(self, w: int, overrides: dict[int, np.ndarray]) -> WindowLocalization:
        if w in overrides:
            return localize_window(overrides[w], w, self.preds, self.ctx.speed.value_hz, self.th, self.fs)
        if w not in self._loc:
            self._loc[w] = localize_window(self._record(w, {}).x, w, self.preds, self.ctx.speed.value_hz, self.th, self.fs)
        return self._loc[w]

    # ---- main ---------------------------------------------------------------------------------
    def analyze(self, k: int, overrides: dict[int, np.ndarray] | None = None) -> Analysis:
        overrides = overrides or {}
        th = self.th
        rec = self._record(k, overrides)
        trust = evaluate_trust(self.ctx, rec)
        asset = self.ctx.asset_id
        sha = rec.sha256

        freqs_o, amp_o = ordinary_spectrum(rec.x, self.fs) if trust.signal_ok else (np.array([0.0]), np.array([0.0]))
        order_ok = trust.signal_ok and "ORDER_ANALYSIS" not in trust.blocks and "ALL" not in trust.blocks
        explain: ExplainResult | None = explain_ordinary(freqs_o, amp_o, self.ctx, th) if order_ok else None

        status = "BLOCKED_SIGNAL"
        reasons: list[str] = []
        suspected: str | None = None
        draft: InspectionDraft | None = None
        candidates: list[CandidateFamily] = []
        env_series = None
        view_a_family: str | None = None
        ordinary_peaks: list[SpectrumPeak] = []
        env_evidence = EnvelopeEvidence(band_hz=list(th.demod_band), band_source="fixed", sk=None, noise_floor=0.0,
                                        peaks=[], notes="envelope analysis not run for this window")
        stage1: list[Stage1Result] = []
        det: ReplayDetector | None = None
        s1: Stage1Result | None = None

        if not trust.signal_ok or "ALL" in trust.blocks:
            reasons = list(trust.notes)
            draft = draft_task("RECAPTURE_SIGNAL", asset, None, [])
        elif "BASELINE_COMPARISON" in trust.blocks:
            status = "BLOCKED_BASELINE"
            reasons = [n for n in trust.notes if "REGIME" in n] or ["REGIME_UNVERIFIED"]
            draft = draft_task("ANALYST_REVIEW", asset, None, [])
        else:
            det, stage1 = self._stage1_to(k, overrides)
            s1 = stage1[-1]
            if s1.state == Stage1State.BASELINE:
                status = "BLOCKED_BASELINE"
                reasons = [f"BASELINE_ACCUMULATING_{k}_OF_{th.baseline_n}"]
            elif not s1.persistent:
                if s1.state in (Stage1State.NORMAL, Stage1State.WATCH):
                    status = "NO_ANOMALY_DETECTED"
                    if s1.moved:
                        reasons = [f"SINGLE_GROUP_{s1.moved[0]}_NOT_FUSED"]
                else:
                    status = "WATCH_EARLY"
                    reasons = ([f"ABNORMAL_NOT_PERSISTENT_RUN_{s1.run_length}_OF_{th.persist}"]
                               if s1.state == Stage1State.ABNORMAL else [f"EARLY_INDICATORS_{'+'.join(s1.moved)}"])
            else:
                if "LOCALIZATION" in trust.blocks:
                    status = "ABNORMAL_LOCATION_UNCONFIRMED"
                    reasons = [f"LOCALIZATION_BLOCKED_{n}" for n in trust.notes]
                    draft = draft_task(trust.tasks[0], asset, None, [])
                else:
                    first = max(1, k - th.loc_last + 1)
                    locs = [self._localization(w, overrides) for w in range(first, k + 1)]
                    cur = locs[-1]
                    agg = aggregate(locs)
                    dec = decide(agg, th)
                    env_series = (cur.freqs, cur.amp)
                    env_peaks = [SpectrumPeak(freq_hz=h.freq_hz, amp=h.amp, label=f"{fam} h{h.k}",
                                              locator=locator(asset, k, sha, "envelope", h.freq_hz, k=h.k))
                                 for fam in FAMILIES for h in cur.scores[fam].harmonics if h.above_floor]
                    env_peaks += [SpectrumPeak(freq_hz=sb.lo_hz, amp=sb.lo_amp, label=f"{fam} h{sb.k} sb-1",
                                               locator=locator(asset, k, sha, "envelope", sb.lo_hz, k=sb.k, m=-1))
                                  for fam in FAMILIES for sb in cur.scores[fam].sidebands]
                    env_peaks += [SpectrumPeak(freq_hz=sb.hi_hz, amp=sb.hi_amp, label=f"{fam} h{sb.k} sb+1",
                                               locator=locator(asset, k, sha, "envelope", sb.hi_hz, k=sb.k, m=+1))
                                  for fam in FAMILIES for sb in cur.scores[fam].sidebands]
                    env_evidence = EnvelopeEvidence(
                        band_hz=list(cur.band), band_source=cur.band_source, sk=cur.sk, noise_floor=cur.noise,
                        peaks=env_peaks,
                        notes=f"median over windows {first}..{k}; band chosen by harmonic coherence (tie -> fixed 2-4 kHz)")
                    for fam in sorted(FAMILIES, key=lambda f: -agg[f].score):
                        fs_ = cur.scores[fam]
                        need = th.cage_min_harmonics if fam == "FTF" else th.margin_min_harmonics
                        candidates.append(CandidateFamily(
                            family=fam, element=ELEMENT[fam], predicted_hz=self.preds[fam], found_f0_hz=fs_.f0,
                            score_median=agg[fam].score, score_current=fs_.score,
                            harmonics_above_floor_median=agg[fam].harmonics,
                            sideband_pairs_median=agg[fam].sideband_pairs, eligible=agg[fam].harmonics >= need,
                            excluded_hz=list(fs_.excluded_hz),
                            locators=[locator(asset, k, sha, "envelope", h.freq_hz, k=h.k) for h in fs_.harmonics if h.above_floor]))
                    if dec.call.startswith("SUSPECTED_"):
                        f0 = cur.scores[dec.top].f0
                        va = ordinary_supports(freqs_o, amp_o, f0, explain.explained_hz, th)
                        ordinary_peaks = [SpectrumPeak(freq_hz=h.freq_hz, amp=h.amp, label=f"{dec.top} h{h.k} (ordinary)",
                                                       locator=locator(asset, k, sha, "ordinary", h.freq_hz, k=h.k))
                                          for h in va.harmonics]
                        if va.supported:
                            status = "ANALYST_REVIEW_REQUIRED"
                            suspected = ELEMENT[dec.top]
                            view_a_family = dec.top
                            evid = [c.locators for c in candidates if c.family == dec.top][0] + [p.locator for p in ordinary_peaks]
                            draft = draft_task("INSPECTION_WORK_ORDER", asset, suspected, evid)
                        else:
                            status = "ABNORMAL_LOCATION_UNCONFIRMED"
                            reasons = [f"VIEW_A_NO_SUPPORT_{dec.top}"]
                            draft = draft_task("ANALYST_REVIEW", asset, None, [])
                    elif dec.call == "CAGE_CONSISTENT":
                        status = "ABNORMAL_LOCATION_UNCONFIRMED"
                        reasons = ["CAGE_CONSISTENT_NOT_CALLED"]
                        draft = draft_task("ANALYST_REVIEW", asset, None, [])
                    else:
                        status = "ABNORMAL_LOCATION_UNCONFIRMED"
                        reasons = ["BEARING_PATTERN_LOCATION_UNCONFIRMED", *dec.reasons]
                        draft = draft_task("ANALYST_REVIEW", asset, None, [])

        # ---- contract ---------------------------------------------------------------------------
        feats = self._features(k, overrides) if trust.signal_ok else {}
        baseline = None
        if det is not None and det.baseline is not None:
            baseline = {"windows": list(det.baseline.windows), "median": det.baseline.median, "mad": det.baseline.mad}
        explained_peaks = [SpectrumPeak(freq_hz=p.freq_hz, amp=p.amp, label=p.label,
                                        locator=locator(asset, k, sha, "ordinary", p.freq_hz, k=p.order))
                           for p in (explain.peaks if explain else [])]
        result = ResultContract(
            analysis_id=f"{self.record_dir.name}-{k:04d}-{sha[:8]}",
            asset_id=asset,
            source_window=SourceWindow(record=k, file=rec.path, channel=rec.channel, n_samples=rec.n,
                                       fs_hz=rec.fs, duration_s=rec.duration_s, sha256=sha),
            input_trust=InputTrust(trust_level=trust.trust_level.value, signal_ok=trust.signal_ok,
                                   blocks=trust.blocks, tasks=trust.tasks,
                                   speed=self.ctx.speed.model_dump(mode="json"), geometry=self.ctx.geometry.model_dump(mode="json"),
                                   regime=self.ctx.regime.model_dump(mode="json"), acquisition=self.ctx.acquisition.model_dump(mode="json"),
                                   notes=trust.notes),
            anomaly_evidence=AnomalyEvidence(
                stage1_state=(s1.state.value if s1 else "BASELINE"), persistent=bool(s1 and s1.persistent),
                onset_window=(s1.onset_window if s1 else None), run_length=(s1.run_length if s1 else 0),
                moved_groups=(s1.moved if s1 else []), z=(s1.z if s1 else {}), features=feats, baseline=baseline,
                rule={"z_thresh": th.z_thresh, "one_sided": th.one_sided, "min_groups": th.min_groups,
                      "persist": th.persist, "baseline_n": th.baseline_n}),
            machine_components=MachineComponents(
                shaft_hz_nominal=self.ctx.speed.value_hz,
                shaft_hz_measured=(explain.shaft_hz_measured if explain else None),
                shaft_hz_used_for_prediction=self.ctx.speed.value_hz,
                bearing_model=self.ctx.geometry.model_number,
                geometry_verified=self.ctx.geometry.trust != TrustLevel.UNVERIFIED,
                predicted_hz=(self.preds if order_ok else {}), explained_peaks=explained_peaks),
            ordinary_spectrum_evidence=OrdinarySpectrumEvidence(
                max_hz=th.ordinary_max_hz, noise_floor=(explain.noise_floor if explain else 0.0),
                peaks=ordinary_peaks, view_a_supports=view_a_family,
                notes="machine components labelled before any bearing family is considered; measured shaft speed reported, not used"),
            envelope_evidence=env_evidence,
            candidate_families=candidates,
            suspected_location=suspected,
            status=status,
            refusal_reasons=reasons,
            inspection_draft=draft,
            human_review=HumanReview(required=(status == "ANALYST_REVIEW_REQUIRED")),
        )
        self.cache.flush()
        return Analysis(result=result, series={"ordinary": (freqs_o, amp_o), "envelope": env_series, "stage1": stage1})
