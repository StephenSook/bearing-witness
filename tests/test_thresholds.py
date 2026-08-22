import dataclasses

from bearing_witness import thresholds


def test_thresholds_are_frozen_v3_and_hashable():
    th = thresholds.THRESHOLDS
    assert th.VERSION == "v3"
    assert dataclasses.is_dataclass(th) and th.__dataclass_params__.frozen
    assert th.baseline_n == 10 and th.z_thresh == 5.0 and th.persist == 3 and th.min_groups == 2
    assert th.one_sided is True
    assert th.demod_band == (2000.0, 4000.0)
    assert th.family_present == 9.0 and th.margin == 1.5 and th.loc_last == 5
    assert th.cage_min_harmonics == 3 and th.element_min_harmonics == 3
    assert len(thresholds.thresholds_sha256()) == 64
