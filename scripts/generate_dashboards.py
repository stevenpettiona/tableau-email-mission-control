#!/usr/bin/env python3
"""One-shot generator for the 4 dashboard parts.

Emits one part file per dashboard under parts/dashboards/. Each contains:
  - SECTION:DASHBOARD — the <dashboard> element
  - SECTION:WINDOW-ENTRY — corresponding <window class='dashboard'> entry

Layout strategy (minimum-viable for Tableau to open and render):
  Each dashboard is 1366x900 fixed. A vertical layout-flow holds:
    - 44px hero banner (#2D1B5E text title)
    - 38px nav-strip (4 nav buttons; type='dashboard' targeting the other dashboards)
    - 48px global filter bar (7 parameter quick-filter zones)
    - body — varies per dashboard, contains the worksheets in tiled containers
    - 32px footer

Zone dimensions in Tableau use fractional units (out of 100000) — generator
converts pixel sizes appropriately.

Run once:
    python3 scripts/generate_dashboards.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "parts" / "dashboards"
MANIFEST = ROOT / "parts" / "manifest.json"

W = 1366
H = 900


def make_uuid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


# Predetermine UUIDs so cross-dashboard nav buttons can reference them.
DASHBOARDS = [
    ("Email Overview",            "overview",            make_uuid()),
    ("Email Campaign Performance", "campaign-performance", make_uuid()),
    ("Email Audience Breakdown",  "audience-breakdown",  make_uuid()),
    ("Email Pipeline",            "pipeline",            make_uuid()),
]
DASHBOARD_BY_NAME = {name: (slug, gid) for (name, slug, gid) in DASHBOARDS}


# ---------- helpers ----------

def zone_open(zid: int, x: int, y: int, w: int, h: int, ztype: str = "",
              extra: str = "") -> str:
    type_attr = f" type='{ztype}'" if ztype else ""
    return (
        f"<zone h='{h}' id='{zid}'{type_attr} w='{w}' x='{x}' y='{y}'{extra}>"
    )


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def zone_text(zid: int, x: int, y: int, w: int, h: int, text: str,
              bg: str = "#FFFFFF", fg: str = "#111827",
              size: int = 12, weight: str = "regular",
              align: str = "left") -> str:
    bold_attr = " bold='true'" if weight in ("bold", "semibold") else ""
    return f"""<zone h='{h}' id='{zid}' type-v2='text' w='{w}' x='{x}' y='{y}'>
  <formatted-text>
    <run fontcolor='{fg}' fontname='Poppins' fontsize='{size}'{bold_attr}>{xml_escape(text)}</run>
  </formatted-text>
