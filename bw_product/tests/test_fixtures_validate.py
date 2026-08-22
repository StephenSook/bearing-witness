import json
from pathlib import Path

import pytest

from bw_product import contract_shape as cs
from bw_product import store as st
from bw_product.tests.conftest import needs_mongod

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures_data"
NAMES = ("green", "yellow", "red", "refusal")

pytestmark = pytest.mark.skipif(
    not (FIXTURE_DIR / "fixture_red.json").exists(),
    reason="fixtures not generated (run python -m bw_product.fixtures)")


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"fixture_{name}.json").read_text())


def test_every_fixture_conforms_to_contract_shape():
    for name in NAMES:
        assert cs.validate_shape(_load(name)["result"]) == [], name


def test_red_fixture_measured_bpfo_is_near_prediction_and_low():
    peaks = _load("red")["result"]["envelope_evidence"]["peaks"]
    f0 = peaks[0]["freq_hz"]
    # measured fundamental sits inside the +/-2% window and runs low (slip)
    assert abs(f0 - 107.907) <= 2.16
    assert f0 < 107.907


def test_red_fixture_harmonics_are_integer_multiples():
    peaks = _load("red")["result"]["envelope_evidence"]["peaks"]
    f0 = peaks[0]["freq_hz"]
    for p in peaks[1:]:
        assert abs(p["freq_hz"] - p["harmonic"] * f0) <= 2.0


def test_refusal_fixture_blocks_localization_with_the_exact_task():
    r = _load("refusal")["result"]
    assert r["status"] == "ABNORMAL_LOCATION_UNCONFIRMED"
    assert r["suspected_location"] is None
    assert r["inspection_draft"]["task_type"] == "VERIFY_BEARING_GEOMETRY"
    assert r["refusal_reasons"]


@needs_mongod
def test_every_fixture_inserts_under_live_validators(db):
    st.init_db(db)
    for name in NAMES:
        st.insert_case(db, _load(name)["result"])
    assert db.diagnostic_cases.count_documents({}) == len(NAMES)


@needs_mongod
def test_asset_config_fixture_inserts_under_validator(db):
    st.init_db(db)
    r = _load("red")["result"]
    geometry = {k: v for k, v in r["input_trust"]["geometry"].items() if k != "verified"}
    v = st.put_asset_config(db, r["asset_id"], geometry, r["input_trust"]["regime"])
    assert v == 1


def test_red_fixture_view_a_support_is_measured_not_asserted():
    ose = _load("red")["result"]["ordinary_spectrum_evidence"]
    assert ose["view_a_supports"] == "BPFO"  # family name per the real contract
    assert len(ose["peaks"]) == 3
    for p in ose["peaks"]:
        # every peak carries the contract's SpectrumPeak shape incl. its locator
        assert set(p) >= {"freq_hz", "amp", "label", "locator"}, p
        assert p["locator"].split("|")[3] == "ordinary"


def test_red_family_scores_are_measured_floats():
    fam = _load("red")["result"]["candidate_families"][0]
    assert isinstance(fam["score_median"], float) and fam["score_median"] > 0
    assert isinstance(fam["score_current"], float) and fam["score_current"] > 0
    assert fam["harmonics_above_floor_median"] >= 3
    assert fam["sideband_pairs_median"] == 0.0  # no v3 sideband spacing for BPFO
    assert fam["eligible"] is True


def test_all_fixtures_validate_under_real_engine_contract():
    """THE SEAM TEST (integration protocol, first gate of PLAN 2.8): every fixture
    must validate under the engine lane's real pydantic ResultContract, landed
    2026-08-21 (bearing_witness/contract.py). Read-only consumption; the adapter
    flip itself stays a Saturday task."""
    contract = pytest.importorskip("bearing_witness.contract")
    for name in NAMES:
        contract.ResultContract.model_validate(_load(name)["result"])


def test_build_red_refuses_unsupporting_window():
    """The builder must fail loudly rather than emit a red claim its own
    measurements do not back (fabricated-evidence guard). Window 8 is early
    life: no two-view support exists there."""
    fixtures = pytest.importorskip("bw_product.fixtures")
    try:
        fixtures.data_root()
    except FileNotFoundError:
        pytest.skip("XJTU-SY corpus not mounted")
    with pytest.raises(ValueError, match="not supported by measurement"):
        fixtures.build_red(8)
