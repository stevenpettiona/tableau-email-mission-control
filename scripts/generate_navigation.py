#!/usr/bin/env python3
"""Generates interactive navigation strip zones for all 4 dashboards.

Writes:
  parts/navigation/nav-{slug}.xml   — standalone zone XML per dashboard (reference)
  parts/dashboards/*.xml            — patches static text nav zones → button zones

The nav strip shows 4 tabs. On each dashboard, one tab is "active" (accent bg,
bold) and the others are "inactive" (dark bg, regular weight).

Run once:
    python3 scripts/generate_navigation.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAV_DIR = ROOT / "parts" / "navigation"
DASH_DIR = ROOT / "parts" / "dashboards"

# --- Colours (our palette) ---
ACTIVE_BG = "#6B3FA0"    # accent purple — active/current tab
INACTIVE_BG = "#1F1045"  # nav strip dark purple — inactive tabs
NAV_STRIP_BG = "#1F1045" # outer container background
TEXT_COLOR = "#ffffff"
FONT = "Poppins"
FONT_SIZE = "9"

# Nav dimensions (900px tall dashboard: 4222 units = 38px)
NAV_OUTER_H = "4222"
NAV_OUTER_Y = "4888"   # starts right after the 44px hero banner (4888 units)
# fixed-size is in pixels; is-fixed prevents the strip from growing/shrinking
NAV_FIXED_SIZE = "38"

# --- The 4 tabs in order ---
# (friendly_name, caption, window_uuid)
TABS = [
    ("Overview",             "Overview",             "{C5677F52-EC91-4676-970C-B2B74BC6CBAC}"),
    ("Campaign Performance", "Campaign Performance", "{A32A9061-EDF3-40B3-93CD-E1B12EA58AFA}"),
    ("Audience Breakdown",   "Audience Breakdown",   "{009BEC44-BB31-41EF-B95B-51262EC806BA}"),
    ("Email Pipeline",       "Email → Pipeline", "{6C7A0900-EC67-48CA-B906-CCEB95344A45}"),
]

# --- Per-dashboard config ---
# (slug, dashboard_file, active_tab_index, outer_zone_id, inner_zone_ids)
DASHBOARDS = [
    ("overview",             "overview-dashboard.xml",             0, "1114", ["1115", "1116", "1117", "1118"]),
    ("campaign-performance", "campaign-performance-dashboard.xml", 1, "1305", ["1306", "1307", "1308", "1309"]),
    ("audience-breakdown",   "audience-breakdown-dashboard.xml",   2, "1508", ["1509", "1510", "1511", "1512"]),
    ("pipeline",             "pipeline-dashboard.xml",             3, "1713", ["1714", "1715", "1716", "1717"]),
]

ZONE_WIDTH = 25000
X_POSITIONS = [0, 25000, 50000, 75000]


def button_zone_xml(friendly_name: str, caption: str, window_id: str,
                    zone_id: str, x: int, is_active: bool) -> str:
    bg = ACTIVE_BG if is_active else INACTIVE_BG
    bold_attr = f" bold='true'" if is_active else ""
    return f"""\
<zone friendly-name='{friendly_name}' h='{NAV_OUTER_H}' id='{zone_id}' type-v2='text' w='{ZONE_WIDTH}' x='{x}' y='{NAV_OUTER_Y}'>
  <formatted-text>
    <run{bold_attr} fontcolor='{TEXT_COLOR}' fontalignment='1' fontname='{FONT}' fontsize='{FONT_SIZE}'>{caption}</run>
  </formatted-text>
  <zone-style>
    <format attr='background-color' value='{bg}' />
    <format attr='border-color' value='#000000' />
    <format attr='border-style' value='none' />
    <format attr='border-width' value='0' />
    <format attr='margin' value='4' />
  </zone-style>
