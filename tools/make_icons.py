#!/usr/bin/env python3
"""Generate the cluster's SVG icon set into ``assets/icons``.

Telltale colours are fixed by convention (red = stop, amber = caution,
green/blue = status), so each symbol is emitted already coloured rather than
being tinted at runtime — that keeps the QML free of shader effects, which are
not available on every GL stack.

Run ``python3 tools/make_icons.py`` after editing to regenerate.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "icons"

RED = "#E8493C"
AMBER = "#F5A623"
GREEN = "#4CD964"
BLUE = "#4A9BF0"
WHITE = "#FFFFFF"
DIM = "#C9D4DF"

# --------------------------------------------------------------------------
# Shape fragments.  Each entry is a callable taking the colour and returning
# the inner SVG markup for a 48x48 viewBox.
# --------------------------------------------------------------------------


def fuel_pump(c: str) -> str:
    return f"""
  <path fill="{c}" fill-rule="evenodd" d="M11 8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v33H11z
           M15 8h6v6h-6z"/>
  <rect x="8" y="41" width="24" height="4" rx="1.4" fill="{c}"/>
  <path fill="{c}" d="M32 16h3.4a2.6 2.6 0 0 1 2.6 2.6V32a2 2 0 0 0 4 0V21.3l-3.8-3.8 2-2 4.2 4.2
           c.4.4.6.9.6 1.4V32a5 5 0 0 1-10 0V19.6c0-.4-.3-.6-.6-.6H32z"/>"""


def coolant(c: str) -> str:
    return f"""
  <path fill="none" stroke="{c}" stroke-width="2.8" d="M20.5 27.5V11a3.5 3.5 0 0 1 7 0v16.5a6.5 6.5 0 1 1-7 0z"/>
  <circle cx="24" cy="33.5" r="3.2" fill="{c}"/>
  <rect x="22.6" y="15" width="2.8" height="12" rx="1.4" fill="{c}"/>
  <path fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round"
        d="M4 42c2.2-2.4 4.4-2.4 6.6 0s4.4 2.4 6.6 0M30.8 42c2.2-2.4 4.4-2.4 6.6 0s4.4 2.4 6.6 0"/>"""


def arrow(c: str, flip: bool) -> str:
    tf = ' transform="translate(48,0) scale(-1,1)"' if flip else ""
    return f'\n  <path fill="{c}"{tf} d="M30 6 6 24l24 18v-9h12V15H30z"/>'


def high_beam(c: str) -> str:
    return f"""
  <path fill="{c}" d="M8 12h7c7.2 0 13 5.4 13 12s-5.8 12-13 12H8z"/>
  <g stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M32 15h11M32 24h11M32 33h11"/>
  </g>"""


def low_beam(c: str) -> str:
    return f"""
  <path fill="{c}" d="M8 12h7c7.2 0 13 5.4 13 12s-5.8 12-13 12H8z"/>
  <g stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M33 13l9 5M33 22l9 5M33 31l9 5"/>
  </g>"""


def position_light(c: str) -> str:
    return f"""
  <ellipse cx="24" cy="24" rx="7" ry="9" fill="{c}"/>
  <g stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M36 15h8M36 24h8M36 33h8M12 15H4M12 24H4M12 33H4"/>
  </g>"""


def fog(c: str, rear: bool) -> str:
    rays = "M33 13l9 5M33 22l9 5M33 31l9 5" if not rear else "M33 18h10M33 27h10M33 36h10"
    return f"""
  <path fill="{c}" d="M6 12h7c7.2 0 13 5.4 13 12s-5.8 12-13 12H6z"/>
  <g stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="{rays}"/>
  </g>
  <path fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"
        d="M30 10c-3 3-3 6 0 9s3 6 0 9 -3 6 0 9"/>"""


def circle_bang(c: str) -> str:
    """The classic brake / stop telltale: (!) between two bracket arcs."""
    return f"""
  <circle cx="24" cy="24" r="12.5" fill="none" stroke="{c}" stroke-width="3"/>
  <rect x="22.2" y="15" width="3.6" height="12" rx="1.8" fill="{c}"/>
  <circle cx="24" cy="31.5" r="2.2" fill="{c}"/>
  <g fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M8.5 15.5a17 17 0 0 0 0 17M39.5 15.5a17 17 0 0 1 0 17"/>
  </g>"""


def circle_p(c: str) -> str:
    return f"""
  <circle cx="24" cy="24" r="12.5" fill="none" stroke="{c}" stroke-width="3"/>
  <path fill="{c}" d="M19.5 15.5h6a5.2 5.2 0 0 1 0 10.4h-2.6v6.6h-3.4zm3.4 3.2v4h2.6a2 2 0 0 0 0-4z"/>
  <g fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M8.5 15.5a17 17 0 0 0 0 17M39.5 15.5a17 17 0 0 1 0 17"/>
  </g>"""


