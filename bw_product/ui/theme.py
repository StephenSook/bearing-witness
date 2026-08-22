"""Signal Ledger design tokens + global chrome CSS.

Direction (from the haoqi.design teardown, FRONTEND_DESIGN_LANGUAGE_Aug21.md):
editorial poster typography inside a live instrument. Paper field in light mode,
graphite in dark; tiny mono telemetry everywhere; hairline gauge grid with +
crosses; lime is spent ONLY on evidence; state colors are earned by state.
Fonts: Archivo variable (display) + Geist Mono (telemetry), vendored offline.
"""
from __future__ import annotations

from nicegui import ui

# palette (light-mode values; dark overrides below)
PAPER = "#efede7"
PAPER_BRIGHT = "#fbfaf4"
INK = "#111512"
GRAPHITE = "#191b1b"
GRAPHITE_DEEP = "#0f1111"
LIME = "#d8ff3e"
STATE_GREEN = "#2f7d4f"
STATE_AMBER = "#a9741a"
STATE_RED = "#b23b3b"
TRACE_MEASURED = "#b23b3b"
TRACE_PREDICTED = "#1f4fa3"
EASE = "cubic-bezier(0.66, 0, 0.01, 1)"

LAMP = {"green": STATE_GREEN, "yellow": STATE_AMBER, "red": STATE_RED, "resolved": "#5a6058"}

