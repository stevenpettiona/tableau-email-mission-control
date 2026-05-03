#!/usr/bin/env python3
"""One-shot generator for the 22 worksheet parts.

Emits one XML part file per worksheet under parts/worksheets/. Each contains:
  - SECTION:WORKSHEET — <worksheet> element
  - SECTION:WINDOW-ENTRY — <window class='worksheet'>

Structural conventions applied (aligned with example worksheets):
  - <layout-options><title> with fontalignment='1' on every worksheet.
  - <datasource-dependencies datasource='Parameters'> on every worksheet.
  - <slices> block on multi-measure and dimensional views.
  - <filter class='categorical' column='...[:Measure Names]'> for multi-measure.
  - Fully-qualified field references: [federated.xxx].[field] everywhere.
  - [:Measure Names] (colon prefix) for the Measure Names virtual field.
  - Scorecards use [X SP] primary + [X Δ] delta via <customized-label>.
  - derivation='User' for COUNTD/ratio calc fields; 'Sum' for raw measures.
  - Rich table style (header, cell, field-labels) on text table worksheets.
  - Mark color #6B3FA0 for bar/line charts.

Run once:
    python3 scripts/generate_worksheets.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "parts" / "worksheets"
MANIFEST = ROOT / "parts" / "manifest.json"

DS1 = "federated.ehemailengagement"
DS1_CAPTION = "EH Email Engagement"
DS2 = "federated.ehemailpipeline"
DS2_CAPTION = "EH Email Pipeline"

TITLE_COLOR = "#6B3FA0"
TITLE_FONT = "Poppins"
HEADER_BG = "#6B3FA0"       # Measure Names column header background
FIELD_LABEL_BG = "#1F1045"  # Row dimension field-label background


def make_uuid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def instance_name(col: str, derivation: str, col_type: str = "qk") -> str:
    bare = col.strip("[]")
    if derivation == "User":
        prefix = "usr"
    elif derivation == "Sum":
        prefix = "sum"
    else:
        prefix = "none"
    key = "nk" if col_type == "nk" else "qk"
    return f"[{prefix}:{bare}:{key}]"


def col_instance_xml(col: str, derivation: str, inst_type: str = "quantitative",
                     col_type: str = "qk") -> str:
    iname = instance_name(col, derivation, col_type)
    return f"        <column-instance column='{col}' derivation='{derivation}' name='{iname}' pivot='key' type='{inst_type}' />"


# ---------------------------------------------------------------------------
# Parameters dependency block (minimal stubs — full definitions live in the
# Parameters datasource part and get compiled into the workbook)
# ---------------------------------------------------------------------------

PARAMS_DEP_XML = """\
      <datasource-dependencies datasource='Parameters'>
        <column caption='Platform' datatype='string' name='[Platform Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Program Type' datatype='string' name='[Program Type Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Direction' datatype='string' name='[Direction Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Country' datatype='string' name='[Country Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Company Size' datatype='string' name='[Company Size Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Product' datatype='string' name='[Product Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Date Range (Days)' datatype='integer' name='[Date Range Days]' param-domain-type='list' role='measure' type='ordinal' value='90' />
        <column caption='Chart View' datatype='string' name='[Chart View Toggle]' param-domain-type='list' role='measure' type='nominal' value='&quot;Sends + Rates&quot;' />
        <column caption='Program Type Quick Filter' datatype='string' name='[Program Type Quick Filter]' param-domain-type='list' role='measure' type='nominal' value='&quot;All&quot;' />
        <column caption='Start Date' datatype='date' name='[Start Date]' param-domain-type='range' role='measure' type='quantitative' value='#2026-02-01#' />
        <column caption='End Date' datatype='date' name='[End Date]' param-domain-type='range' role='measure' type='quantitative' value='#2026-05-01#' />
        <column caption='Compare Period' datatype='string' name='[Compare Period]' param-domain-type='list' role='measure' type='nominal' value='&quot;PoP&quot;' />
        <column caption='Comparison Start' datatype='date' name='[Comparison Start]' param-domain-type='range' role='measure' type='quantitative' value='#2025-02-01#' />
        <column caption='Comparison End' datatype='date' name='[Comparison End]' param-domain-type='range' role='measure' type='quantitative' value='#2025-05-01#' />
      </datasource-dependencies>"""


# ---------------------------------------------------------------------------
# Shared XML fragments
# ---------------------------------------------------------------------------

PANE_MARK_STYLE = """\
        <style>
          <style-rule element='mark'>
            <format attr='mark-labels-show' value='true' />
            <format attr='mark-labels-cull' value='true' />
          </style-rule>
        </style>"""

WINDOW_CARDS = """\
  <cards>
    <edge name='left'>
      <strip size='160'>
        <card type='pages' />
        <card type='filters' />
        <card type='marks' />
      </strip>
    </edge>
    <edge name='top'>
      <strip size='2147483647'><card type='columns' /></strip>
      <strip size='2147483647'><card type='rows' /></strip>
      <strip size='31'><card type='title' /></strip>
    </edge>
  </cards>"""

SCORECARD_TABLE_STYLE = """\
    <style>
      <style-rule element='cell'>
        <format attr='text-align' value='center' />
        <format attr='vertical-align' value='center' />
      </style-rule>
      <style-rule element='label'>
        <format attr='text-align' value='center' />
        <format attr='vertical-align' value='center' />
      </style-rule>
    </style>"""


def layout_options_xml(title_text: str) -> str:
    escaped = (title_text.upper()
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))
    return f"""\
  <layout-options>
    <title>
      <formatted-text>
        <run bold='true' fontalignment='1' fontcolor='{TITLE_COLOR}' fontname='{TITLE_FONT}' fontsize='8'>{escaped}</run>
      </formatted-text>
    </title>
  </layout-options>"""


def layout_options_blank() -> str:
    return """\
  <layout-options>
    <title>
      <formatted-text />
    </title>
  </layout-options>"""


def window_xml(name: str) -> str:
    win_uuid = make_uuid()
    return f"""<window class='worksheet' name='{name}'>
{WINDOW_CARDS}
  <simple-id uuid='{win_uuid}' />