def abs_icon(c: str) -> str:
    return f"""
  <circle cx="24" cy="24" r="12.5" fill="none" stroke="{c}" stroke-width="3"/>
  <text x="24" y="29.5" font-family="sans-serif" font-size="12" font-weight="bold"
        text-anchor="middle" fill="{c}">ABS</text>
  <g fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M8.5 15.5a17 17 0 0 0 0 17M39.5 15.5a17 17 0 0 1 0 17"/>
  </g>"""


def _car_body(c: str) -> str:
    return (f'<path fill="{c}" d="M12 30a3 3 0 0 1-3-3v-4.5c0-.8.3-1.5.9-2l2.3-2.1 1.7-4.6'
            f'A3.5 3.5 0 0 1 17.2 11h13.6a3.5 3.5 0 0 1 3.3 2.3l1.7 4.6 2.3 2.1c.6.5.9 1.2.9 2V27'
            f'a3 3 0 0 1-3 3z"/>')


def esc(c: str, off: bool) -> str:
    extra = (f'\n  <text x="24" y="44" font-family="sans-serif" font-size="11" font-weight="bold"'
             f' text-anchor="middle" fill="{c}">OFF</text>') if off else ""
    skid = "" if off else (
        f'\n  <g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round">'
        f'<path d="M12 43c3.5-3 3.5-6 0-9M36 43c-3.5-3-3.5-6 0-9"/></g>')
    return f'\n  {_car_body(c)}{skid}{extra}'


def traction_off(c: str) -> str:
    return f"""
  {_car_body(c)}
  <g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round">
    <path d="M12 39c3.5-3 3.5-6 0-9M36 39c-3.5-3-3.5-6 0-9"/>
  </g>
  <path stroke="{c}" stroke-width="3" stroke-linecap="round" d="M9 9l30 30"/>"""


def airbag(c: str) -> str:
    return f"""
  <path fill="{c}" d="M10 40a3 3 0 0 1-3-3V21a4 4 0 0 1 8 0v6h6a3 3 0 0 1 0 6h-4v7z"/>
  <circle cx="11" cy="12" r="4.5" fill="{c}"/>
  <circle cx="33" cy="26" r="9" fill="none" stroke="{c}" stroke-width="3"/>
  <path stroke="{c}" stroke-width="3" stroke-linecap="round" d="M33 35v5"/>"""


def check_engine(c: str) -> str:
    return f"""
  <path fill="{c}" d="M14 16h4v-4h10v4h5l4 5h3v-4h4v16h-4v-4h-3l-4 5H20v-5h-6v5H6V16h8z"/>"""


def oil(c: str) -> str:
    return f"""
  <path fill="{c}" d="M6 26h6l4-4h9c4.5 0 8 2.4 9.6 6H42a2 2 0 0 1 0 4h-3v3a3 3 0 0 1-3 3H12
           a6 6 0 0 1-6-6z"/>
  <path fill="{c}" d="M31 8c2.6 3 5 5.7 5 8a5 5 0 0 1-10 0c0-2.3 2.4-5 5-8z"/>"""


def battery(c: str) -> str:
    return f"""
  <path fill="{c}" d="M6 15h4v-3h8v3h12v-3h8v3h4a2 2 0 0 1 2 2v18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V17a2 2 0 0 1 2-2z"/>
  <g stroke="#000" stroke-width="2.6" stroke-linecap="round" opacity="0.85">
    <path d="M10 24h7M13.5 20.5v7M31 24h7"/>
  </g>"""


def tpms(c: str) -> str:
    return f"""
  <path fill="{c}" fill-rule="evenodd" d="M10 12h28c1.6 0 2.6 1.8 1.8 3.2-1.9 3.3-2.8 7.2-2.8 11.3
           0 3.6.7 7 2 10.1.5 1.3-.4 2.7-1.8 2.7H10.8c-1.4 0-2.3-1.4-1.8-2.7 1.3-3.1 2-6.5 2-10.1
           0-4.1-.9-8-2.8-11.3C7.4 13.8 8.4 12 10 12z
           M22.2 17h3.6v11h-3.6z M22 31h4v4h-4z"/>
  <path stroke="{c}" stroke-width="2.6" stroke-linecap="round" d="M6 43h36"/>"""


def seatbelt(c: str) -> str:
    return f"""
  <circle cx="17" cy="10" r="5" fill="{c}"/>
  <path fill="{c}" d="M11 18h7l14 24h-7l-3.4-6H14a3 3 0 0 1-3-3z"/>
  <path fill="{c}" d="M27 17h7L23 42h-7z" opacity="0.55"/>"""


def door_open(c: str) -> str:
    return f"""
  <path fill="{c}" d="M20 10h8v28h-8z"/>
  <path fill="{c}" d="M18 14v20H8a2 2 0 0 1-2-2V22c0-.7.3-1.4.9-1.8z"/>
  <path fill="{c}" d="M30 14v20h10a2 2 0 0 0 2-2V22c0-.7-.3-1.4-.9-1.8z"/>
  <path stroke="{c}" stroke-width="3" stroke-linecap="round" d="M12 42h24"/>"""


