#!/usr/bin/env python3
"""Compile shell + parts -> versioned Tableau .twb.

Reads:
  shell/email-mission-control.shell.twb       — skeleton with INJECT markers
  parts/manifest.json                         — ordered list of parts per marker
  parts/<group>/<file>.xml                    — part contents (with header comment + sections)

Writes:
  builds/email-mission-control_<YYYYMMDD>-v<N>.twb
  email-mission-control.twb                   — live copy at project root

Usage:
  python3 scripts/compile.py
  python3 scripts/compile.py --dry-run
  python3 scripts/compile.py --version 5
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELL = ROOT / "shell" / "email-mission-control.shell.twb"
MANIFEST = ROOT / "parts" / "manifest.json"
PARTS_DIR = ROOT / "parts"
BUILDS_DIR = ROOT / "builds"
LIVE_TWB = ROOT / "email-mission-control.twb"

INJECT_RE = re.compile(r"<!--\s*INJECT:([a-z\-]+)\s*-->")

# Markers expected in the shell, in the order parts are slotted in.
MARKERS = [
    "datasources",
    "worksheets",
    "dashboards",
    "windows-entries",
    "actions",
]


def strip_header(part_text: str) -> str:
    """Drop the opening <!-- ... --> header comment from a part file."""
    text = part_text.lstrip()
    if text.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            text = text[end + 3 :].lstrip()
    return text


def parse_header_field(part_text: str, field: str) -> str:
    """Extract a named field value from the header comment, e.g. 'datasource'."""
    m = re.search(rf"^\s*{re.escape(field)}:\s*(.+)$", part_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def split_section(part_text: str, section: str) -> str:
    """Return content between <!-- SECTION:NAME --> markers within a part file."""
    pattern = re.compile(
        rf"<!--\s*SECTION:{section}\s*-->(.*?)(?=<!--\s*SECTION:|$)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(part_text)
    return m.group(1).strip() if m else ""


def load_part(rel_path: str) -> str:
    p = PARTS_DIR / rel_path
    if not p.exists():
        raise FileNotFoundError(f"Part not found: {p}")
    return p.read_text(encoding="utf-8")


def assemble_marker(marker: str, manifest: dict) -> str:
    """Return the concatenated XML for a given marker."""
    if marker == "datasources":
        # Group calculated-field parts by their declared datasource slug (ds1, ds2, …)
        cf_by_ds: dict[str, list[str]] = {}
        for rel in manifest.get("calculated-fields", []):
            text = load_part(rel)
            ds_label = parse_header_field(text, "datasource")
            cf_by_ds.setdefault(ds_label, []).append(strip_header(text).strip())

        chunks = []
        for rel in manifest.get("datasources", []):
            text = load_part(rel)
            ds_label = parse_header_field(text, "datasource")
            ds_xml = strip_header(text)
            cf_xml = "\n  ".join(cf_by_ds.get(ds_label, []))
            ds_xml = ds_xml.replace("<!-- INJECT:calculated-fields -->", cf_xml)
            chunks.append(ds_xml)
        return "\n".join(chunks)

    if marker == "windows-entries":
        # Window entries come from worksheet parts AND dashboard parts (SECTION:WINDOW-ENTRY).
        chunks = []
        for rel in manifest.get("worksheets", []) + manifest.get("dashboards", []):
            text = load_part(rel)
            section = split_section(text, "WINDOW-ENTRY")
            if section:
                chunks.append(section)
        return "\n".join(chunks)

    if marker == "worksheets":
        rels = manifest.get("worksheets", [])
        chunks = []
        for rel in rels:
            text = load_part(rel)
            section = split_section(text, "WORKSHEET")
            chunks.append(section if section else strip_header(text))
        return "\n".join(chunks)

    if marker == "dashboards":
        rels = manifest.get("dashboards", [])
        chunks = []
        for rel in rels:
            text = load_part(rel)
            section = split_section(text, "DASHBOARD")
            chunks.append(section if section else strip_header(text))
        return "\n".join(chunks)

    rels = manifest.get(marker, [])
    chunks = [strip_header(load_part(rel)) for rel in rels]
    return "\n".join(chunks)


def determine_version(pin: int | None) -> int:
    if pin is not None:
        return pin
    today = dt.date.today().strftime("%Y%m%d")
    pattern = re.compile(rf"email-mission-control_{today}-v(\d+)\.twb$")
    if not BUILDS_DIR.exists():
        return 1
    versions = []
    for p in BUILDS_DIR.iterdir():
        m = pattern.search(p.name)
        if m:
            versions.append(int(m.group(1)))
    return (max(versions) + 1) if versions else 1


def compile_workbook(dry_run: bool, pin_version: int | None) -> Path | None:
    if not SHELL.exists():
        print(f"[error] shell file missing: {SHELL}", file=sys.stderr)
        sys.exit(1)
    if not MANIFEST.exists():
        print(f"[error] manifest missing: {MANIFEST}", file=sys.stderr)
        sys.exit(1)

    shell_text = SHELL.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    found_markers = INJECT_RE.findall(shell_text)
    missing = [m for m in MARKERS if m not in found_markers]
    if missing:
        print(f"[error] shell is missing INJECT markers: {missing}", file=sys.stderr)
        sys.exit(2)

    out_text = shell_text
    for marker in MARKERS:
        block = assemble_marker(marker, manifest)
        out_text = out_text.replace(f"<!-- INJECT:{marker} -->", block)

    if dry_run:
        print("[dry-run] compile OK")
        print(f"[dry-run] markers replaced: {MARKERS}")
        print(f"[dry-run] output size: {len(out_text):,} chars")
        return None

    BUILDS_DIR.mkdir(exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    version = determine_version(pin_version)
    out_path = BUILDS_DIR / f"email-mission-control_{today}-v{version}.twb"
    out_path.write_text(out_text, encoding="utf-8")
    shutil.copyfile(out_path, LIVE_TWB)
    print(f"[ok] wrote {out_path}")
    print(f"[ok] live -> {LIVE_TWB}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--version", type=int, default=None)
    args = ap.parse_args()
    compile_workbook(args.dry_run, args.version)


if __name__ == "__main__":
    main()
