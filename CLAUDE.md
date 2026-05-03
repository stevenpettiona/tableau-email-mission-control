# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Tableau workbook** project for Employment Hero's **email marketing** analytics — the **"Email Performance Dashboard"**, a 4-dashboard suite tracking email engagement to commercial outcome.

The workbook is built using an **atomic parts-based architecture**. Do not edit the shell file directly. Edit the atomic parts files and run the compiler.

**Authoritative spec**: the build prompt pasted into the conversation is the source of truth. Where it conflicts with anything else (screenshots, prior CLAUDE.md, the example marketing workbook), the spec wins.

### Known spec correction

The spec defines `[Open Rate]` as `[Sends] / NULLIF([Opens], 0)` — this is a typo. The corrected formula (also given in the spec note immediately below) is:

```
COUNTD(IF [Event Type]='Open' THEN [event_id] END)
/ NULLIF(COUNTD(IF [Event Type]='Send' THEN [event_id] END), 0)
```

Always use the corrected form, against raw `event_id`, to avoid aggregation-of-aggregation errors.

## Build System

### How to build

```bash
python3 scripts/compile.py
```

This assembles `shell/email-mission-control.shell.twb` + all files listed in `parts/manifest.json` into a versioned build under `builds/` and updates the live `email-mission-control.twb`.

```bash
python3 scripts/compile.py --dry-run     # validate without writing
python3 scripts/compile.py --version 5   # pin a specific version number
```

### File structure

```
shell/
  email-mission-control.shell.twb       ← skeleton TWB with INJECT markers
  email-mission-control.twb             ← legacy reference (DO NOT EDIT — kept for column-map reference only)

parts/
  manifest.json                         ← ordered list of all parts (source of truth for compilation)
  calculated-fields/                    ← one .xml file per calculated field
  worksheets/                           ← one .xml file per worksheet
  dashboards/                           ← one .xml file per dashboard (SECTION:DASHBOARD + SECTION:WINDOW-ENTRY)
  navigation/                           ← navigation zone files (embedded via dashboard parts)
  actions/                              ← workbook action elements

scripts/
  compile.py                            ← assembles shell + parts → builds/email-mission-control_{date}-vN.twb

builds/                                 ← versioned compiled output (gitignored)
screenshots/                            ← reference PNG per dashboard (the spec is authoritative when it conflicts with screenshots)
email-mission-control.twb               ← live copy at project root, always current build output
```

### Parts file naming convention

Lowercase hyphenated. Examples: `sc-sends.xml`, `bc-email-trend.xml`, `cf-open-rate.xml`, `email-overview-dashboard.xml`.

### Part file format

Every parts file has a standard header comment:

```xml
<!--
  part-type: calculated-field | worksheet | dashboard | navigation | actions
  name: [original Tableau name]
  caption: Human readable name
  datasource: ds1 | ds2 | parameters
  last-modified: YYYY-MM-DD
-->
```

Dashboard parts files contain two named sections:

```xml
<!-- SECTION:DASHBOARD -->
<dashboard name='...'>...</dashboard>

<!-- SECTION:WINDOW-ENTRY -->
<window class='dashboard' name='...'>...</window>
```

### Shell injection markers

The shell TWB has five named markers where parts are injected:

- `<!-- INJECT:datasources -->` — replaces the entire `<datasources>` block (DS1 + DS2 + Parameters all together)
- `<!-- INJECT:worksheets -->` — inside `<worksheets>`
- `<!-- INJECT:dashboards -->` — inside `<dashboards>`
- `<!-- INJECT:windows-entries -->` — inside `<windows>` (after worksheet window entries)
- `<!-- INJECT:actions -->` — inside `<actions>`

Calculated fields are injected into their parent datasource block via the datasources injection — they are not a separate top-level marker, because DS1, DS2, and Parameters each own their own calc fields.

## Data Architecture

**Database**: AWS Redshift
**Host**: `ehdw-01.c4377kymkso8.ap-southeast-2.redshift.amazonaws.com:5439`
**Database/Schema**: `dev` / `mart`
**Auth**: username/password, SSL required, username `tableau_user`