def washer(c: str) -> str:
    return f"""
  <path fill="{c}" d="M14 22h20l4 16H10z"/>
  <path fill="none" stroke="{c}" stroke-width="2.8" stroke-linecap="round"
        d="M24 20V9M24 9c-4 0-6 2-6 5M24 9c4 0 6 2 6 5"/>
  <g stroke="{c}" stroke-width="2.6" stroke-linecap="round">
    <path d="M8 12c-2 2-2 4 0 6M40 12c2 2 2 4 0 6"/>
  </g>"""


def glow_plug(c: str) -> str:
    return f"""
  <path fill="none" stroke="{c}" stroke-width="3.4" stroke-linecap="round"
        d="M10 12h6c4 0 4 6 0 6h-4c-4 0-4 6 0 6h6c4 0 4 6 0 6h-6"/>
  <path fill="none" stroke="{c}" stroke-width="3.4" stroke-linecap="round"
        d="M34 12c4 0 4 6 0 6s-4 6 0 6 4 6 0 6"/>"""


def cruise(c: str) -> str:
    return f"""
  <circle cx="24" cy="24" r="17" fill="none" stroke="{c}" stroke-width="3"/>
  <path fill="{c}" d="M23 24l11-9 1.6 2-9.6 10.4A2.2 2.2 0 1 1 23 24z"/>
  <g stroke="{c}" stroke-width="2.6" stroke-linecap="round">
    <path d="M24 7v3M41 24h-3M24 41v-3M7 24h3"/>
  </g>"""


def eps(c: str) -> str:
    return f"""
  <circle cx="21" cy="26" r="15" fill="none" stroke="{c}" stroke-width="3"/>
  <circle cx="21" cy="26" r="4.5" fill="{c}"/>
  <path stroke="{c}" stroke-width="3" stroke-linecap="round" d="M21 21.5V13M17 28.5L8 34M25 28.5l9 5.5"/>
  <rect x="38" y="6" width="4" height="14" rx="2" fill="{c}"/>
  <circle cx="40" cy="25" r="2.4" fill="{c}"/>"""


def immobilizer(c: str) -> str:
    return f"""
  {_car_body(c)}
  <circle cx="34" cy="36" r="6" fill="none" stroke="{c}" stroke-width="3"/>
  <path stroke="{c}" stroke-width="3" stroke-linecap="round" d="M34 42v4M31.5 44h5"/>"""


def lane_departure(c: str) -> str:
    return f"""
  <g stroke="{c}" stroke-width="3.4" stroke-linecap="round">
    <path d="M9 8L4 40M39 8l5 32"/>
  </g>
  <path fill="{c}" d="M17 34a2.5 2.5 0 0 1-2.5-2.5v-4c0-.7.3-1.3.8-1.7l1.9-1.7 1.4-3.8A3 3 0 0 1 21.4 18h5.2
           a3 3 0 0 1 2.8 2.3l1.4 3.8 1.9 1.7c.5.4.8 1 .8 1.7v4A2.5 2.5 0 0 1 31 34z"/>"""


def fca(c: str) -> str:
    return f"""
  {_car_body(c)}
  <g fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round">
    <path d="M15 40c2.6-2.6 5.4-4 9-4s6.4 1.4 9 4M20 45c1.4-1.2 2.6-1.8 4-1.8s2.6.6 4 1.8"/>
  </g>"""


ICONS: dict[str, str] = {
    "fuel_pump": fuel_pump(DIM),
    "fuel_pump_white": fuel_pump(WHITE),
    "low_fuel": fuel_pump(AMBER),
    "coolant": coolant(DIM),
    "temp_warn": coolant(RED),
    "turn_left": arrow(GREEN, False),
    "turn_right": arrow(GREEN, True),
    "high_beam": high_beam(BLUE),
    "low_beam": low_beam(GREEN),
    "position_light": position_light(GREEN),
    "fog_front": fog(GREEN, False),
    "fog_rear": fog(AMBER, True),
    "brake": circle_bang(RED),
    "park_brake": circle_p(RED),
    "abs": abs_icon(AMBER),
    "esc": esc(AMBER, False),
    "esc_off": esc(AMBER, True),
    "traction_off": traction_off(AMBER),
    "airbag": airbag(RED),
    "check_engine": check_engine(AMBER),
    "oil": oil(RED),
    "battery": battery(RED),
    "tpms": tpms(AMBER),
    "seatbelt": seatbelt(RED),
    "door_open": door_open(RED),
    "washer": washer(AMBER),
    "glow_plug": glow_plug(AMBER),
    "cruise": cruise(GREEN),
    "cruise_ready": cruise(WHITE),
    "eps": eps(AMBER),
    "immobilizer": immobilizer(AMBER),
    "lane_departure": lane_departure(GREEN),
    "lane_warn": lane_departure(AMBER),
    "fca": fca(RED),
}

TEMPLATE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">{}\n</svg>\n'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in ICONS.items():
        (OUT / f"{name}.svg").write_text(TEMPLATE.format(body.rstrip()))
    print(f"wrote {len(ICONS)} icons to {OUT}")


if __name__ == "__main__":
    main()