</zone>"""


def nav_strip_xml(outer_id: str, inner_ids: list[str], active_idx: int) -> str:
    """Returns the complete nav strip zone block."""
    buttons = []
    for i, (tab_x, (friendly, caption, window_id)) in enumerate(zip(X_POSITIONS, TABS)):
        buttons.append(button_zone_xml(
            friendly, caption, window_id,
            inner_ids[i], tab_x, is_active=(i == active_idx),
        ))

    inner_xml = "".join(buttons)
    return (
        f"<zone fixed-size='{NAV_FIXED_SIZE}' friendly-name='Navigation'"
        f" h='{NAV_OUTER_H}' id='{outer_id}' is-fixed='true'"
        f" layout-strategy-id='distribute-evenly' param='horz'"
        f" type-v2='layout-flow' w='100000' x='0' y='{NAV_OUTER_Y}'>\n"
        f"{inner_xml}\n"
        f"<zone-style>\n"
        f"  <format attr='background-color' value='{NAV_STRIP_BG}' />\n"
        f"  <format attr='border-color' value='#000000' />\n"
        f"  <format attr='border-style' value='none' />\n"
        f"  <format attr='border-width' value='0' />\n"
        f"  <format attr='margin' value='1' />\n"
        f"</zone-style>\n"
        f"</zone>"
    )


# ---------------------------------------------------------------------------
# Zone-block extraction — properly handles nested <zone> depth so we never
# accidentally swallow adjacent siblings (e.g. the filter bar).
# ---------------------------------------------------------------------------

_ZONE_OPEN_RE = re.compile(r"<zone\b[ \t\n>]")  # <zone followed by space/newline/> only
_ZONE_CLOSE = "</zone>"


def _find_zone_block(text: str, zone_id: str) -> tuple[int, int] | None:
    """Return (start, end) byte offsets for the complete zone with the given id.

    Works by counting open/close zone tags from the matched opening tag, which
    correctly handles any depth of nesting without depending on attribute order
    or specific surrounding siblings.
    """
    id_pattern = re.compile(rf"<zone\b[^>]*\bid='{re.escape(zone_id)}'[^>]*>")
    m = id_pattern.search(text)
    if not m:
        return None

    start = m.start()
    pos = m.end()  # just past the opening >
    depth = 1

    while depth > 0:
        open_m = _ZONE_OPEN_RE.search(text, pos)
        close_pos = text.find(_ZONE_CLOSE, pos)

        if close_pos == -1:
            return None  # malformed XML

        if open_m is not None and open_m.start() < close_pos:
            # There is another <zone before the next </zone>.
            # Determine if it is self-closing (<zone ... />) or not.
            tag_end = text.index(">", open_m.start())
            if text[tag_end - 1] == "/":
                # Self-closing — doesn't add to depth; skip past it.
                pos = tag_end + 1
            else:
                depth += 1
                pos = tag_end + 1
        else:
            depth -= 1
            pos = close_pos + len(_ZONE_CLOSE)

    return start, pos


def write_nav_part(slug: str, active_idx: int,
                   outer_id: str, inner_ids: list[str]) -> None:
    """Write a standalone navigation part file (reference/documentation)."""
    content = (
        f"<!--\n"
        f"  part-type: navigation\n"
        f"  dashboard: {slug}\n"
        f"  active-tab: {TABS[active_idx][0]}\n"
        f"  last-modified: 2026-05-04\n"
        f"\n"
        f"  This zone is embedded verbatim in parts/dashboards/{slug}-dashboard.xml\n"
        f"  within the outer layout-basic zone, replacing the static text nav strip.\n"
        f"  Active tab uses background {ACTIVE_BG} (accent purple).\n"
        f"  Inactive tabs use {INACTIVE_BG} (nav strip dark purple).\n"
        f"-->\n"
        f"{nav_strip_xml(outer_id, inner_ids, active_idx)}\n"
    )
    (NAV_DIR / f"nav-{slug}.xml").write_text(content, encoding="utf-8")
    print(f"  parts/navigation/nav-{slug}.xml")


def patch_dashboard(filename: str, active_idx: int,
                    outer_id: str, inner_ids: list[str]) -> None:
    """Replace the nav strip zone in a dashboard file with the button-zone version."""
    path = DASH_DIR / filename
    text = path.read_text(encoding="utf-8")

    bounds = _find_zone_block(text, outer_id)
    if bounds is None:
        print(f"  [warn] nav strip (id={outer_id}) not found in {filename}")
        return

    start, end = bounds
    new_strip = nav_strip_xml(outer_id, inner_ids, active_idx)
    new_text = text[:start] + new_strip + text[end:]

    path.write_text(new_text, encoding="utf-8")
    print(f"  parts/dashboards/{filename}")


def main() -> None:
    NAV_DIR.mkdir(parents=True, exist_ok=True)
    print("Writing navigation part files:")
    for slug, dash_file, active_idx, outer_id, inner_ids in DASHBOARDS:
        write_nav_part(slug, active_idx, outer_id, inner_ids)

    print("Patching dashboard files:")
    for slug, dash_file, active_idx, outer_id, inner_ids in DASHBOARDS:
        patch_dashboard(dash_file, active_idx, outer_id, inner_ids)


if __name__ == "__main__":
    main()
