#!/usr/bin/env python3
"""Generates interactive navigation strip zones for all 4 dashboards.

Writes:
  parts/navigation/nav-{slug}.xml   — standalone zone XML per dashboard (reference)
  parts/dashboards/*.xml            — patches nav strip zones in dashboard files

The nav strip shows 4 tabs. On each dashboard, one tab is "active" (accent bg,
bold Tableau Bold) and the others are "inactive" (dark bg, regular weight).
Navigation uses type-v2='dashboard-object' button zones with goto-sheet actions.

Run once:
    python3 scripts/generate_navigation.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAV_DIR = ROOT / "parts" / "navigation"
DASH_DIR = ROOT / "parts" / "dashboards"

# --- Colours (matched to user-edited TWB) ---
ACTIVE_BG = "#7a48b9"    # accent purple — active/current tab
INACTIVE_BG = "#4b2b72"  # hero banner dark purple — inactive tabs
NAV_STRIP_BG = "#4b2b72" # outer container background
TEXT_COLOR = "#ffffff"
FONT_SIZE = "9"

# Nav dimensions (matched to user-edited TWB)
NAV_OUTER_H = "3333"   # 30px
NAV_OUTER_Y = "4192"   # absolute y — right after HeroBanner in vert flow
NAV_FIXED_SIZE = "30"  # px, pinned height
BUTTON_H = "3334"      # inner button zone height
BUTTON_Y = "4222"      # absolute y of inner button zones

# Tab widths and x-positions (must sum to 100000)
TAB_WIDTHS = [25037, 25036, 24964, 24963]
X_POSITIONS = [0, 25037, 50073, 75037]

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
    ("overview",             "overview-dashboard.xml",             0, "1131", ["1129", "1132", "1133", "1134"]),
    ("campaign-performance", "campaign-performance-dashboard.xml", 1, "1344", ["1345", "1346", "1347", "1348"]),
    ("audience-breakdown",   "audience-breakdown-dashboard.xml",   2, "1544", ["1545", "1546", "1547", "1548"]),
    ("pipeline",             "pipeline-dashboard.xml",             3, "1744", ["1745", "1746", "1747", "1748"]),
]


def button_zone_xml(friendly_name: str, caption: str, window_id: str,
                    zone_id: str, x: int, w: int, is_active: bool) -> str:
    bg = ACTIVE_BG if is_active else INACTIVE_BG
    if is_active:
        font_style = f"bold='true' fontcolor='{TEXT_COLOR}' fontname='Tableau Bold' fontsize='{FONT_SIZE}'"
    else:
        font_style = f"fontcolor='{TEXT_COLOR}' fontsize='{FONT_SIZE}'"
    return f"""\
<zone h='{BUTTON_H}' id='{zone_id}' type-v2='dashboard-object' w='{w}' x='{x}' y='{BUTTON_Y}'>
  <button action='tabdoc:goto-sheet window-id=&quot;{window_id}&quot;' button-type='text'>
    <button-visual-state>
      <caption>{caption}</caption>
      <button-caption-font-style {font_style} />
      <format attr='background-color' value='{bg}' />
    </button-visual-state>
  </button>
  <zone-style>
    <format attr='border-color' value='#ffffff' />
    <format attr='border-style' value='solid' />
    <format attr='border-width' value='1' />
    <format attr='margin' value='4' />
  </zone-style>
</zone>"""


def nav_strip_xml(outer_id: str, inner_ids: list[str], active_idx: int) -> str:
    """Returns the complete nav strip zone block."""
    buttons = []
    for i, (tab_x, tab_w, (friendly, caption, window_id)) in enumerate(
        zip(X_POSITIONS, TAB_WIDTHS, TABS)
    ):
        buttons.append(button_zone_xml(
            friendly, caption, window_id,
            inner_ids[i], tab_x, tab_w, is_active=(i == active_idx),
        ))

    inner_xml = "\n".join(buttons)
    return (
        f"<zone friendly-name='Navigation' fixed-size='{NAV_FIXED_SIZE}'"
        f" h='{NAV_OUTER_H}' id='{outer_id}' is-fixed='true'"
        f" layout-strategy-id='distribute-evenly' param='horz'"
        f" type-v2='layout-flow' w='100000' x='0' y='{NAV_OUTER_Y}'>\n"
        f"{inner_xml}\n"
        f"<zone-style>\n"
        f"  <format attr='border-color' value='#000000' />\n"
        f"  <format attr='border-style' value='none' />\n"
        f"  <format attr='border-width' value='0' />\n"
        f"  <format attr='background-color' value='{NAV_STRIP_BG}' />\n"
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
        f"  within the Dashboard Container vert layout-flow, as the second child\n"
        f"  (after HeroBanner). Active tab uses background {ACTIVE_BG}.\n"
        f"  Inactive tabs use {INACTIVE_BG}.\n"
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