</window>"""


# ---------------------------------------------------------------------------
# Scorecard (single-value tile with SP primary + Δ secondary)
# ---------------------------------------------------------------------------

# (worksheet_name, sp_col, delta_col, datatype, caption, sp_derivation)
DS1_SC = [
    ("[SC] Sends",        "[Sends SP]",        "[Sends Δ]",        "integer", "Sends",        "User"),
    ("[SC] Opens",        "[Opens SP]",        "[Opens Δ]",        "integer", "Opens",        "User"),
    ("[SC] Clicks",       "[Clicks SP]",       "[Clicks Δ]",       "integer", "Clicks",       "User"),
    ("[SC] Unsubscribes", "[Unsubscribes SP]", "[Unsubscribes Δ]", "integer", "Unsubscribes", "User"),
    ("[SC] Open Rate",    "[Open Rate SP]",    "[Open Rate Δ]",    "real",    "Open Rate",    "User"),
    ("[SC] CTR",          "[CTR SP]",          "[CTR Δ]",          "real",    "CTR",          "User"),
    ("[SC] CTOR",         "[CTOR SP]",         "[CTOR Δ]",         "real",    "CTOR",         "User"),
    ("[SC] Unsub Rate",   "[Unsub Rate SP]",   "[Unsub Rate Δ]",   "real",    "Unsub Rate",   "User"),
]

# Pipeline engagement scorecards on DS1 (avoid DS2 cross-table query errors)
DS1_PIPELINE_SC = [
    ("[SC] Pipeline - Sends",  "[Sends SP]",  "[Sends Δ]",  "integer", "Sends",  "User"),
    ("[SC] Pipeline - Opens",  "[Opens SP]",  "[Opens Δ]",  "integer", "Opens",  "User"),
    ("[SC] Pipeline - Clicks", "[Clicks SP]", "[Clicks Δ]", "integer", "Clicks", "User"),
]

# DS2 pipeline scorecards — no SP/LP equivalents for these, keep Sum
DS2_SC = [
    ("[SC] Pipeline - MQLs", "[mqls]", None, "integer", "MQLs", "Sum"),
    ("[SC] Pipeline - SAOs", "[saos]", None, "integer", "SAOs", "Sum"),
]


def scorecard_xml(name: str, ds_name: str, ds_caption: str,
                  sp_col: str, delta_col: str | None,
                  dtype: str, caption: str,
                  sp_derivation: str = "User") -> tuple[str, str]:
    ws_uuid = make_uuid()
    sp_iname = instance_name(sp_col, sp_derivation)

    # Build datasource-dependencies columns
    dep_cols = f"        <column caption='{caption} SP' datatype='{dtype}' name='{sp_col}' role='measure' type='quantitative' />\n"
    dep_cols += f"        {col_instance_xml(sp_col, sp_derivation).strip()}\n"

    if delta_col:
        delta_iname = instance_name(delta_col, "User")
        dep_cols += f"        <column caption='{caption} Δ' datatype='real' default-format='p0.00%' name='{delta_col}' role='measure' type='quantitative' />\n"
        dep_cols += f"        {col_instance_xml(delta_col, 'User').strip()}\n"

        delta_encoding = f"\n              <text column='[{ds_name}].{delta_iname}' />"
        customized_label = f"""
            <customized-label>
              <formatted-text>
                <run bold='true' fontname='{TITLE_FONT}' fontsize='14'><![CDATA[<[{ds_name}].{sp_iname}>]]></run>
                <run>Æ&#10;</run>
                <run fontcolor='#888888' fontname='{TITLE_FONT}' fontsize='8'><![CDATA[<[{ds_name}].{delta_iname}> vs prior period]]></run>
              </formatted-text>
            </customized-label>"""
    else:
        delta_encoding = ""
        customized_label = ""

    ws = f"""<worksheet name='{name}'>
{layout_options_xml(caption)}
  <table>
    <view>
      <datasources>
        <datasource caption='{ds_caption}' name='{ds_name}' />
        <datasource caption='Parameters' name='Parameters' />
      </datasources>
{PARAMS_DEP_XML}
      <datasource-dependencies datasource='{ds_name}'>
{dep_cols.rstrip()}
      </datasource-dependencies>
      <aggregation value='true' />
    </view>
{SCORECARD_TABLE_STYLE}
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view>
          <breakdown value='auto' />
        </view>
        <mark class='Automatic' />
        <encodings>
          <text column='[{ds_name}].{sp_iname}' />{delta_encoding}
        </encodings>{customized_label}
{PANE_MARK_STYLE}
      </pane>
    </panes>
    <rows />
    <cols />
  </table>
  <simple-id uuid='{ws_uuid}' />
