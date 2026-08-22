"""Bearing Witness UI entry (PLAN.md 2.3-2.7).

Run: .venv-product/bin/python -m bw_product.ui        (BW_FX=off for the flat build)

One NiceGUI app, sub-page routing, the instrument HUD on every screen. The FX
layer (preloader, pinhole, scramble, WebGL corroboration) is progressive
enhancement behind BW_FX; the judged loop renders complete with it off.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from nicegui import app, ui

from ..contract_shape import traffic_light
from . import charts, evidence, fleet, fleet_case, theme
from .casedata import SCENARIOS, connect_backend, load
from .hud import Hud, ReplayState

HERE = Path(__file__).parent
FX_ON = os.environ.get("BW_FX", "on").lower() not in ("off", "0", "false")

app.add_static_files("/static", str(HERE / "static"))
app.add_static_files("/fixtures", str(HERE.parent / "fixtures_data"))

BACKEND = connect_backend()


def spectrum_view(name: str, hud: Hud, dark) -> None:
    """Full-bleed dark corroboration screen. The tunnel IS the measured envelope."""
    if name not in SCENARIOS:
        ui.label("unknown case").classes("bw-mono")
        return
    result = BACKEND.case(name)
    series = load(name)["series"]
    hud.show_case(result)
    ui.query("body").classes(add="bw-void")

    with ui.element("div").classes("w-full").style("position:relative;height:calc(100vh - 170px)"):
        if FX_ON:
            ui.element("div").props('id="bw-spectrum3d"').classes("w-full") \
                .style("position:absolute;inset:0")
            payload = json.dumps({"envelope": series["envelope"],
                                  "peaks": result["envelope_evidence"]["peaks"]})
            ui.add_body_html(f"""
            <script type="module">
              import {{ init }} from '/static/fx/spectrum3d.js';
              setTimeout(() => init('bw-spectrum3d', {payload}), 120);
            </script>""")
        else:
            ui.plotly({**charts.spectrum_figure(
                series["envelope"], True, title="View B · envelope spectrum (2-4 kHz demod)",
                xmax=450, predicted=result["machine_components"]["predicted_hz"],
                peaks=result["envelope_evidence"]["peaks"]), "config": charts.CONFIG}) \
                .classes("w-full").style("height:60vh")

        with ui.element("div").style(
                "position:absolute;left:24px;bottom:24px;pointer-events:none;z-index:5"):
            ui.html('<div class="bw-display bw-subhead" data-scramble-once>TWO VIEWS AGREE.</div>')
            for p in result["envelope_evidence"]["peaks"]:
                # engine peaks name themselves ("BPFO h2"); fixture peaks carry
                # harmonic + label both. Render the label, never index a key
                # only one dialect has.
                label = p.get("label") or f"BPFO h{p.get('harmonic', '?')}"
                ui.label(f"{label} · {p['freq_hz']:.2f} HZ · MEASURED") \
                    .classes("bw-mono").style("opacity:0.85")
            ui.label(f"PREDICTED {result['machine_components']['predicted_hz']['BPFO']:.2f} HZ "
                     f"· SETPOINT 35.0 · SLIP VISIBLE").classes("bw-mono").style("opacity:0.55")
        ui.button("← EVIDENCE", on_click=lambda: ui.navigate.to(f"/case/{name}")) \
            .props("outline no-caps").classes("bw-mono") \
            .style("position:absolute;right:24px;bottom:24px;color:#efede7;z-index:6")


def index() -> None:
    theme.apply()
    dark = ui.dark_mode(value=False)
    state = ReplayState(backend=BACKEND.kind, total=158)

    if FX_ON:
        ui.add_body_html('<script src="/static/fx/scramble.js"></script>')
        ui.add_body_html('<script src="/static/fx/pinhole.js"></script>')
        ui.add_body_html('<script src="/static/fx/preloader.js"></script>')
    else:
        ui.add_body_html("<script>window.__bwFxOff = true;</script>")

    def toggle_theme() -> None:
        dark.toggle()
        if FX_ON:
            ui.run_javascript("window.bwPinhole && window.bwPinhole.wipe()")

    hud = Hud(state, toggle_theme)
    ui.keyboard(on_key=lambda e: _keys(e, toggle_theme), repeating=False)

    def _keys(e, toggle) -> None:
        if not e.action.keydown:
            return
        if e.key == "f":
            ui.navigate.to("/")
        elif e.key == "e":
            ui.navigate.to("/case/red")
        elif e.key == "t":
            toggle()

    def _light_field() -> None:
        ui.query("body").classes(remove="bw-void")

    async def _fleet_case_page(bearing: str, condition: str, record: str) -> None:
        _light_field()
        await fleet_case.view(bearing, condition, int(record), BACKEND, hud, dark.value)

    with ui.element("div").classes("bw-field w-full"):
        ui.sub_pages({
            "/": lambda: (_light_field(), fleet.view(BACKEND, hud)),
            "/case/{name}": lambda name: (_light_field(),
                                          evidence.view(name, BACKEND, hud, dark.value, FX_ON)),
            "/spectrum/{name}": lambda name: spectrum_view(name, hud, dark),
            "/fleet/{bearing}/{condition}/{record}": _fleet_case_page,
        }).classes("w-full")


def run() -> None:
    ui.run(index, title="BEARING WITNESS", reload=False, show=False,
           favicon=str(HERE / "static" / "favicon.svg"),
           port=int(os.environ.get("BW_PORT", "8080")), dark=None)
