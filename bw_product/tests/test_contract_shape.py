from bw_product import contract_shape as cs


def test_field_order_is_the_14_field_contract():
    assert len(cs.FIELDS) == 14
    assert cs.FIELDS[0] == "analysis_id" and cs.FIELDS[-1] == "human_review"


def test_empty_contract_conforms():
    assert cs.validate_shape(cs.empty_contract()) == []


def test_vocab_violations_are_caught():
    r = cs.empty_contract()
    r["status"] = "HEALTHY"  # not a product state, on purpose
    assert any("bad status" in p for p in cs.validate_shape(r))
    r = cs.empty_contract()
    r["status"] = "ANALYST_REVIEW_REQUIRED"
    r["inspection_draft"] = {
        "task_type": "INSPECT_BEARING",  # pre-rename vocabulary must be rejected
        "title": "t", "asset_id": "a", "suspected_element": "outer",
        "evidence_locators": [], "recommended_action": "inspect", "not_claimed": [],
    }
    assert any("bad task_type" in p for p in cs.validate_shape(r))


def test_replace_is_banned_in_recommended_action():
    r = cs.empty_contract()
    r["status"] = "ANALYST_REVIEW_REQUIRED"
    r["inspection_draft"] = {
        "task_type": "INSPECTION_WORK_ORDER", "title": "t", "asset_id": "a",
        "suspected_element": "outer", "evidence_locators": [],
        "recommended_action": "Replace the bearing", "not_claimed": [],
    }
    assert any("replace" in p for p in cs.validate_shape(r))


def test_traffic_light_mapping():
    assert cs.traffic_light("NO_ANOMALY_DETECTED") == "green"
    assert cs.traffic_light("WATCH_EARLY") == "yellow"
    assert cs.traffic_light("ABNORMAL_LOCATION_UNCONFIRMED") == "yellow"
    assert cs.traffic_light("BLOCKED_SIGNAL") == "yellow"
    assert cs.traffic_light("BLOCKED_BASELINE") == "yellow"
    assert cs.traffic_light("ANALYST_REVIEW_REQUIRED") == "red"
    assert cs.traffic_light("INSPECTION_APPROVED") == "resolved"


def test_locator_format():
    sha = "abcdef0123456789"
    loc = cs.locator("XJTU-SY/35Hz12kN/Bearing1_3", 155, sha, "envelope", 107.031, 1)
    assert loc == "XJTU-SY/35Hz12kN/Bearing1_3|w155|abcdef01|envelope|107.03Hz|h1"
    loc_sb = cs.locator("A", 5, sha, "ordinary", 214.0625, 2, sideband=-1)
    assert loc_sb.endswith("|214.06Hz|h2|sb-1")