</worksheet>"""

    return ws, window_xml(name)


# ---------------------------------------------------------------------------
# Column helpers for dep blocks
# ---------------------------------------------------------------------------

def dim_col(caption: str, name: str, dtype: str = "string",
            col_type: str = "nominal") -> str:
    return f"        <column caption='{caption}' datatype='{dtype}' name='{name}' role='dimension' type='{col_type}' />"


def dim_col_with_instance(caption: str, name: str, dtype: str = "string",
                          col_type: str = "nominal",
                          inst_type: str = "nominal") -> tuple[str, str]:
    """Returns (column_xml, column_instance_xml) for a dimension needing a none: instance."""
    col = f"        <column caption='{caption}' datatype='{dtype}' name='{name}' role='dimension' type='{col_type}' />"
    iname = instance_name(name, "None", "nk")
    inst = f"        <column-instance column='{name}' derivation='None' name='{iname}' pivot='key' type='{inst_type}' />"
    return col, inst


def meas_col(caption: str, name: str, dtype: str = "integer",
             derivation: str = "User") -> str:
    iname = instance_name(name, derivation)
    return (
        f"        <column caption='{caption}' datatype='{dtype}' name='{name}' role='measure' type='quantitative' />\n"
        f"        {col_instance_xml(name, derivation).strip()}"
    )


# ---------------------------------------------------------------------------
# Measure Names filter for multi-measure views
# ---------------------------------------------------------------------------

def measure_names_filter_xml(ds_name: str, inames: list[str]) -> str:
    members = "\n".join(
        f"              <groupfilter function='member' level='[:Measure Names]' member='&quot;[{ds_name}].{iname}&quot;' />"
        for iname in inames
    )
    return f"""\
      <filter class='categorical' column='[{ds_name}].[:Measure Names]'>
        <groupfilter function='union' user:ui-domain='relevant' user:ui-enumeration='inclusive' user:ui-marker='enumerate'>
{members}
        </groupfilter>
      </filter>"""


def slices_xml(columns: list[str]) -> str:
    items = "\n".join(f"            <column>{c}</column>" for c in columns)
    return f"""\
          <slices>
{items}
          </slices>"""


# ---------------------------------------------------------------------------
# Table style for text tables
# ---------------------------------------------------------------------------

def table_style_xml(ds_name: str) -> str:
    return f"""\
    <style>
      <style-rule element='cell'>
        <format attr='font-size' value='9' />
        <format attr='text-align' value='right' />
      </style-rule>
      <style-rule element='header'>
        <format attr='font-size' value='9' />
        <format attr='text-align' value='left' />
        <format attr='background-color' field='[{ds_name}].[:Measure Names]' value='{HEADER_BG}' />
        <format attr='color' data-class='subtotal' field='[{ds_name}].[:Measure Names]' value='#ffffff' />
      </style-rule>
      <style-rule element='field-labels'>
        <format attr='background-color' value='{FIELD_LABEL_BG}' />
      </style-rule>
      <style-rule element='field-labels-decoration'>
        <format attr='color' value='#ffffff' />
      </style-rule>
      <style-rule element='field-labels-spanner'>
        <format attr='color' scope='cols' value='#ffffff' />
        <format attr='font-weight' scope='cols' value='bold' />
      </style-rule>
      <style-rule element='label'>
        <format attr='font-size' value='9' />
        <format attr='text-align' value='center' />
        <format attr='color' field='[{ds_name}].[:Measure Names]' value='#ffffff' />
      </style-rule>
    </style>"""


# ---------------------------------------------------------------------------
# Generic chart/table builder
# ---------------------------------------------------------------------------

def chart_xml(name: str, ds_name: str, ds_caption: str,
              mark_class: str,
              rows_xml: str, cols_xml: str,
              dep_columns_xml: str = "",
              encodings_xml: str = "",
              filter_xml: str = "",
              slices_xml_str: str = "",
              table_style: str = "",
              title_text: str = "") -> tuple[str, str]:
    ws_uuid = make_uuid()

    layout = layout_options_xml(title_text) if title_text else layout_options_blank()

    slices_block = f"\n{slices_xml_str}" if slices_xml_str else ""
    filter_block = f"\n{filter_xml}" if filter_xml else ""

    style_block = table_style if table_style else "    <style />"

    ws = f"""<worksheet name='{name}'>
{layout}
  <table>
    <view>
      <datasources>
        <datasource caption='{ds_caption}' name='{ds_name}' />
        <datasource caption='Parameters' name='Parameters' />
      </datasources>
{PARAMS_DEP_XML}
      <datasource-dependencies datasource='{ds_name}'>
{dep_columns_xml}
      </datasource-dependencies>{filter_block}{slices_block}
      <aggregation value='true' />
    </view>
{style_block}
    <panes>
      <pane selection-relaxation-option='selection-relaxation-allow'>
        <view>
          <breakdown value='auto' />
        </view>
        <mark class='{mark_class}' />
        <encodings>
{encodings_xml}
        </encodings>
{PANE_MARK_STYLE}
      </pane>
    </panes>
    <rows>{rows_xml}</rows>
    <cols>{cols_xml}</cols>
  </table>
  <simple-id uuid='{ws_uuid}' />
