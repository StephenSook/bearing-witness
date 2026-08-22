"""Stage 1 — detect a persistent change against the asset's own early baseline.

Replay discipline: a window's state uses only windows pushed before or at it. The baseline is
the first `baseline_n` pushed windows. Nothing here knows what a bearing fault frequency is.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from statistics import median

from .dsp import robust_z
from .features import FEATURE_GROUPS, FEATURE_NAMES
from .thresholds import Thresholds


class Stage1State(str, Enum):
    BASELINE = "BASELINE"        # inside the baseline-accumulation period; not evaluated
    NORMAL = "NORMAL"            # no group moved
    WATCH = "WATCH"              # exactly one group moved, not an early-indicator-only pattern
    WATCH_EARLY = "WATCH_EARLY"  # one group moved and it is an early indicator (hf_band or envelope); two = fusion -> ABNORMAL
    ABNORMAL = "ABNORMAL"        # >= min_groups moved this window (persistence decided by the run)


@dataclass(frozen=True)
class Baseline:
    median: dict[str, float]
    mad: dict[str, float]
    windows: tuple[int, ...]


def fit_baseline(rows: list[dict[str, float]], windows: list[int]) -> Baseline:
    med, mad = {}, {}
    for n in FEATURE_NAMES:
        vals = [r[n] for r in rows]
        m = median(vals)
        med[n] = float(m)
        mad[n] = float(median([abs(v - m) for v in vals]))
    return Baseline(median=med, mad=mad, windows=tuple(windows))


def zscores(baseline: Baseline, feats: dict[str, float]) -> dict[str, float]:
    return {n: robust_z(feats[n], baseline.median[n], baseline.mad[n]) for n in FEATURE_NAMES}


def moved_groups(z: dict[str, float], th: Thresholds) -> list[str]:
    out = []
    for g, names in FEATURE_GROUPS.items():
        if th.one_sided:
            hit = any(z[n] >= th.z_thresh for n in names)
        else:
            hit = any(abs(z[n]) >= th.z_thresh for n in names)
        if hit:
            out.append(g)
    return out


def classify(moved: list[str], th: Thresholds) -> Stage1State:
    if len(moved) >= th.min_groups:
        return Stage1State.ABNORMAL
    if not moved:
        return Stage1State.NORMAL
    if set(moved) <= set(th.watch_early_groups):
        return Stage1State.WATCH_EARLY
    return Stage1State.WATCH


@dataclass
class Stage1Result:
    window: int
    state: Stage1State
    moved: list[str]
    z: dict[str, float]
    run_length: int
    onset_window: int | None

    @property
    def persistent(self) -> bool:
        return self.onset_window is not None


@dataclass
class ReplayDetector:
    th: Thresholds
    rows: list[dict[str, float]] = field(default_factory=list)
    windows: list[int] = field(default_factory=list)
    baseline: Baseline | None = None
    run: int = 0
    onset_window: int | None = None

    def push(self, window: int, feats: dict[str, float]) -> Stage1Result:
        self.rows.append(feats)
        self.windows.append(window)
        n = len(self.rows)
        if n < self.th.baseline_n:
            return Stage1Result(window, Stage1State.BASELINE, [], {}, 0, None)
        if n == self.th.baseline_n:
            self.baseline = fit_baseline(self.rows, self.windows)
            return Stage1Result(window, Stage1State.BASELINE, [], {}, 0, None)
        z = zscores(self.baseline, feats)
        moved = moved_groups(z, self.th)
        state = classify(moved, self.th)
        if state == Stage1State.ABNORMAL:
            self.run += 1
            if self.run >= self.th.persist and self.onset_window is None:
                self.onset_window = self.windows[-self.th.persist]
        else:
            self.run = 0
        return Stage1Result(window, state, moved, z, self.run, self.onset_window)