</zone>"""


def zone_worksheet(zid: int, x: int, y: int, w: int, h: int, name: str) -> str:
    return f"<zone h='{h}' id='{zid}' name='{name}' w='{w}' x='{x}' y='{y}' />"


def zone_param(zid: int, x: int, y: int, w: int, h: int, param_name: str,
               caption: str) -> str:
    # Render parameter zones as plain text labels for now — Tableau-native
    # parameter quick-filter zone schema is uncertain across versions, so we
    # ship a visible label and let the user wire up the actual control after
    # opening in Tableau Desktop (Dashboard menu → Show Parameter).
    return zone_text(zid, x, y, w, h, caption, bg="#FFFFFF", fg="#6B7280",
                     size=10, weight="regular", align="left")


def zone_nav(zid: int, x: int, y: int, w: int, h: int, label: str,
             target_dashboard: str, active: bool) -> str:
    # Same caveat: dashboard navigation button schema is uncertain. Emit a
    # styled text zone as a placeholder; nav actions can be added in Tableau
    # Desktop (Dashboard → Actions → Add Navigate Action).
    bg = "#6B3FA0" if active else "#1F1045"
    return zone_text(zid, x, y, w, h, label, bg=bg, fg="#FFFFFF",
                     size=12, weight="semibold", align="center")


# ---------- shared chrome ----------

def chrome_zones(start_id: int, active_dashboard: str, body_zones_xml: str,
                 body_height: int) -> tuple[str, int]:
    """Return (chrome+body XML, next_zone_id). Caller wraps in root layout-basic."""
    zid = start_id
    parts: list[str] = []

    # Hero banner — 44px
    hero_zid, zid = zid, zid + 1
    hero_h_frac = int(44 / H * 100000)
    parts.append(
        zone_text(hero_zid, 0, 0, 100000, hero_h_frac,
                  "Marketing Mission Control — Email Performance",
                  bg="#2D1B5E", fg="#FFFFFF", size=13, weight="semibold",
                  align="left")
    )

    # Nav strip — 38px
    nav_y_frac = hero_h_frac
    nav_h_frac = int(38 / H * 100000)
    nav_zone_id = zid; zid += 1
    nav_inner = []
    btn_count = len(DASHBOARDS)
    btn_w_frac = int(100000 / btn_count)
    for i, (dname, _slug, _gid) in enumerate(DASHBOARDS):
        btn_zid = zid; zid += 1
        nav_inner.append(zone_nav(
            btn_zid,
            i * btn_w_frac, 0,
            btn_w_frac, 100000,
            label=dname.replace("Email ", "").replace(
                "Pipeline", "Email → Pipeline"),
            target_dashboard=dname,
            active=(dname == active_dashboard),
        ))
    parts.append(f"""<zone h='{nav_h_frac}' id='{nav_zone_id}' type-v2='layout-flow' w='100000' x='0' y='{nav_y_frac}' param='horz' layout-strategy-id='distribute-evenly'>
{''.join(nav_inner)}
</zone>""")

    # Filter bar — 48px, 7 parameter dropdowns
    filt_y_frac = hero_h_frac + nav_h_frac
    filt_h_frac = int(48 / H * 100000)
    filt_zid = zid; zid += 1
    filters = [
        ("[Date Range Days]", "DATE RANGE"),
        ("[Platform Filter]", "PLATFORM"),
        ("[Program Type Filter]", "PROGRAM TYPE"),
        ("[Direction Filter]", "DIRECTION"),
        ("[Country Filter]", "COUNTRY"),
        ("[Company Size Filter]", "COMPANY SIZE"),
        ("[Product Filter]", "PRODUCT"),
    ]
    filt_inner = []
    n = len(filters)
    cell_w = int(100000 / n)
    for i, (param, label) in enumerate(filters):
        cell_zid = zid; zid += 1
        filt_inner.append(zone_param(
            cell_zid, i * cell_w, 0, cell_w, 100000, param, label))
    parts.append(f"""<zone h='{filt_h_frac}' id='{filt_zid}' type-v2='layout-flow' w='100000' x='0' y='{filt_y_frac}' param='horz' layout-strategy-id='distribute-evenly'>
{''.join(filt_inner)}
</zone>""")

    # Body
    body_y_frac = filt_y_frac + filt_h_frac
    body_h_frac = int(body_height / H * 100000)
    body_zid = zid; zid += 1
    parts.append(f"""<zone h='{body_h_frac}' id='{body_zid}' type-v2='layout-basic' w='100000' x='0' y='{body_y_frac}'>
{body_zones_xml}
</zone>""")

    # Footer — 32px
    foot_y_frac = body_y_frac + body_h_frac
    foot_h_frac = 100000 - foot_y_frac
    foot_zid = zid; zid += 1
    parts.append(zone_text(
        foot_zid, 0, foot_y_frac, 100000, foot_h_frac,
        "Source: Redshift mart.fct_marketing_email_engagement · dim_marketing_campaign · dim_marketing_audience  —  Open Rate Target: TBC | CTR Target: TBC | Unsub Threshold: TBC",
        bg="#FFFFFF", fg="#9CA3AF", size=10, weight="regular", align="left",
    ))

    return "\n".join(parts), zid


# ---------- per-dashboard body builders ----------

def overview_body(start_id: int) -> tuple[str, int]:
    """Row 1: 8 KPI cells (110px). Row 2: trend left + platform split right (628px)."""
    zid = start_id
    body_h = 738
    kpi_h_frac = int(110 / body_h * 100000)
    chart_h_frac = 100000 - kpi_h_frac

    parts = []
    # KPI row
    kpi_row_zid = zid; zid += 1
    kpi_inner = []
    kpi_sheets = [
        "[SC] Sends", "[SC] Opens", "[SC] Clicks", "[SC] Unsubscribes",
        "[SC] Open Rate", "[SC] CTR", "[SC] CTOR", "[SC] Unsub Rate",
    ]
    cell_w = int(100000 / len(kpi_sheets))
    for i, name in enumerate(kpi_sheets):
        cell_zid = zid; zid += 1
        kpi_inner.append(zone_worksheet(cell_zid, i * cell_w, 0, cell_w, 100000, name))
    parts.append(f"""<zone h='{kpi_h_frac}' id='{kpi_row_zid}' type-v2='layout-flow' w='100000' x='0' y='0' param='horz' layout-strategy-id='distribute-evenly'>
{''.join(kpi_inner)}
</zone>""")

    # Chart row
    chart_row_zid = zid; zid += 1
    left_w = int(0.65 * 100000)
    right_w = 100000 - left_w
    left_zid = zid; zid += 1
    right_zid = zid; zid += 1
    chart_inner = (
        zone_worksheet(left_zid, 0, 0, left_w, 100000, "[BC] Email Trend") +
        zone_worksheet(right_zid, left_w, 0, right_w, 100000, "[BC] Platform Split")
    )
    parts.append(f"""<zone h='{chart_h_frac}' id='{chart_row_zid}' type-v2='layout-basic' w='100000' x='0' y='{kpi_h_frac}'>
{chart_inner}
</zone>""")

    return "\n".join(parts), zid


def campaign_body(start_id: int) -> tuple[str, int]:
    """36px pill bar + 32px summary + 670px campaign table."""
    zid = start_id
    body_h = 738
    pill_h = int(36 / body_h * 100000)
    summary_h = int(32 / body_h * 100000)
    table_h = 100000 - pill_h - summary_h

    parts = []
    pill_zid = zid; zid += 1
    parts.append(zone_text(
        pill_zid, 0, 0, 100000, pill_h,
        "ALL  |  BATCH & BLAST  |  EMAIL NURTURE  |  SALES EMAIL  |  NEWSLETTER  |  EVENT / WEBINAR  |  TRAINING  |  DEFAULT",
        bg="#FFFFFF", fg="#6B7280", size=10, weight="regular", align="left"))
    sum_zid = zid; zid += 1
    parts.append(zone_text(
        sum_zid, 0, pill_h, 100000, summary_h,
        "Showing all programs",
        bg="#FFFFFF", fg="#6B7280", size=11, weight="regular", align="left"))
    table_zid = zid; zid += 1
    parts.append(zone_worksheet(
        table_zid, 0, pill_h + summary_h, 100000, table_h, "[BC] Campaign Table"))

    return "\n".join(parts), zid


def audience_body(start_id: int) -> tuple[str, int]:
    """2x2 grid + 32px summary."""
    zid = start_id
    body_h = 738
    summary_h = int(32 / body_h * 100000)
    grid_h = 100000 - summary_h
    half = 50000

    parts = []
    grid_zid = zid; zid += 1
    z1 = zid; zid += 1
    z2 = zid; zid += 1
    z3 = zid; zid += 1
    z4 = zid; zid += 1
    grid_inner = (
        zone_worksheet(z1, 0, 0, half, grid_h // 2, "[BC] Country Breakdown") +
        zone_worksheet(z2, half, 0, half, grid_h // 2, "[BC] Company Size Breakdown") +
        zone_worksheet(z3, 0, grid_h // 2, half, grid_h - grid_h // 2, "[BC] Lifecycle Stage Breakdown") +
        zone_worksheet(z4, half, grid_h // 2, half, grid_h - grid_h // 2, "[BC] Industry Breakdown")
    )
    parts.append(f"""<zone h='{grid_h}' id='{grid_zid}' type-v2='layout-basic' w='100000' x='0' y='0'>
{grid_inner}
</zone>""")
    sum_zid = zid; zid += 1
    parts.append(zone_text(
        sum_zid, 0, grid_h, 100000, summary_h,
        "Best performing segment will appear here once data is loaded",
        bg="#FFFFFF", fg="#6B7280", size=11, weight="regular", align="left"))

    return "\n".join(parts), zid


def pipeline_body(start_id: int) -> tuple[str, int]:
    """36px banner + 80px funnel + 540px main + footer-band stretches via chrome footer."""
    zid = start_id
    body_h = 738
    banner_h = int(36 / body_h * 100000)
    funnel_h = int(80 / body_h * 100000)
    main_h = 100000 - banner_h - funnel_h

    parts = []

    # Amber data-note banner
    banner_zid = zid; zid += 1
    parts.append(zone_text(
        banner_zid, 0, 0, 100000, banner_h,
        "Attribution is at program level — MQLs and SAOs are credited to the Marketo program, not to individual email recipients.",
        bg="#FEF3C7", fg="#92400E", size=11, weight="regular", align="left"))

    # Funnel row
    funnel_zid = zid; zid += 1
    funnel_sheets = [
        ("[SC] Pipeline - Sends", "#C4B5FD"),
        ("[SC] Pipeline - Opens", "#A78BFA"),
        ("[SC] Pipeline - Clicks", "#7C3AED"),
        ("[SC] Pipeline - MQLs", "#EC4899"),
        ("[SC] Pipeline - SAOs", "#BE185D"),
    ]
    cell_w = int(100000 / len(funnel_sheets))
    funnel_inner = []
    for i, (name, _bg) in enumerate(funnel_sheets):
        cz = zid; zid += 1
        funnel_inner.append(zone_worksheet(cz, i * cell_w, 0, cell_w, 100000, name))
    parts.append(f"""<zone h='{funnel_h}' id='{funnel_zid}' type-v2='layout-flow' w='100000' x='0' y='{banner_h}' param='horz' layout-strategy-id='distribute-evenly'>
{''.join(funnel_inner)}
</zone>""")

    # Main row
    main_zid = zid; zid += 1
    left_w = int(0.65 * 100000)
    right_w = 100000 - left_w
    table_zid = zid; zid += 1
    right_top_zid = zid; zid += 1
    right_bot_zid = zid; zid += 1
    right_split_h = int(0.59 * 100000)
    main_inner = (
        zone_worksheet(table_zid, 0, 0, left_w, 100000, "[BC] Pipeline Table") +
        zone_worksheet(right_top_zid, left_w, 0, right_w, right_split_h, "[BC] Pipeline Trend") +
        zone_text(right_bot_zid, left_w, right_split_h, right_w, 100000 - right_split_h,
                  "What This View Intentionally Omits — No ROI or revenue attribution. No multi-touch attribution. No individual recipient tracing.",
                  bg="#F5F3FF", fg="#4B5563", size=11, weight="regular", align="left")
    )
    parts.append(f"""<zone h='{main_h}' id='{main_zid}' type-v2='layout-basic' w='100000' x='0' y='{banner_h + funnel_h}'>
{main_inner}
</zone>""")

    return "\n".join(parts), zid


# ---------- assembly ----------

def assemble(name: str, slug: str, dashboard_uuid: str, body_fn,
             zone_id_base: int) -> tuple[str, str]:
    import re as _re
    body_xml, after_body = body_fn(zone_id_base + 100)
    chrome_xml, _next = chrome_zones(after_body + 1, name, body_xml, body_height=738)

    # Worksheets used = zones in the chrome+body that carry a name= attribute and
    # no type-v2= (i.e. they are sheet placements, not text/layout zones).
    full_zone_xml = chrome_xml
    used_sheets = []
    seen = set()
    for m in _re.finditer(r"<zone\b[^>]*\bname='([^']+)'[^>]*/>", full_zone_xml):
        # exclude zones that have a type-v2= (those are not sheet zones)
        zone_tag = m.group(0)
        if "type-v2=" in zone_tag:
            continue
        sheet_name = m.group(1)
        if sheet_name not in seen:
            seen.add(sheet_name)
            used_sheets.append(sheet_name)

    root_zid = zone_id_base
    dashboard_xml = f"""<dashboard enable-sort-zone-taborder='true' name='{name}'>
  <style />
  <size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' />
  <zones>
    <zone h='100000' id='{root_zid}' type-v2='layout-basic' w='100000' x='0' y='0'>
{chrome_xml}
    </zone>
  </zones>
  <simple-id uuid='{dashboard_uuid}' />
