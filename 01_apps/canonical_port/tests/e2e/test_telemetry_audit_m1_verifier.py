#!/usr/bin/env python3
"""
Comprehensive Empirical Challenger M1 Verification Test Suite.
"""

import os
import sys
import re
import json
from pathlib import Path

REPORT_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/telemetry_audit_report.md")
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

def run_all_checks():
    assert REPORT_PATH.exists(), f"Report file {REPORT_PATH} not found"
    content = REPORT_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    print("==================================================")
    print("1. LINE COUNT & DOCUMENT STRUCTURE")
    print("==================================================")
    print(f"Total lines: {len(lines)}")
    line_count_pass = len(lines) > 400
    print(f"Line count > 400 check: {'PASS' if line_count_pass else 'FAIL'}")

    # Headings
    headings = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))
    print(f"Total markdown headings: {len(headings)}")

    print("\n==================================================")
    print("2. MARKDOWN TABLE PARSING & COLUMN CONSISTENCY")
    print("==================================================")
    tables = []
    current_table = []
    table_start = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not current_table:
                table_start = i
            current_table.append((i, stripped))
        else:
            if current_table:
                tables.append((table_start, current_table))
                current_table = []

    if current_table:
        tables.append((table_start, current_table))

    print(f"Found {len(tables)} Markdown tables across document.")
    table_issues = []
    total_data_rows = 0

    for idx, (start_line, raw_rows) in enumerate(tables, 1):
        if len(raw_rows) < 2:
            table_issues.append((start_line, f"Table {idx} has fewer than 2 rows."))
            continue
        
        header_line, header_str = raw_rows[0]
        delim_line, delim_str = raw_rows[1]

        header_cols = [c.strip() for c in header_str.split("|")[1:-1]]
        delim_cols = [c.strip() for c in delim_str.split("|")[1:-1]]

        expected_cols = len(header_cols)
        
        # Check delimiter validity
        if len(delim_cols) != expected_cols:
            table_issues.append((delim_line, f"Table {idx} header has {expected_cols} cols but delimiter has {len(delim_cols)} cols."))
        
        for r_line, r_str in raw_rows[2:]:
            total_data_rows += 1
            # Split on | but note unescaped pipes
            cols = [c.strip() for c in r_str.split("|")[1:-1]]
            if len(cols) != expected_cols:
                table_issues.append((r_line, f"Table {idx} (starts line {start_line}): Row at line {r_line} has {len(cols)} cols (expected {expected_cols}). Content: {r_str[:80]}..."))

    print(f"Total Table Data Rows: {total_data_rows}")
    print(f"Table Syntax Issues Found: {len(table_issues)}")
    for line_no, issue in table_issues:
        print(f"  [TABLE BUG line {line_no}]: {issue}")

    print("\n==================================================")
    print("3. FILE REFERENCES & MONOREPO PATH AUDIT")
    print("==================================================")
    # Extract file references
    patterns = [
        r"`([0-9]{2}_[a-zA-Z0-9_\-\./]+)`",
        r"`([a-zA-Z0-9_\-\./]+\.(?:py|sh|json|yaml|yml|md|ts|tsx|jsx|js|toml|txt|conf|service))`",
        r"`(/Users/aaron/[a-zA-Z0-9_\-\./]+)`",
        r"`(/Volumes/[a-zA-Z0-9_\-\./]+)`",
        r"(?:from|in|file)\s+`([^`]+)`",
    ]

    all_raw_paths = set()
    for pat in patterns:
        for m in re.finditer(pat, content):
            raw = m.group(1).strip()
            if raw and not raw.startswith("http") and not raw.startswith("#"):
                # Clean trailing punctuation
                raw = raw.rstrip(".,;:)]}\"'")
                if len(raw) > 2 and ("/" in raw or "." in raw):
                    all_raw_paths.add(raw)

    print(f"Extracted {len(all_raw_paths)} unique path references.")

    existing_paths = []
    missing_paths = []

    for path_str in sorted(all_raw_paths):
        # Strip line numbers like :221
        clean_path = re.sub(r":\d+$", "", path_str)
        
        # Check absolute
        if clean_path.startswith("/"):
            p = Path(clean_path)
        else:
            p = MONOREPO_ROOT / clean_path
            if not p.exists():
                # check canonical_port relative
                p_cp = REPORT_PATH.parent / clean_path
                if p_cp.exists():
                    p = p_cp

        if p.exists():
            existing_paths.append((path_str, str(p), "DIR" if p.is_dir() else "FILE"))
        else:
            missing_paths.append((path_str, str(p)))

    print(f"Verified Existing Paths on Disk: {len(existing_paths)}")
    print(f"Unresolved / Missing Paths: {len(missing_paths)}")
    for raw, target in missing_paths:
        print(f"  [MISSING PATH] {raw} -> {target}")

    print("\n==================================================")
    print("4. BROKEN LINKS & ANCHORS AUDIT")
    print("==================================================")
    # Collect all heading anchors
    anchors = set()
    for _, _, title in headings:
        # standard github markdown anchor slug
        slug = title.lower()
        slug = re.sub(r"[^\w\s\-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        anchors.add(slug)
        # also raw title without spaces
        anchors.add(re.sub(r"\s+", "-", title.lower()))

    # Find links
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    broken_links = []
    valid_links = 0
    for text, target in links:
        if target.startswith("#"):
            slug = target[1:].lower()
            if slug in anchors:
                valid_links += 1
            else:
                # Check fuzzy
                clean_slug = re.sub(r"[^\w\-]", "", slug)
                matched = any(clean_slug in a or a in clean_slug for a in anchors)
                if matched:
                    valid_links += 1
                else:
                    broken_links.append((text, target, "Anchor not found"))
        elif target.startswith("http://") or target.startswith("https://"):
            valid_links += 1
        else:
            # File link
            clean_target = target.split("#")[0]
            f_path = REPORT_PATH.parent / clean_target
            f_root = MONOREPO_ROOT / clean_target
            if f_path.exists() or f_root.exists():
                valid_links += 1
            else:
                broken_links.append((text, target, "File link target not found"))

    print(f"Total Markdown Links Checked: {len(links)} (Valid: {valid_links}, Broken: {len(broken_links)})")
    for bl in broken_links:
        print(f"  [BROKEN LINK]: {bl}")

    print("\n==================================================")
    print("5. RULE #0 & DATA INTEGRITY AUDIT")
    print("==================================================")
    forbidden_terms = ["TODO", "FIXME", "TBD", "PLACEHOLDER", "FAKE_DATA", "SIMULATED_ARRAY"]
    forbidden_hits = []
    for line_num, line in enumerate(lines, 1):
        for term in forbidden_terms:
            if term in line:
                forbidden_hits.append((line_num, term, line.strip()))

    print(f"Forbidden Placeholder Hits: {len(forbidden_hits)}")
    for hit in forbidden_hits:
        print(f"  [PLACEHOLDER line {hit[0]}]: {hit[1]} in '{hit[2]}'")

    return {
        "line_count": len(lines),
        "table_count": len(tables),
        "table_data_rows": total_data_rows,
        "table_issues": table_issues,
        "existing_paths": len(existing_paths),
        "missing_paths": missing_paths,
        "broken_links": broken_links,
        "forbidden_hits": forbidden_hits
    }

def test_telemetry_audit_markdown_tables():
    """Challenger M1 verification test: verify all 16 markdown tables pass column alignment with 0 syntax issues."""
    res = run_all_checks()
    assert res["line_count"] > 400, f"Expected line count > 400, got {res['line_count']}"
    assert res["table_count"] == 16, f"Expected 16 tables, found {res['table_count']}"
    assert len(res["table_issues"]) == 0, f"Found {len(res['table_issues'])} table issues: {res['table_issues']}"
    assert len(res["forbidden_hits"]) == 0, f"Found forbidden terms: {res['forbidden_hits']}"

if __name__ == "__main__":
    res = run_all_checks()