</worksheet>"""

    return ws, window_xml(name)


# ---------------------------------------------------------------------------
# Individual chart definitions
# ---------------------------------------------------------------------------

def bc_email_trend() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Event Week", "[event_week]", "date", "ordinal"),
        # none: instance for ordinal date dimension (event_week is already week-level)
        f"        <column-instance column='[event_week]' derivation='None' name='[none:event_week:ok]' pivot='key' type='ordinal' />",
        meas_col("Sends", "[Sends]", "integer", "User"),
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
        meas_col("CTR", "[CTR]", "real", "User"),
    ])
    iname_sends = instance_name("[Sends]", "User")
    iname_or = instance_name("[Open Rate]", "User")
    encodings = f"          <color column='[{DS1}].{iname_or}' />"
    axis_style = f"""\
    <style>
      <style-rule element='axis'>
        <format attr='title' class='0' field='[{DS1}].[Multiple Values]' scope='cols' value='' />
      </style-rule>
    </style>"""
    slices = slices_xml([f"[{DS1}].[none:event_week:ok]"])
    return chart_xml(
        "[BC] Email Trend", DS1, DS1_CAPTION, "Bar",
        rows_xml=f"[{DS1}].{iname_sends}",
        cols_xml=f"[{DS1}].[none:event_week:ok]",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        slices_xml_str=slices,
        table_style=axis_style,
        title_text="Email Trend",
    )


def bc_platform_split() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Platform", "[platform]"),
        f"        <column-instance column='[platform]' derivation='None' name='[none:platform:nk]' pivot='key' type='nominal' />",
        meas_col("Sends", "[Sends]", "integer", "User"),
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
    ])
    iname_sends = instance_name("[Sends]", "User")
    encodings = f"          <color column='[{DS1}].[none:platform:nk]' />"
    slices = slices_xml([f"[{DS1}].[none:platform:nk]"])
    return chart_xml(
        "[BC] Platform Split", DS1, DS1_CAPTION, "Bar",
        rows_xml=f"[{DS1}].{iname_sends}",
        cols_xml=f"[{DS1}].[none:platform:nk]",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        slices_xml_str=slices,
        title_text="Platform Split",
    )


def bc_campaign_table() -> tuple[str, str]:
    measures = [
        ("[Sends]",        "integer", "Sends",        "User"),
        ("[Opens]",        "integer", "Opens",        "User"),
        ("[Clicks]",       "integer", "Clicks",       "User"),
        ("[Unsubscribes]", "integer", "Unsubscribes", "User"),
        ("[Open Rate]",    "real",    "Open Rate",    "User"),
        ("[CTR]",          "real",    "CTR",          "User"),
        ("[CTOR]",         "real",    "CTOR",         "User"),
        ("[Unsub Rate]",   "real",    "Unsub Rate",   "User"),
    ]
    measure_inames = [instance_name(col, deriv) for col, _, _, deriv in measures]

    dep_parts = [
        dim_col("Program Name", "[campaign_name]"),
        dim_col("Sub-Campaign Display", "[Sub Campaign Display]"),
        dim_col("Program Type Badge", "[Program Type Badge]"),
        dim_col("Platform", "[platform]"),
        dim_col("Program Launch Month", "[campaign_year_month]", "date", "ordinal"),
        f"        <column-instance column='[campaign_year_month]' derivation='None' name='[none:campaign_year_month:ok]' pivot='key' type='ordinal' />",
    ]
    for col, dtype, caption, deriv in measures:
        dep_parts.append(meas_col(caption, col, dtype, deriv))
    dep = "\n".join(dep_parts)

    mn_filter = measure_names_filter_xml(DS1, measure_inames)
    slices = slices_xml([f"[{DS1}].[:Measure Names]"])
    tbl_style = table_style_xml(DS1)

    rows = (
        f"[{DS1}].[campaign_name] / [{DS1}].[Sub Campaign Display] / "
        f"[{DS1}].[Program Type Badge] / [{DS1}].[platform] / "
        f"[{DS1}].[none:campaign_year_month:ok]"
    )
    encodings = f"          <text column='[{DS1}].[Multiple Values]' />"

    return chart_xml(
        "[BC] Campaign Table", DS1, DS1_CAPTION, "Text",
        rows_xml=rows,
        cols_xml=f"[{DS1}].[:Measure Names]",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        filter_xml=mn_filter,
        slices_xml_str=slices,
        table_style=tbl_style,
        title_text="Campaign Table",
    )


def bc_country_breakdown() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Country", "[country]"),
        f"        <column-instance column='[country]' derivation='None' name='[none:country:nk]' pivot='key' type='nominal' />",
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
        meas_col("Sends", "[Sends]", "integer", "User"),
    ])
    iname_or = instance_name("[Open Rate]", "User")
    slices = slices_xml([f"[{DS1}].[none:country:nk]"])
    return chart_xml(
        "[BC] Country Breakdown", DS1, DS1_CAPTION, "Bar",
        rows_xml=f"[{DS1}].[none:country:nk]",
        cols_xml=f"[{DS1}].{iname_or}",
        dep_columns_xml=dep,
        slices_xml_str=slices,
        title_text="Country Breakdown",
    )


def bc_company_size_breakdown() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Company Size", "[company_size]"),
        f"        <column-instance column='[company_size]' derivation='None' name='[none:company_size:nk]' pivot='key' type='nominal' />",
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
        meas_col("CTR", "[CTR]", "real", "User"),
        meas_col("Unsub Rate", "[Unsub Rate]", "real", "User"),
    ])
    iname_or = instance_name("[Open Rate]", "User")
    encodings = f"          <color column='[{DS1}].[none:company_size:nk]' />"
    slices = slices_xml([f"[{DS1}].[none:company_size:nk]"])
    return chart_xml(
        "[BC] Company Size Breakdown", DS1, DS1_CAPTION, "Bar",
        rows_xml=f"[{DS1}].{iname_or}",
        cols_xml=f"[{DS1}].[none:company_size:nk]",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        slices_xml_str=slices,
        title_text="Company Size Breakdown",
    )


def bc_lifecycle_stage_breakdown() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Lifecycle Stage", "[lifecycle_stage]"),
        f"        <column-instance column='[lifecycle_stage]' derivation='None' name='[none:lifecycle_stage:nk]' pivot='key' type='nominal' />",
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
        meas_col("CTR", "[CTR]", "real", "User"),
        meas_col("Sends", "[Sends]", "integer", "User"),
    ])
    iname_or = instance_name("[Open Rate]", "User")
    slices = slices_xml([f"[{DS1}].[none:lifecycle_stage:nk]"])
    return chart_xml(
        "[BC] Lifecycle Stage Breakdown", DS1, DS1_CAPTION, "Circle",
        rows_xml=f"[{DS1}].[none:lifecycle_stage:nk]",
        cols_xml=f"[{DS1}].{iname_or}",
        dep_columns_xml=dep,
        slices_xml_str=slices,
        title_text="Lifecycle Stage Breakdown",
    )


def bc_industry_breakdown() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Industry", "[industry]"),
        f"        <column-instance column='[industry]' derivation='None' name='[none:industry:nk]' pivot='key' type='nominal' />",
        meas_col("Sends", "[Sends]", "integer", "User"),
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
    ])
    iname_sends = instance_name("[Sends]", "User")
    iname_or = instance_name("[Open Rate]", "User")
    encodings = f"          <color column='[{DS1}].{iname_or}' />"
    slices = slices_xml([f"[{DS1}].[none:industry:nk]"])
    return chart_xml(
        "[BC] Industry Breakdown", DS1, DS1_CAPTION, "Bar",
        rows_xml=f"[{DS1}].[none:industry:nk]",
        cols_xml=f"[{DS1}].{iname_sends}",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        slices_xml_str=slices,
        title_text="Industry Breakdown",
    )


def sk_campaign_trend_sparkline() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("Event Week", "[event_week]", "date", "ordinal"),
        f"        <column-instance column='[event_week]' derivation='None' name='[none:event_week:ok]' pivot='key' type='ordinal' />",
        dim_col("Program Name", "[campaign_name]"),
        meas_col("Open Rate", "[Open Rate]", "real", "User"),
    ])
    iname_or = instance_name("[Open Rate]", "User")
    slices = slices_xml([
        f"[{DS1}].[none:campaign_name:nk]",
        f"[{DS1}].[none:event_week:ok]",
    ])
    return chart_xml(
        "[SK] Campaign Trend Sparkline", DS1, DS1_CAPTION, "Line",
        rows_xml=f"[{DS1}].{iname_or}",
        cols_xml=f"[{DS1}].[none:event_week:ok]",
        dep_columns_xml=dep,
        slices_xml_str=slices,
    )


def bc_pipeline_trend() -> tuple[str, str]:
    dep = "\n".join([
        dim_col("MQL Date", "[mql_date]", "date", "ordinal"),
        f"        <column-instance column='[mql_date]' derivation='None' name='[none:mql_date:ok]' pivot='key' type='ordinal' />",
        meas_col("MQLs", "[mqls]", "integer", "Sum"),
        meas_col("SAOs", "[saos]", "integer", "Sum"),
    ])
    iname_mqls = instance_name("[mqls]", "Sum")
    slices = slices_xml([f"[{DS2}].[none:mql_date:ok]"])
    return chart_xml(
        "[BC] Pipeline Trend", DS2, DS2_CAPTION, "Bar",
        rows_xml=f"[{DS2}].{iname_mqls}",
        cols_xml=f"[{DS2}].[none:mql_date:ok]",
        dep_columns_xml=dep,
        slices_xml_str=slices,
        title_text="Pipeline Trend",
    )


def bc_pipeline_table() -> tuple[str, str]:
    measures = [
        ("[mqls]",       "integer", "MQLs",             "Sum"),
        ("[leads]",      "integer", "Leads",             "Sum"),
        ("[saos]",       "integer", "SAOs",              "Sum"),
        ("[sao_arr_aud]","real",    "SAO ARR (AUD)",     "Sum"),
        ("[SAO Rate]",   "real",    "SAO Rate (MQL→SAO)", "User"),
    ]
    measure_inames = [instance_name(col, deriv) for col, _, _, deriv in measures]

    dep_parts = [
        dim_col("Program Name", "[campaign_name]"),
        dim_col("MQL Country", "[mql_country]"),
        dim_col("SAO Country", "[sao_country]"),
    ]
    for col, dtype, caption, deriv in measures:
        dep_parts.append(meas_col(caption, col, dtype, deriv))
    dep = "\n".join(dep_parts)

    mn_filter = measure_names_filter_xml(DS2, measure_inames)
    slices = slices_xml([f"[{DS2}].[:Measure Names]"])
    tbl_style = table_style_xml(DS2)
    encodings = f"          <text column='[{DS2}].[Multiple Values]' />"

    return chart_xml(
        "[BC] Pipeline Table", DS2, DS2_CAPTION, "Text",
        rows_xml=f"[{DS2}].[campaign_name]",
        cols_xml=f"[{DS2}].[:Measure Names]",
        dep_columns_xml=dep,
        encodings_xml=encodings,
        filter_xml=mn_filter,
        slices_xml_str=slices,
        table_style=tbl_style,
        title_text="Pipeline Table",
    )


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_part(filename: str, name: str, ds_label: str,
               ws_xml: str, win_xml: str) -> str:
    rel_path = f"worksheets/{filename}"
    body = f"""<!--
  part-type: worksheet
  name: {name}
  caption: {name}
  datasource: {ds_label}
  last-modified: 2026-05-04
