"""Evidence screen (PLAN.md 2.5): one real bearing, one window, every claim
linked to something checkable. Trend above, trust and machine-frequency
explanation beside each other, the two spectra side by side, locators
underneath, and the decision block last: the screen ends on a decision,
never on a lone spectrum.
"""
from __future__ import annotations

from pathlib import Path

from nicegui import ui

from .casedata import SCENARIOS, Backend, load, trend as load_trend
from . import charts, decide, trust
from .hud import Hud
from .live import live_analysis_row

AUDIO_DIR = Path(__file__).parent.parent / "fixtures_data"


def _stepper(current: str) -> None:
    with ui.element("div").style("display:flex;gap:10px;flex-wrap:wrap"):
        for name, meta in SCENARIOS.items():
            sel = name == current
            label = f"W{meta['window']:03d}" + ("*" if name == "refusal" else "")
            chip = ui.label(label).classes("bw-mono bw-chip" + (" bw-chip-lime" if sel else ""))
            chip.style("cursor:pointer")
            if not sel:
                chip.on("click", lambda n=name: ui.navigate.to(f"/case/{n}"))


def _explain_panel(result: dict) -> None:
    mc = result["machine_components"]
    with ui.element("div").classes("bw-card w-full").style("cursor:default"):
        ui.label("STAGE 2 · KNOWN MACHINE FREQUENCIES FIRST").classes("bw-mono").style("font-weight:700")
        ui.label("CALCULATED FAMILIES SUPPORT LOCALIZATION. THEY ARE NOT THE DETECTOR.") \
            .classes("bw-mono").style("opacity:0.55;margin-top:4px;font-size:9px")
        for fam, hz in mc["predicted_hz"].items():
            with ui.element("div").classes("bw-caprow").style("margin-top:6px"):
                ui.label(fam)
                ui.element("span").classes("leader")
                ui.label(f"{hz:.3f} HZ · ±{charts.half_width(hz):.2f}")
        with ui.element("div").classes("bw-caprow").style("margin-top:6px"):
            ui.label("SHAFT 1X (SETPOINT)")
            ui.element("span").classes("leader")
            ui.label(f'{mc["shaft_hz_nominal"]:.1f} HZ · PREDICTIONS USE THIS')
        ui.label("ENVELOPE PEAK HEIGHT IS NOT SEVERITY: LATE-STAGE IMPACTS BROADEN AND OVERLAP.") \
            .classes("bw-mono").style("opacity:0.5;margin-top:10px;font-size:9px")


def view(name: str, backend: Backend, hud: Hud, dark: bool, fx_on: bool) -> None:
    if name not in SCENARIOS:
        ui.label("unknown case").classes("bw-mono")
        return
    meta = SCENARIOS[name]

    def _render() -> None:
        result = backend.case(name)
        hud.show_case(result)
        container.clear()
        with container:
            ui.html(f'<div class="bw-display bw-headline" data-scramble-once>{meta["phase"]}</div>')
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;margin-top:12px;flex-wrap:wrap;gap:10px"):
                _stepper(name)
                ui.label(result["analysis_id"].upper()).classes("bw-mono").style("opacity:0.5")

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 1 · TREND VS THE ASSET'S OWN EARLY BASELINE · "
                         f"REPLAY SEES ONLY WINDOWS 1-{meta['window']}").classes("bw-mono")
                ui.element("div").classes("rule")
            onset = result["anomaly_evidence"].get("onset_window")
            # replay discipline: window k sees only 1..k; never plot the future
            clipped = charts.clip_trend(backend_trend, meta["window"])
            onset_shown = onset if (onset is not None and onset <= meta["window"]) else None
            ui.plotly({**charts.trend_figure(clipped, meta["window"], onset_shown, dark),
                       "config": charts.CONFIG}).classes("w-full").style("height:230px")

            with ui.element("div").classes("w-full grid grid-cols-1 lg:grid-cols-2 gap-4"):
                trust.panel(result)
                _explain_panel(result)

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 3 · TWO VIEWS, SIDE BY SIDE").classes("bw-mono")
                ui.element("div").classes("rule")
            series = backend_series[name]
            with ui.element("div").classes("w-full grid grid-cols-1 lg:grid-cols-2 gap-4"):
                ui.plotly({**charts.spectrum_figure(
                    series["ordinary"], dark, title="View A · ordinary spectrum",
                    xmax=2000, log_y=True), "config": charts.CONFIG}) \
                    .classes("w-full").style("height:300px")
                ui.plotly({**charts.spectrum_figure(
                    series["envelope"], dark, title="View B · envelope spectrum (2-4 kHz demod)",
                    xmax=450, predicted=result["machine_components"]["predicted_hz"],
                    peaks=result["envelope_evidence"]["peaks"]), "config": charts.CONFIG}) \
                    .classes("w-full").style("height:300px")

            locs = [loc for fam in result["candidate_families"] for loc in fam["locators"]]
            if result["inspection_draft"]:
                locs = locs or result["inspection_draft"]["evidence_locators"]
            if locs:
                with ui.element("div").classes("bw-section"):
                    ui.label("EVIDENCE LOCATORS · EVERY CLAIM RESOLVES").classes("bw-mono")
                    ui.element("div").classes("rule")
                for loc in locs:
                    ui.label(loc).classes("bw-locator").on(
                        "click", lambda l=loc: ui.notify(f"locator · {l}", type="info"))

            if fx_on and name in ("red",):
                ui.button("ENTER CORROBORATION VIEW ↗",
                          on_click=lambda: ui.navigate.to(f"/spectrum/{name}")) \
                    .props("outline no-caps").classes("bw-mono").style("margin-top:18px;color:inherit")

            wav_early = AUDIO_DIR / "beat_early.wav"
            wav_late = AUDIO_DIR / "beat_late.wav"
            if hud.state.sound and wav_early.exists() and wav_late.exists():
                with ui.element("div").classes("bw-section"):
                    ui.label("AUDIO BEAT · TWO NATIVE-SPEED 1.28 S RECORDS").classes("bw-mono")
                    ui.element("div").classes("rule")
                with ui.element("div").classes("w-full grid grid-cols-2 gap-4"):
                    with ui.element("div"):
                        ui.label("EARLY (W8)").classes("bw-mono")
                        ui.audio("/fixtures/beat_early.wav")
                    with ui.element("div"):
                        ui.label("LATE (W155)").classes("bw-mono")
                        ui.audio("/fixtures/beat_late.wav")

            with ui.element("div").classes("bw-section"):
                ui.label("STAGE 4 · A HUMAN SAYS YES").classes("bw-mono")
                ui.element("div").classes("rule")
            decide.block(name, backend, hud, _render)

            # dormant until `python -m bearing_witness` answers (2.8): the
            # pick-any-window flex renders itself the moment the engine exists
            live_analysis_row(backend)

    backend_trend = load_trend()
    backend_series = {name: load(name)["series"]}
    container = ui.element("div").classes("w-full")
    _render()
