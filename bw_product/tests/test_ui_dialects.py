"""The evidence UI must render BOTH nested dialects: the fixtures' transcription
and the live engine's contract (shapes verified against the real CLI,
2026-08-22). These are the exact engine key-sets that used to KeyError the
trust panel and the chart annotations.
"""
from bw_product.ui import trust

ENGINE_GEOMETRY = {"model_number": "LDK UER204", "n_elements": 8, "D_mm": 34.55,
                   "d_mm": 7.92, "contact_angle_deg": 0.0, "source": "kit",
                   "trust": "verified"}
FIXTURE_GEOMETRY = {"bearing_model": "LDK UER204", "n_balls": 8,
                    "ball_diameter_mm": 7.92, "pitch_diameter_mm": 34.55,
                    "contact_angle_deg": 0.0, "provenance": "Wang 2020",
                    "verified": True}
ENGINE_REGIME = {"condition_id": "35Hz12kN", "load_kn": 12.0, "source": "kit",
                 "trust": "verified"}
FIXTURE_REGIME = {"condition": "35Hz12kN", "load_kN": 12.0}


def test_geometry_line_renders_both_dialects():
    assert trust.geometry_line(ENGINE_GEOMETRY) == "LDK UER204 · 8 balls"
    assert trust.geometry_line(FIXTURE_GEOMETRY) == "LDK UER204 · 8 balls"


def test_regime_line_renders_both_dialects():
    assert trust.regime_line(ENGINE_REGIME) == "35Hz12kN · 12 kN"
    assert trust.regime_line(FIXTURE_REGIME) == "35Hz12kN · 12 kN"


def test_geometry_verified_prefers_machine_components():
    engine_like = {"machine_components": {"geometry_verified": True},
                   "input_trust": {"geometry": ENGINE_GEOMETRY}}
    fixture_like = {"machine_components": {},
                    "input_trust": {"geometry": FIXTURE_GEOMETRY}}
    unverified = {"machine_components": {"geometry_verified": False},
                  "input_trust": {"geometry": ENGINE_GEOMETRY}}
    assert trust.geometry_verified(engine_like) is True
    assert trust.geometry_verified(fixture_like) is True
    assert trust.geometry_verified(unverified) is False


def test_slip_line_uses_live_measurement_when_present():
    live = {"machine_components": {"shaft_hz_measured": 34.579, "shaft_hz_nominal": 35.0},
            "input_trust": {"speed": {"value_hz": 35.0}}}
    fixture = {"machine_components": {"shaft_hz_measured": None},
               "input_trust": {"speed": {"value_hz": 35.0}}}
    assert trust.slip_line(live) == "34.58 Hz (1.2% low: slip)"
    assert "prep measurement" in trust.slip_line(fixture)


def test_chart_annotation_derives_harmonic_from_engine_label():
    from bw_product.ui.charts import spectrum_figure
    engine_peaks = [{"freq_hz": 214.06, "amp": 1.19, "label": "BPFO h2",
                     "locator": "x|w155|abcd1234|envelope|214.06Hz|h2"}]
    fig = spectrum_figure(([0, 450], [0, 1]), False, title="t", peaks=engine_peaks)
    texts = [a["text"] for a in fig["layout"]["annotations"]]
    assert any(t.startswith("h2") for t in texts), texts