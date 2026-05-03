# Email Performance Dashboard

A **Tableau workbook** for Employment Hero's email marketing analytics. Four dashboards tracking email engagement through to commercial outcome, built with an atomic parts-based architecture that keeps the workbook maintainable and version-controlled as plain XML.

---

## Dashboards

| Dashboard | Description |
|---|---|
| **Overview** | KPI scorecards, weekly send trend, platform split |
| **Campaign Performance** | Per-campaign table with open rate, CTR, CTOR, unsub rate |
| **Audience Breakdown** | Segmentation by country, company size, lifecycle stage, industry |
| **Email → Pipeline** | MQL and SAO attribution for email programs |

All dashboards are **1366 × 900 px fixed** and share a common chrome: hero banner, navigation tab strip, global filter bar, and footer.

---

## Architecture

The workbook is built from **atomic parts files** assembled by a Python compiler. The live `email-mission-control.twb` at the project root is always the latest compiled output — **do not edit it directly**.

```
shell/
  email-mission-control.shell.twb   ← skeleton TWB with <!-- INJECT:* --> markers

parts/
  manifest.json                     ← ordered list of all parts (compilation source of truth)
  datasources/                      ← DS1 (email engagement), DS2 (pipeline), Parameters
  calculated-fields/                ← one .xml file per calculated field
  worksheets/                       ← one .xml file per worksheet (~23 sheets)
  dashboards/                       ← one .xml file per dashboard layout + window entry
  navigation/                       ← nav strip zone files (reference; embedded via dashboards)
  actions/                          ← workbook-level action elements

scripts/
  compile.py                        ← assembles shell + parts → builds/ and root TWB
  generate_navigation.py            ← regenerates nav strip zones across all 4 dashboards
  generate_worksheets.py            ← regenerates worksheet XML from templates
  generate_dashboards.py            ← regenerates dashboard layout XML

builds/                             ← versioned output (gitignored)
screenshots/                        ← reference PNG per dashboard
example/                            ← reference MMC workbook and part examples
```

### Injection markers

The shell TWB has five `<!-- INJECT:* -->` markers:

| Marker | Injects |
|---|---|
| `INJECT:datasources` | Full `<datasources>` block (DS1 + DS2 + Parameters + all calc fields) |
| `INJECT:worksheets` | All `<worksheet>` elements |
| `INJECT:dashboards` | All `<dashboard>` elements |
| `INJECT:windows-entries` | All `<window>` entries for worksheets and dashboards |
| `INJECT:actions` | All `<action>` elements |

---

## Build

**Requires**: Python 3.10+, no external dependencies.

```bash
# Compile to builds/ and update the live root TWB
python3 scripts/compile.py

# Validate structure without writing output
python3 scripts/compile.py --dry-run

# Pin a specific version number
python3 scripts/compile.py --version 6

# Regenerate nav strip zones across all 4 dashboards after layout changes
python3 scripts/generate_navigation.py
```

Every compile writes a versioned file to `builds/email-mission-control_YYYYMMDD-vN.twb` and overwrites `email-mission-control.twb` at the project root.

---

## Data

**Database**: AWS Redshift — `ehdw-01.c4377kymkso8.ap-southeast-2.redshift.amazonaws.com:5439`  
**Schema**: `dev.mart`

### Two datasources

| | Caption | Used by | Type |
|---|---|---|---|
| **DS1** | EH Email Engagement | Overview, Campaign Performance, Audience Breakdown | Custom SQL (single relation joining fct + dims) |
| **DS2** | EH Email Pipeline | Email Pipeline only | Tableau Relationships (3 logical tables) |

DS2 relates **Email Events** (anchor) → **Program MQLs** and **Program SAOs** on `dim_marketing_campaign_sk`. The date filter applies only to `[event_timestamp]` — never to `mql_date` or `sao_date`.

### Parameters

Seven global filter parameters live in a `Parameters` datasource: **Date Range (Days)**, **Platform**, **Program Type**, **Direction**, **Country**, **Company Size**, **Product**. Each filter calc is a no-op when the parameter equals `"All"`.

---

## Parts conventions

### File naming
Lowercase hyphenated: `sc-sends.xml`, `bc-email-trend.xml`, `cf-open-rate.xml`.

### Worksheet prefix key

| Prefix | Type |
|---|---|
| `[SC]` | Scorecard / KPI tile |
| `[BC]` | Bar chart / table |
| `[SK]` | Sparkline |

### Part file header
Every parts file carries a standard header comment:
```xml
<!--
  part-type: calculated-field | worksheet | dashboard | navigation | actions
  name: [Tableau internal name]
  caption: Human readable name
  datasource: ds1 | ds2 | parameters
  last-modified: YYYY-MM-DD
-->
```

Dashboard parts contain two named sections:
```xml
<!-- SECTION:DASHBOARD -->
<dashboard name='...'>...</dashboard>

<!-- SECTION:WINDOW-ENTRY -->
<window class='dashboard' name='...'>...</window>
```

---

## Colour palette

| Role | Hex |
|---|---|
| Hero banner | `#2D1B5E` |
| Nav strip / inactive tab | `#1F1045` |
| Active tab / accent | `#6B3FA0` |
| Secondary metric | `#EC4899` |
| Positive | `#22C55E` |
| Negative | `#EF4444` |
| Amber | `#F59E0B` |

Font: **Poppins** throughout.

---

## Tableau version

Built with **Tableau 2026.1.0** (Build 20261.26.0226.1626), workbook version `18.1`.