CSS = f"""
@import url('/static/vendor/fonts.css');

:root {{
  --paper: {PAPER};
  --paper-bright: {PAPER_BRIGHT};
  --ink: {INK};
  --graphite: {GRAPHITE};
  --graphite-deep: {GRAPHITE_DEEP};
  --lime: {LIME};
  --state-green: {STATE_GREEN};
  --state-amber: {STATE_AMBER};
  --state-red: {STATE_RED};
  --trace-measured: {TRACE_MEASURED};
  --trace-predicted: {TRACE_PREDICTED};
  --field: var(--paper);
  --ink-now: var(--ink);
  --hairline: rgba(17, 21, 18, 0.18);
  --ease: {EASE};
}}
body.body--dark {{
  --field: var(--graphite);
  --ink-now: var(--paper);
  --hairline: rgba(239, 237, 231, 0.16);
}}

html, body {{ background: var(--field) !important; }}
body {{
  color: var(--ink-now);
  font-family: 'Archivo', 'Helvetica Neue', sans-serif;
  transition: background 0.5s var(--ease), color 0.5s var(--ease);
}}

/* the machinist's field: hairline grid with + crosses at intersections */
.bw-field {{
  min-height: 100vh;
  background-image:
    radial-gradient(circle at 0 0, transparent 0, transparent 100%),
    linear-gradient(var(--hairline) 1px, transparent 1px),
    linear-gradient(90deg, var(--hairline) 1px, transparent 1px);
  background-size: 100% 100%, 160px 160px, 160px 160px;
  background-position: 0 0, 40px 24px, 40px 24px;
  padding: 76px 40px 84px 40px;
}}
.bw-field::before {{
  content: '+'; position: fixed; top: 72px; left: 32px; opacity: 0.4;
  font-family: 'Geist Mono', monospace; font-size: 12px; pointer-events: none;
}}

/* mono telemetry text */
.bw-mono {{
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
}}
.bw-mono-lg {{ font-family: 'Geist Mono', monospace; font-size: 13px; letter-spacing: 0.1em; }}

/* editorial display type */
.bw-display {{
  font-family: 'Archivo', sans-serif;
  font-weight: 860; font-stretch: 115%;
  letter-spacing: -0.02em; line-height: 0.92; text-transform: uppercase;
}}
.bw-headline {{ font-size: clamp(44px, 7.5vw, 118px); }}
.bw-subhead  {{ font-size: clamp(22px, 3vw, 40px); font-weight: 780; }}

/* HUD chrome */
.bw-hud {{
  position: fixed; left: 0; right: 0; z-index: 900;
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 24px; pointer-events: none;
  mix-blend-mode: normal;
}}
.bw-hud > * {{ pointer-events: auto; }}
.bw-hud-top {{
  top: 0;
  background: linear-gradient(to bottom, var(--field) 55%, transparent);
}}
.bw-hud-bottom {{
  bottom: 0;
  background: linear-gradient(to top, var(--field) 55%, transparent);
}}
.bw-hud a, .bw-hud .bw-navlink {{
  color: var(--ink-now); text-decoration: none; cursor: pointer;
  border-bottom: 1px solid transparent; transition: border-color 0.15s var(--ease);
}}
.bw-hud .bw-navlink:hover {{ border-bottom-color: var(--ink-now); }}

/* state chips */
.bw-chip {{
  display: inline-flex; align-items: center; gap: 8px;
  border: 1px solid var(--ink-now); border-radius: 2px; padding: 3px 10px;
}}
.bw-chip .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.bw-chip-lime {{ background: var(--lime); color: var(--ink); border-color: var(--ink); }}

/* poster fleet cards */
.bw-card {{
  border: 1px solid var(--hairline); border-radius: 2px;
  background: var(--paper-bright); color: var(--ink);
  padding: 18px 18px 12px 18px; position: relative; overflow: hidden;
  transition: transform 0.3s var(--ease), box-shadow 0.3s var(--ease);
  cursor: pointer;
}}
body.body--dark .bw-card {{ background: var(--graphite-deep); color: var(--paper); }}
.bw-card:hover {{ transform: translateY(-3px); box-shadow: 0 12px 32px rgba(15,17,17,0.18); }}
.bw-card.bw-card-dead {{ opacity: 0.38; cursor: not-allowed; filter: grayscale(0.6); }}
.bw-card.bw-card-dead:hover {{ transform: none; box-shadow: none; }}
.bw-card .bw-card-index {{
  font-family: 'Archivo'; font-weight: 900; font-size: 84px; line-height: 0.9;
  letter-spacing: -0.04em; opacity: 0.92;
}}
.bw-caprow {{
  display: flex; align-items: baseline; gap: 8px; margin-top: 10px;
  font-family: 'Geist Mono', monospace; font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.bw-caprow > * {{ white-space: nowrap; }}
.bw-caprow .leader {{ min-width: 12px; }}
.bw-caprow .leader {{ flex: 1; border-bottom: 1px dotted currentColor; opacity: 0.5;
  transform: translateY(-3px); }}

/* evidence locators: underlined editorial links */
.bw-locator {{
  font-family: 'Geist Mono', monospace; font-size: 11px; letter-spacing: 0.04em;
  text-decoration: underline; text-underline-offset: 3px; cursor: pointer;
  color: var(--ink-now); opacity: 0.9; word-break: break-all;
}}
.bw-locator:hover {{ background: var(--lime); color: var(--ink); }}

/* traffic lamp */
.bw-lamp {{
  width: 100%; border-radius: 2px; padding: 26px 24px;
  color: {PAPER_BRIGHT};
}}
.bw-lamp .bw-state-string {{
  font-family: 'Geist Mono', monospace; font-size: 15px; letter-spacing: 0.18em;
}}

/* section label with rule */
.bw-section {{
  display: flex; align-items: center; gap: 14px; margin: 34px 0 10px 0; width: 100%;
}}
.bw-section .rule {{ flex: 1; height: 1px; background: var(--hairline); }}

/* dark spectrum screen: the void overrides the theme vars so the HUD adapts */
.bw-void {{
  --field: {GRAPHITE_DEEP};
  --ink-now: {PAPER};
  --hairline: rgba(239, 237, 231, 0.10);
  background: {GRAPHITE_DEEP} !important; color: {PAPER};
}}
.bw-void .bw-field {{ background-image: none; }}

/* scramble targets get stable width */
[data-scramble] {{ white-space: pre; }}

/* kill Quasar page padding fighting the field */
.nicegui-content {{ padding: 0 !important; }}
"""


def apply() -> None:
    ui.add_head_html('<link rel="preload" as="style" href="/static/vendor/fonts.css">')
    ui.add_css(CSS)