-->
<!-- SECTION:WORKSHEET -->
{ws_xml}

<!-- SECTION:WINDOW-ENTRY -->
{win_xml}
"""
    (OUT_DIR / filename).write_text(body, encoding="utf-8")
    return rel_path


def slug(name: str) -> str:
    return (name
            .replace("[SC] ", "sc-")
            .replace("[BC] ", "bc-")
            .replace("[SK] ", "sk-")
            .replace(" - ", "-")
            .replace(" ", "-")
            .lower())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    # DS1 scorecards (SP + delta)
    for name, sp_col, delta_col, dtype, caption, derivation in DS1_SC:
        ws, win = scorecard_xml(name, DS1, DS1_CAPTION, sp_col, delta_col,
                                dtype, caption, derivation)
        paths.append(write_part(f"{slug(name)}.xml", name, "ds1", ws, win))

    # Pipeline engagement scorecards on DS1 (SP + delta)
    for name, sp_col, delta_col, dtype, caption, derivation in DS1_PIPELINE_SC:
        ws, win = scorecard_xml(name, DS1, DS1_CAPTION, sp_col, delta_col,
                                dtype, caption, derivation)
        paths.append(write_part(f"{slug(name)}.xml", name, "ds1", ws, win))

    # DS2 scorecards (MQLs/SAOs — no SP/LP, keep Sum)
    for name, sp_col, delta_col, dtype, caption, derivation in DS2_SC:
        ws, win = scorecard_xml(name, DS2, DS2_CAPTION, sp_col, delta_col,
                                dtype, caption, derivation)
        paths.append(write_part(f"{slug(name)}.xml", name, "ds2", ws, win))

    # DS1 charts
    charts_ds1 = [
        ("bc-email-trend.xml",               "ds1", "[BC] Email Trend",               bc_email_trend()),
        ("bc-platform-split.xml",            "ds1", "[BC] Platform Split",            bc_platform_split()),
        ("bc-campaign-table.xml",            "ds1", "[BC] Campaign Table",            bc_campaign_table()),
        ("bc-country-breakdown.xml",         "ds1", "[BC] Country Breakdown",         bc_country_breakdown()),
        ("bc-company-size-breakdown.xml",    "ds1", "[BC] Company Size Breakdown",    bc_company_size_breakdown()),
        ("bc-lifecycle-stage-breakdown.xml", "ds1", "[BC] Lifecycle Stage Breakdown", bc_lifecycle_stage_breakdown()),
        ("bc-industry-breakdown.xml",        "ds1", "[BC] Industry Breakdown",        bc_industry_breakdown()),
        ("sk-campaign-trend-sparkline.xml",  "ds1", "[SK] Campaign Trend Sparkline",  sk_campaign_trend_sparkline()),
    ]
    for fname, ds_label, ws_name, (ws, win) in charts_ds1:
        paths.append(write_part(fname, ws_name, ds_label, ws, win))

    # DS2 charts
    charts_ds2 = [
        ("bc-pipeline-trend.xml", "ds2", "[BC] Pipeline Trend", bc_pipeline_trend()),
        ("bc-pipeline-table.xml", "ds2", "[BC] Pipeline Table", bc_pipeline_table()),
    ]
    for fname, ds_label, ws_name, (ws, win) in charts_ds2:
        paths.append(write_part(fname, ws_name, ds_label, ws, win))

    # Update manifest
    manifest = json.loads(MANIFEST.read_text())
    manifest["worksheets"] = paths
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(paths)} worksheet parts")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
