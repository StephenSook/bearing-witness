"""Fleet screen: poster-card grid of the 15 XJTU-SY bearings, exact denominator.

The frozen v3 evaluator ran Fri 2026-08-21 night (0 wrong / 10 correct /
1 cage-consistent / 4 abstain / 0 missed): when eval/results_v3.json is present
every card shows its REAL verdict, status, and onset. Only Bearing1_3 carries
the full replay walk, and only its card navigates; without the results file the
screen falls back to the honest 1-of-15 fixture state.
"""
from __future__ import annotations

from nicegui import ui

from ..contract_shape import traffic_light
from .casedata import FLEET_TOTAL, SCENARIOS, Backend, evaluation
from .hud import Hud
from .theme import LAMP

BEARINGS = [f"Bearing{c}_{i}" for c in (1, 2, 3) for i in range(1, 6)]
CONDITIONS = {1: "35HZ/12KN", 2: "37.5HZ/11KN", 3: "40HZ/10KN"}

_VERDICT_SHORT = {"CORRECT": "CORRECT", "CORRECT_CONSISTENT": "CONSISTENT",
                  "ABSTAIN": "ABSTAINED"}


def view(backend: Backend, hud: Hud) -> None:
    red = backend.case("red")
    hud.show_case(red)
    ev = evaluation()
    results = (ev or {}).get("results", {})

    with ui.element("div").classes("w-full"):
        ui.html('<div class="bw-display bw-headline" data-scramble-once>DETECT THE CHANGE.</div>')
        ui.label("EXPLAIN THE SPECTRUM · ESCALATE WITH EVIDENCE · A HUMAN SAYS YES") \
            .classes("bw-mono").style("opacity:0.6;margin-top:10px")

        with ui.element("div").classes("bw-section"):
            if ev:
                s = ev["summary"]
                ui.label(f"FLEET · {len(results)} OF {FLEET_TOTAL} EVALUATED · FROZEN v3 RUN · "
                         f"{s['wrong']} WRONG · {s['missed']} MISSED · "
                         f"{s['correct'] + s['cage_consistent_correct']} CALLS · "
                         f"{s['abstain']} HONEST ABSTENTIONS").classes("bw-mono")
            else:
                ui.label(f"FLEET · 1 OF {FLEET_TOTAL} BEARINGS LOADED (FIXTURES, REAL DATA) · "
                         f"14 NOT EVALUATED").classes("bw-mono")
            ui.element("div").classes("rule")

        with ui.element("div").classes("w-full grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3"):
            for b in BEARINGS:
                cond = int(b[7])
                live = b == "Bearing1_3"   # the only bearing with the full replay walk loaded
                r = results.get(b)
                card = ui.element("div").classes("bw-card" + ("" if live else " bw-card-dead"))
                with card:
                    ui.label(b.replace("Bearing", "")).classes("bw-card-index")
                    with ui.element("div").classes("bw-caprow"):
                        ui.label(b.upper())
                        ui.element("span").classes("leader")
                        ui.label(CONDITIONS[cond])
                    if r:
                        with ui.element("div").classes("bw-caprow"):
                            ui.label(_VERDICT_SHORT.get(r["verdict"], r["verdict"])
                                     + (f" · {r['suspected_location'].upper()}"
                                        if r["suspected_location"] else "")).style("opacity:0.75")
                            ui.element("span").classes("leader")
                            ui.label("OPEN ↗" if live else f"ONSET W{r['onset_window']}")
                        with ui.element("div").classes("bw-caprow").style("margin-top:4px"):
                            ui.label(r["status"]).style(
                                f"color:{LAMP[traffic_light(r['status'])]};font-weight:700;font-size:9px")
                    elif live:
                        status = red["status"]
                        with ui.element("div").classes("bw-caprow"):
                            ui.label("LATEST").style("opacity:0.6")
                            ui.element("span").classes("leader")
                            ui.label("OPEN ↗")
                        with ui.element("div").classes("bw-caprow").style("margin-top:4px"):
                            ui.label(status).style(
                                f"color:{LAMP[traffic_light(status)]};font-weight:700;font-size:9px")
                    else:
                        with ui.element("div").classes("bw-caprow"):
                            ui.label("NOT EVALUATED").style("opacity:0.7")
                if live:
                    card.on("click", lambda: ui.navigate.to("/case/green"))

        with ui.element("div").classes("bw-section"):
            ui.label("REPLAY · ONE REAL LIFE, FOUR MOMENTS").classes("bw-mono")
            ui.element("div").classes("rule")
        with ui.element("div").classes("w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"):
            for name, meta in SCENARIOS.items():
                result = backend.case(name)
                status = result["status"]
                with ui.element("div").classes("bw-card").on(
                        "click", lambda n=name: ui.navigate.to(f"/case/{n}")):
                    ui.label(f"W{meta['window']:03d}").classes("bw-card-index").style("font-size:56px")
                    ui.label(meta["phase"]).classes("bw-subhead bw-display").style("margin-top:6px")
                    with ui.element("div").classes("bw-caprow"):
                        ui.label(status).style(
                            f"color:{LAMP[traffic_light(status)]};font-weight:700")
                        ui.element("span").classes("leader")
                        ui.label(meta["caption"].upper()[:34])
