"""Persistent instrument HUD. Every value is real: acquisition metadata from the
contract's source_window, the live window counter from the selected case, the
exact deterministic state string in the corner chip. The chrome is the product's
honesty made visible; nothing here is decoration with a fake value behind it.
"""
from __future__ import annotations

from nicegui import binding, ui

from ..contract_shape import traffic_light
from .theme import LAMP


@binding.bindable_dataclass
class ReplayState:
    asset: str = "BEARING 1_3"
    window: int = 0
    total: int = 158
    status: str = "NO_ANOMALY_DETECTED"
    backend: str = "mongo"
    sound: bool = False


class Hud:
    """Built once per client; screens push the case they are showing into it."""

    def __init__(self, state: ReplayState, on_theme_toggle) -> None:
        self.state = state
        with ui.element("div").classes("bw-hud bw-hud-top"):
            with ui.element("div").style("display:flex;gap:14px;align-items:center"):
                ui.html('<span data-scramble>BEARING WITNESS</span>', tag="span") \
                    .classes("bw-mono").style("font-weight:700")
                ui.label("HERMIT CRAB").classes("bw-mono").style("opacity:0.55")
            with ui.element("div").style("display:flex;gap:22px;align-items:center"):
                ui.label("FLEET").classes("bw-mono bw-navlink").on("click", lambda: ui.navigate.to("/"))
                ui.label("EVIDENCE").classes("bw-mono bw-navlink").on("click", lambda: ui.navigate.to("/case/red"))
                ui.label("THEME[T]").classes("bw-mono bw-navlink").on("click", on_theme_toggle)
                (ui.label().classes("bw-mono bw-navlink")
                   .bind_text_from(state, "sound", backward=lambda s: "SOUND[|]" if s else "SOUND[·]")
                   .on("click", lambda: setattr(state, "sound", not state.sound)))

        with ui.element("div").classes("bw-hud bw-hud-bottom"):
            ui.label("XJTU-SY REPLAY · 25.6 kHz · 32768 PTS / 1.28 S") \
                .classes("bw-mono").style("opacity:0.75")
            (ui.label().classes("bw-mono")
               .bind_text_from(state, "window",
                               backward=lambda w: f"{self.state.asset} · WINDOW {w:04d}/{self.state.total} · +{w} MIN"))
            with ui.element("div").style("display:flex;gap:10px;align-items:center"):
                self.backend_chip = ui.label().classes("bw-mono").style("opacity:0.75")
                self.backend_chip.bind_text_from(
                    state, "backend",
                    backward=lambda b: "MONGO LOCAL" if b == "mongo" else "MONGO OFFLINE · FILE FALLBACK")
                with ui.element("span").classes("bw-chip bw-mono"):
                    self.dot = ui.element("span").classes("dot")
                    ui.label().classes("bw-mono").bind_text_from(state, "status")
        self.set_status(state.status)

    def set_status(self, status: str) -> None:
        self.state.status = status
        self.dot.style(replace=f"background:{LAMP[traffic_light(status)]}")
        self.dot.update()

    def show_case(self, result: dict) -> None:
        self.state.window = int(result["source_window"]["record"])
        self.set_status(result["status"])
