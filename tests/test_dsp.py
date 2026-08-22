import numpy as np
import pytest

from bearing_witness import dsp
from tests.synth import synth_fault, tones, white


def test_constants():
    assert dsp.FS == 25600.0
    assert dsp.N_EXPECTED == 32768
    assert dsp.BIN_W == pytest.approx(0.78125)


def test_fault_frequencies_match_hand_check():
    f = dsp.fault_frequencies(35.0)
    assert f["BPFO"] == pytest.approx(107.907, abs=1e-3)
    assert f["BPFI"] == pytest.approx(172.093, abs=1e-3)
    assert f["BSF2"] == pytest.approx(144.660, abs=1e-3)
    assert f["FTF"] == pytest.approx(13.488, abs=1e-3)
    assert f["FTF"] == pytest.approx(f["BPFO"] / 8.0)  # identity for 8 elements


def test_half_width_uses_half_bin_only_for_ftf():
    assert dsp.half_width(13.488, 0.02) == pytest.approx(0.390625)      # half-bin wins
    assert dsp.half_width(107.907, 0.02) == pytest.approx(2.15814)      # relative wins
    assert dsp.half_width(144.660, 0.02) > 0.5 * dsp.BIN_W
    assert dsp.half_width(172.093, 0.02) > 0.5 * dsp.BIN_W


def test_envelope_spectrum_recovers_impact_rate():
    x = synth_fault(107.907)
    freqs, amp = dsp.envelope_spectrum(x, (2000.0, 4000.0))
    m = (freqs > 5) & (freqs < 500)
    f_peak = freqs[m][np.argmax(amp[m])]
    assert abs(f_peak - 107.907) < 1.0
    noise = dsp.noise_floor(freqs, amp)
    _, a2 = dsp.peak_in_window(freqs, amp, 2 * 107.907, 2.0)
    assert a2 > 3 * noise  # harmonic ladder present


def test_ordinary_spectrum_amplitude_and_frequency():
    x = tones([(35.0, 1.0)], noise=0.0)
    freqs, amp = dsp.ordinary_spectrum(x)
    f_peak, a_peak = dsp.peak_in_window(freqs, amp, 35.0, 1.0)
    assert abs(f_peak - 35.0) < dsp.BIN_W
    assert a_peak == pytest.approx(1.0, rel=0.05)


def test_peak_in_window_and_empty_window():
    freqs = np.arange(0, 100, 1.0)
    amp = np.zeros_like(freqs); amp[40] = 5.0
    assert dsp.peak_in_window(freqs, amp, 41.0, 2.0) == (40.0, 5.0)
    f, a = dsp.peak_in_window(freqs, amp, 500.0, 1.0)
    assert np.isnan(f) and a == 0.0


def test_refine_peak_interpolates_between_bins():
    x = tones([(34.7, 1.0)], noise=0.0)
    freqs, amp = dsp.ordinary_spectrum(x)
    j = int(np.argmax(amp[(freqs > 30) & (freqs < 40)]) + np.flatnonzero(freqs > 30)[0])
    assert abs(dsp.refine_peak(freqs, amp, j) - 34.7) < 0.1          # better than the 0.78 Hz bin
    assert dsp.refine_peak(freqs, amp, 0) == freqs[0]                 # edge bins fall back to the bin centre


def test_local_noise_excludes_center():
    freqs = np.arange(0, 200, 0.5)
    amp = np.ones_like(freqs); amp[(freqs >= 99) & (freqs <= 101)] = 100.0
    assert dsp.local_noise(freqs, amp, 100.0, half_span=20.0, exclude_hw=1.5) == pytest.approx(1.0)


def test_excess_kurtosis():
    assert abs(dsp.excess_kurtosis(white(1.0, 200000))) < 0.1
    impulsive = white(0.1); impulsive[::2000] += 5.0
    assert dsp.excess_kurtosis(impulsive) > 3.0


def test_robust_z():
    assert dsp.robust_z(10.0, 5.0, 1.0) == pytest.approx(3.3725)
    assert dsp.robust_z(5.0, 5.0, 0.0) == 0.0
    assert dsp.robust_z(6.0, 5.0, 0.0) == pytest.approx(1e9)
    assert dsp.robust_z(4.0, 5.0, 0.0) == pytest.approx(-1e9)
