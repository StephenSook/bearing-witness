import numpy as np
import pytest

from bearing_witness import detect, features
from bearing_witness.thresholds import THRESHOLDS as TH
from tests.synth import tones, white


def _row(seed, **over):
    rng = np.random.default_rng(seed)
    r = {n: 1.0 + 0.01 * rng.normal() for n in features.FEATURE_NAMES}
    r.update(over)
    return r


def _replay(rows):
    det = detect.ReplayDetector(TH)
    return det, [det.push(i + 1, r) for i, r in enumerate(rows)]


def test_baseline_windows_are_not_evaluated():
    det, res = _replay([_row(i) for i in range(10)])
    assert all(r.state == detect.Stage1State.BASELINE for r in res)
    assert det.baseline is not None and det.baseline.windows == tuple(range(1, 11))
    assert det.onset_window is None


def test_onset_needs_two_groups_and_three_consecutive_windows():
    rows = [_row(i) for i in range(10)]
    rows += [_row(20 + i) for i in range(5)]                                   # 11..15 normal
    rows += [_row(30, rms=10.0, p2p=10.0, env_energy=10.0)]                    # 16 abnormal (energy+envelope)
    rows += [_row(31)]                                                         # 17 normal -> run resets
    rows += [_row(40 + i, rms=10.0, p2p=10.0, env_energy=10.0) for i in range(4)]  # 18..21 abnormal
    det, res = _replay(rows)
    by = {r.window: r for r in res}
    assert by[16].state == detect.Stage1State.ABNORMAL and not by[16].persistent
    assert by[17].state == detect.Stage1State.NORMAL and by[17].run_length == 0
    assert by[19].run_length == 2 and by[19].onset_window is None
    assert by[20].run_length == 3 and by[20].onset_window == 18
    assert det.onset_window == 18
    assert by[21].persistent


def test_watch_early_when_only_hf_or_envelope_move():
    base = [_row(i) for i in range(10)]
    _, res = _replay(base + [_row(50, env_energy=10.0)])
    assert res[-1].state == detect.Stage1State.WATCH_EARLY and res[-1].moved == ["envelope"]
    _, res = _replay(base + [_row(51, be_2000_4000=10.0)])
    assert res[-1].state == detect.Stage1State.WATCH_EARLY and res[-1].moved == ["hf_band"]
    # two early groups is fusion (spec: >= 2 groups) -> ABNORMAL, same precedence as prep/stage1_replay.py
    _, res = _replay(base + [_row(52, be_2000_4000=10.0, env_energy=10.0)])
    assert res[-1].state == detect.Stage1State.ABNORMAL and res[-1].moved == ["hf_band", "envelope"]


def test_one_group_is_watch_not_abnormal():
    rows = [_row(i) for i in range(10)] + [_row(50, rms=10.0, p2p=10.0)]
    _, res = _replay(rows)
    assert res[-1].state == detect.Stage1State.WATCH and res[-1].moved == ["energy"]


def test_one_sided_rule_ignores_drops():
    rows = [_row(i) for i in range(10)] + [_row(50, rms=10.0, p2p=10.0, crest=0.0, kurtosis_excess=-50.0)]
    _, res = _replay(rows)
    assert res[-1].moved == ["energy"]        # shape fell; under one-sided it does not count
    assert res[-1].state == detect.Stage1State.WATCH


def test_build_test_fake_tone_cannot_look_abnormal():
    """Spec Stage-1 build test, synthetic version: a 107.9 Hz tone at 5x RMS in a healthy window
    moves energy UP and shape DOWN. One-sided fusion leaves only one group -> never ABNORMAL."""
    base_rows = [features.compute_features(white(1.0, seed=s)) for s in range(10)]
    healthy = white(1.0, seed=99)
    rms = float(np.sqrt(np.mean(healthy ** 2)))
    t = np.arange(len(healthy)) / 25600.0
    fake = healthy + 5.0 * rms * np.sin(2 * np.pi * 107.907 * t)
    det, _ = _replay(base_rows)
    r = det.push(11, features.compute_features(fake))
    assert r.moved == ["energy"]
    assert r.state == detect.Stage1State.WATCH