### Two datasources (different schemas)

| ID | Caption | Used by | Relation type |
|---|---|---|---|
| **DS1** | "EH Email Engagement" | Overview, Campaign Performance, Audience Breakdown | Custom SQL (single relation) |
| **DS2** | "EH Email Pipeline" | Email Pipeline only | Tableau Relationships (logical layer, 3 tables) |

**DS1** is a single Custom SQL select pre-joining `fct_marketing_email_engagement` with `dim_marketing_campaign` and `dim_marketing_audience` (filtered to the four event types Send/Open/Click/Unsubscribe).

**DS2** uses the Tableau 2020.2+ relationships data model (logical layer, NOT physical joins). Three logical tables:
- **Email Events** (root/anchor) — same Custom SQL as DS1
- **Program MQLs** — from `rpt_marketing_mofu_leads`, related on `dim_marketing_campaign_sk` (M:M)
- **Program SAOs** — from `rpt_marketing_bofu_opportunities`, related on `dim_marketing_campaign_sk` (M:M)

Both Program MQLs and Program SAOs relate to **Email Events** (the root), not to each other.

### Calculated fields in DS1

`[Sends]`, `[Opens]`, `[Clicks]`, `[Unsubscribes]`, `[Open Rate]`, `[CTR]`, `[CTOR]`, `[Unsub Rate]`, `[Unsub Rate Alert]`, `[Traffic Light — Open Rate]`, `[Traffic Light — CTR]`, `[Traffic Light — Unsub]`, `[Program Type Badge]`, `[Sub Campaign Display]`.

### Calculated fields in DS2

`[MQL Rate]`, `[SAO Rate (MQL→SAO)]`.

### Date filter

DS1 worksheets all carry a parameter-driven date filter:

```
DATEADD('day', -[Date Range Days], TODAY()) <= [event_timestamp]
AND [event_timestamp] <= TODAY()
```

DS2 worksheets apply the same date logic ONLY to `[event_timestamp]` (Email Events table) — never to `mql_date` or `sao_date`. Pipeline metrics (MQLs, SAOs) show all-time totals attributed to programs whose email sends fall in the date window.

### Parameters

All global filters are Tableau Parameters living in a `Parameters` datasource:

| Parameter | Caption | Default | Members |
|---|---|---|---|
| `[Platform Filter]` | Platform | All | All, marketo, braze b2b |
| `[Program Type Filter]` | Program Type | All | All, Batch and Blast, Email Nurture, Sales Email, Newsletter, Event-Webinar, Training/Hero Academy, Default |
| `[Direction Filter]` | Direction | All | All, Inbound, Outbound |
| `[Country Filter]` | Country | All | All, AU, NZ, GB, CA |
| `[Company Size Filter]` | Company Size | All | All, micro, core, mid-market |
| `[Product Filter]` | Product | All | All, CHR, HRA, MP, LMS, EAP, GC, "" (Not Specified) |
| `[Date Range Days]` | Date Range (Days) | 90 | 30, 60, 90, 180, 365 (integer) |
| `[Chart View Toggle]` | Chart View | Sends + Rates | Sends + Rates, Sends Only, Rates Only |
| `[Program Type Quick Filter]` | Program Type Quick Filter | All | (same as Program Type Filter) — Campaign Performance dashboard only |

Each filter calc skips when the parameter equals `"All"`. Product additionally treats `""` as "match NULL".

## Worksheet Naming Convention

| Prefix | Type |
|---|---|
| `[SC]` | Scorecard / KPI tile |
| `[BC]` | Bar chart / table |
| `[SK]` | Sparkline (mini-chart embedded in tables) |

Total: ~22 worksheets across DS1 (sheets 1–3) and DS2 (sheet 4).

## Dashboards

Each dashboard has a reference screenshot in `screenshots/`. **The spec is authoritative when it conflicts with the screenshot.** Screenshots are useful for layout intuition but the spec's measurements and component definitions win.