</dashboard>"""

    win_uuid = make_uuid()
    viewpoints = "\n    ".join(f"<viewpoint name='{s}' />" for s in used_sheets)
    window_xml = f"""<window class='dashboard' name='{name}'>
  <viewpoints>
    {viewpoints}
  </viewpoints>
  <active id='-1' />
  <simple-id uuid='{win_uuid}' />
</window>"""
    return dashboard_xml, window_xml


def write_part(filename: str, name: str, dash_xml: str, win_xml: str) -> str:
    body = f"""<!--
  part-type: dashboard
  name: {name}
  caption: {name}
  datasource: -
  last-modified: 2026-05-01
-->
<!-- SECTION:DASHBOARD -->
{dash_xml}

<!-- SECTION:WINDOW-ENTRY -->
{win_xml}
"""
    (OUT_DIR / filename).write_text(body, encoding="utf-8")
    return f"dashboards/{filename}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body_fns = {
        "Email Overview": overview_body,
        "Email Campaign Performance": campaign_body,
        "Email Audience Breakdown": audience_body,
        "Email Pipeline": pipeline_body,
    }
    paths = []
    for i, (name, slug, gid) in enumerate(DASHBOARDS):
        zone_base = 1000 + i * 200
        dash_xml, win_xml = assemble(name, slug, gid, body_fns[name], zone_base)
        paths.append(write_part(f"{slug}-dashboard.xml", name, dash_xml, win_xml))

    manifest = json.loads(MANIFEST.read_text())
    manifest["dashboards"] = paths
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for p in paths:
        print(f"  {p}")
    print(f"Wrote {len(paths)} dashboard parts")


if __name__ == "__main__":
    main()
