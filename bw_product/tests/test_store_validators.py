import pytest
from pymongo.errors import DuplicateKeyError, WriteError

from bw_product import contract_shape as cs
from bw_product import store as st
from bw_product.tests.conftest import needs_mongod

pytestmark = needs_mongod


def _red():
    r = cs.empty_contract()
    r.update({
        "analysis_id": "Bearing1_3-0155-abcdef01",
        "asset_id": "XJTU-SY/35Hz12kN/Bearing1_3",
        "status": "ANALYST_REVIEW_REQUIRED",
        "suspected_location": "outer",
        "inspection_draft": {
            "task_type": "INSPECTION_WORK_ORDER",
            "title": "Inspect outer race, Bearing1_3",
            "asset_id": "XJTU-SY/35Hz12kN/Bearing1_3",
            "suspected_element": "outer",
            "evidence_locators": ["XJTU-SY/35Hz12kN/Bearing1_3|w155|abcdef01|envelope|107.03Hz|h1"],
            "recommended_action": "Schedule a visual inspection of the outer race.",
            "not_claimed": ["RUL", "severity grading"],
        },
        "human_review": {"required": True, "decision": None, "reason": None, "timestamp": None},
    })
    return r


def test_init_creates_three_collections_with_validators(db):
    st.init_db(db)
    names = set(db.list_collection_names())
    assert {"asset_configs", "feature_windows", "diagnostic_cases"} <= names
    info = db.command("listCollections", filter={"name": "diagnostic_cases"})
    opts = info["cursor"]["firstBatch"][0]["options"]
    assert "$jsonSchema" in opts.get("validator", {})
    ts_info = db.command("listCollections", filter={"name": "feature_windows"})
    assert "timeseries" in ts_info["cursor"]["firstBatch"][0]["options"]


def test_bad_status_rejected_by_python_gate(db):
    st.init_db(db)
    bad = _red()
    bad["status"] = "HEALTHY"
    with pytest.raises(ValueError):
        st.insert_case(db, bad)


def test_bad_status_rejected_by_mongo_validator(db):
    """Defense in depth: the raw insert (bypassing insert_case) must still be
    refused by the collection's own $jsonSchema validator."""
    st.init_db(db)
    bad = _red()
    bad["status"] = "HEALTHY"
    with pytest.raises(WriteError):
        db.diagnostic_cases.insert_one(bad)


def test_bad_task_type_rejected_by_python_gate(db):
    st.init_db(db)
    bad = _red()
    bad["inspection_draft"]["task_type"] = "INSPECT_BEARING"
    with pytest.raises(ValueError):
        st.insert_case(db, bad)


def test_bad_task_type_rejected_by_mongo_validator(db):
    st.init_db(db)
    bad = _red()
    bad["inspection_draft"]["task_type"] = "INSPECT_BEARING"
    with pytest.raises(WriteError):
        db.diagnostic_cases.insert_one(bad)


def test_collmod_enforces_validator_on_preexisting_collection(db):
    """A collection created WITHOUT a validator (older version, another lane's
    bring-up) must be brought under validation by init_db, not silently kept."""
    db.create_collection("diagnostic_cases")
    st.init_db(db)
    bad = _red()
    bad["status"] = "HEALTHY"
    with pytest.raises(WriteError):
        db.diagnostic_cases.insert_one(bad)


def test_asset_config_versions_are_immutable(db):
    st.init_db(db)
    geometry = {
        "bearing_model": "LDK UER204", "n_balls": 8, "ball_diameter_mm": 7.92,
        "pitch_diameter_mm": 34.55, "contact_angle_deg": 0.0,
        "provenance": "Wang et al. 2020, DOI 10.1109/TR.2018.2882682; Zhang et al. 2023 Table 2",
    }
    v1 = st.put_asset_config(db, "XJTU-SY/35Hz12kN/Bearing1_3", geometry,
                             regime={"speed_hz_setpoint": 35.0, "load_kN": 12.0})
    assert v1 == 1
    with pytest.raises(DuplicateKeyError):
        st.insert_asset_config_version(db, "XJTU-SY/35Hz12kN/Bearing1_3", 1, geometry, {})
    v2 = st.put_asset_config(db, "XJTU-SY/35Hz12kN/Bearing1_3", geometry,
                             regime={"speed_hz_setpoint": 35.0, "load_kN": 12.0})
    assert v2 == 2
    cur = st.current_asset_config(db, "XJTU-SY/35Hz12kN/Bearing1_3")
    assert cur["version"] == 2


def test_feature_window_timeseries_insert(db):
    st.init_db(db)
    st.insert_feature_window(
        db, asset_id="XJTU-SY/35Hz12kN/Bearing1_3", condition="35Hz12kN", window=59,
        features={"rms": 3.67, "p2p": 41.0, "kurtosis_excess": 0.1},
        source_file="Bearing1_3/59.csv", sha256="0" * 64,
    )
    assert db.feature_windows.count_documents({}) == 1


def test_unique_analysis_key(db):
    st.init_db(db)
    st.insert_case(db, _red())
    with pytest.raises(DuplicateKeyError):
        st.insert_case(db, _red())
