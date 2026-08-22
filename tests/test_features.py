import numpy as np
import pytest

from bearing_witness import features
from tests.synth import synth_fault, white


def test_feature_names_are_frozen_and_grouped():
    assert features.FEATURE_NAMES == [
        "rms", "p2p", "crest", "kurtosis_excess",
        "be_2000_4000", "be_4000_6000", "be_6000_8000", "be_8000_10000", "env_energy",
    ]
    assert set(sum(features.FEATURE_GROUPS.values(), [])) == set(features.FEATURE_NAMES)
    assert list(features.FEATURE_GROUPS) == ["energy", "shape", "hf_band", "envelope"]


def test_white_noise_features():
    f = features.compute_features(white(1.0))
    assert set(f) == set(features.FEATURE_NAMES)
    assert f["rms"] == pytest.approx(1.0, rel=0.02)
    assert abs(f["kurtosis_excess"]) < 0.1
    assert 3.5 < f["crest"] < 6.0


def test_fault_signal_moves_hf_band_and_envelope_not_only_energy():
    base = features.compute_features(white(0.2))
    fault = features.compute_features(synth_fault(107.907, noise=0.2, amp=4.0))  # amp is a fixture choice: synth default 1.0 yields only ~2.3x / ~1.4x on these bands (ruled 2026-08-21)
    assert fault["be_2000_4000"] > 3 * base["be_2000_4000"]
    assert fault["env_energy"] > 3 * base["env_energy"]
    assert fault["kurtosis_excess"] > base["kurtosis_excess"] + 1.0
    assert fault["be_8000_10000"] < 2 * base["be_8000_10000"]  # ringing at 3 kHz does not leak to 8-10 kHz