| Dashboard | Internal name | Screenshot | Parts file |
|---|---|---|---|
| Overview | `Email Overview` | `screenshots/overview.png` | `email-overview-dashboard.xml` |
| Campaign Performance | `Email Campaign Performance` | `screenshots/campaign-performance.png` | `email-campaign-performance-dashboard.xml` |
| Audience Breakdown | `Email Audience Breakdown` | `screenshots/audience-breakdown.png` | `email-audience-breakdown-dashboard.xml` |
| Pipeline | `Email Pipeline` | `screenshots/email-pipeline.png` | `email-pipeline-dashboard.xml` |

**Dashboard dimensions**: 1366×900px fixed.

**Body height** (below shared chrome, above footer): `900 - 44 - 38 - 48 - 32 = 738px`.

### Shared chrome (identical on all 4 dashboards)

- **Hero banner** (44px, top, full width) — `#2D1B5E` background, white Poppins 13px semibold title
- **Navigation tab strip** (38px) — `#1F1045` background; 4 navigation buttons (Overview / Campaign Performance / Audience Breakdown / Email → Pipeline); active pill `#6B3FA0` with white text, inactive transparent with white text
- **Global filter bar** (48px) — white background, bottom border `#E5E7EB`, 7 parameter quick-filter dropdowns (Date Range, Platform, Program Type, Direction, Country, Company Size, Product)
- **Footer** (32px) — white background with sources line on the left and target/threshold line on the right; below footer an italic MPP caveat note

### Nav tab order

`Overview → Campaign Performance → Audience Breakdown → Email → Pipeline`.

## Colour Palette

Custom palette named `Email Performance Palette`.

| Role | Hex |
|---|---|
| Background | `#FFFFFF` |
| Text | `#111827` |
| Hero banner | `#2D1B5E` |
| Nav strip | `#1F1045` |
| Accent (primary) | `#6B3FA0` |
| Button text | `#FFFFFF` |
| Secondary metric | `#EC4899` |
| Positive (green) | `#22C55E` |
| Negative (red) | `#EF4444` |
| Amber | `#F59E0B` |
| Light purple | `#A78BFA` |
| Very light purple | `#F5F3FF` |

Pipeline funnel cells use a deepening violet ramp: `#C4B5FD → #A78BFA → #7C3AED → #EC4899 → #BE185D`.

**Font**: Poppins.

## Tableau Version

Built with Tableau 2026.1.0 (Build 20261.26.0226.1626).

## Agent Skills

The spec invokes a `/tableau-orchestrator` skill chain (datasource-builder → worksheet-builder → dashboard-windows-builder → actions-builder). **These specialist skills are not currently installed in this repo.** Until they exist, XML generation is done in-line. If installing them later, they should write to `parts/` and trigger `python3 scripts/compile.py` after every change.

## Build phases

Strict dependency order — each phase produces context inputs for the next:

1. **Task 1 — Datasources** — DS1 + DS2 + Parameters → exports `ds1_name`, `ds2_name`, calc IDs, parameter names
2. **Task 2 — Worksheets** — 22 worksheet XML blocks using Task 1 IDs → exports worksheet names
3. **Task 3 — Dashboards** — 4 dashboard layouts + windows entries → exports dashboard GUIDs and nav-button window-IDs
4. **Task 4 — Actions** — 11 actions (4 nav, 2 filter, 4 highlight, 1 parameter) using Task 2 + 3 outputs

## Cross-agent validation checklist (run before final build)

- Every worksheet name referenced in a dashboard zone exists in `<worksheets>`
- All 4 dashboard GUIDs are unique and appear in both `<dashboards>` and `<windows>`
- DS2 datasource name is distinct from DS1
- All `[Calculation_XXXXXXXXXX]` IDs are unique across all 22 worksheets
- No zone ID collision across the 4 dashboards
- DS2 date filter applies only to `[event_timestamp]` (not `mql_date` or `sao_date`)
- `[Program Type Quick Filter]` is wired only to the Campaign Performance dashboard (does not bleed into the global filter bar)
- The "What This View Intentionally Omits" panel on Pipeline dashboard is a static text object (not a worksheet)
- Footer MPP caveat appears on every dashboard that shows Open Rate (Overview, Campaign Performance, Pipeline)
