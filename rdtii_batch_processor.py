#!/usr/bin/env python3
"""
rdtii_batch_processor.py — Standalone batch client for the RDTII AI Mapper.

Reads seed_tasks.csv → calls POST /api/extract for each row → maps response
to the Legal Inventory Target Schema Template → writes final_rdtii_submission_*.csv.

Output columns (per Singapore, Malaysia, Australia, Legal Inventory.csv):
    country, Act.and.or.practice, Coverage, Timeframe, References,
    cluster, Region, Cov.Name, name, policy.description

Usage:
    python rdtii_batch_processor.py [seed_file.csv]
"""

from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests

API_URL = os.getenv("RDTII_API_URL", "http://localhost:8000/api/extract")
REQUEST_TIMEOUT = int(os.getenv("RDTII_TIMEOUT", "120"))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

REGION_MAP: dict[str, str] = {
    "Malaysia": "South-East Asia",
    "Singapore": "South-East Asia",
    "Indonesia": "South-East Asia",
    "Thailand": "South-East Asia",
    "Vietnam": "South-East Asia",
    "Philippines": "South-East Asia",
    "Brunei": "South-East Asia",
    "Cambodia": "South-East Asia",
    "Laos": "South-East Asia",
    "Myanmar": "South-East Asia",
    "Timor-Leste": "South-East Asia",
    "Australia": "Pacific",
    "New Zealand": "Pacific",
    "Fiji": "Pacific",
    "Papua New Guinea": "Pacific",
    "India": "South Asia",
    "Pakistan": "South Asia",
    "Bangladesh": "South Asia",
    "Sri Lanka": "South Asia",
    "Nepal": "South Asia",
    "Bhutan": "South Asia",
    "Maldives": "South Asia",
    "China": "East Asia",
    "Japan": "East Asia",
    "South Korea": "East Asia",
    "Mongolia": "East Asia",
    "Taiwan": "East Asia",
}


def log(msg: str, color: str = ""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {color}{msg}{RESET}", flush=True)


def read_seed_tasks(path: str = "seed_tasks.csv") -> list[dict]:
    log(f"Reading seed tasks from {path} ...", CYAN)
    tasks: list[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            economy = (row.get("Economy") or "").strip()
            indicator_id = (row.get("Indicator_ID") or "").strip()
            url = (row.get("Source_URL_or_Path") or "").strip()
            if not economy and not indicator_id and not url:
                continue
            tasks.append(
                {"economy": economy, "indicator_id": indicator_id, "source_url": url}
            )
    log(f"  → Loaded {len(tasks)} task(s)", GREEN)
    return tasks


def call_extract_api(source_url: str) -> dict | None:
    log(f"  POST {API_URL} (timeout={REQUEST_TIMEOUT}s)")
    try:
        resp = requests.post(
            API_URL,
            data={"source_url": source_url},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        mapping_count = len(data.get("mappings") or [])
        rejected_count = len(data.get("rejected") or [])
        log(f"  ← {mapping_count} mapping(s), {rejected_count} rejected", GREEN)
        return data
    except requests.exceptions.Timeout:
        log(f"  ✗ TIMEOUT after {REQUEST_TIMEOUT}s", RED)
    except requests.exceptions.RequestException as e:
        log(f"  ✗ API error: {e}", RED)
    except Exception as e:
        log(f"  ✗ Unexpected error: {e}", RED)
    return None


def derive_economy_region(economy: str) -> str:
    return REGION_MAP.get(economy, "")


def derive_cov_name(scope: str) -> str:
    s = scope.strip().lower()
    if s == "horizontal":
        return "Cross-cutting"
    elif s == "sectoral":
        return "Sectoral"
    return "Sectoral"


def format_act_and_practice(raw: str) -> str:
    if not raw:
        return "[PENDING HUMAN REVIEW]"

    formatted = raw.strip()

    # Remove trailing semicolons and whitespace
    formatted = formatted.rstrip(";").strip()

    # If there's a "—" or "–" with article/provision details, strip after it
    import re
    formatted = re.sub(r"\s*[—–]\s*(?:Article|Section|Chapter|Clause|Art\.|Sec\.|Ch\.).*", "", formatted, flags=re.IGNORECASE)

    # If the text contains article/provision numbers in parentheses at the end, remove them
    formatted = re.sub(r"\s*\(.*(?:Article|Section|Art\.|Sec\.).*\)\s*$", "", formatted)

    # Multiple consecutive spaces → single space
    formatted = re.sub(r"\s{2,}", " ", formatted)

    # Ensure semicolons only for actual multi-measure entries
    formatted = formatted.strip().rstrip(";").strip()

    return formatted if formatted else "[PENDING HUMAN REVIEW]"


def format_coverage(raw: str, scope: str) -> str:
    if not raw:
        if scope == "horizontal":
            return "Cross-cutting"
        return "Sectoral"

    formatted = raw.strip().rstrip(";").strip()

    # Map common scope values to proper coverage descriptions
    s = scope.strip().lower()
    if s == "horizontal" and (not formatted or formatted.lower() == "horizontal"):
        return "Cross-cutting"
    if s == "sectoral" and (not formatted or formatted.lower() in ("sectoral", "sectoral ")):
        return "Sectoral"

    # Standardize coverage — capitalize first letter, ensure clean output
    if formatted.lower() == "cross-cutting":
        return "Cross-cutting"
    if formatted.lower().startswith("sectoral"):
        return "Sectoral"

    return formatted if formatted else "Sectoral"


def format_timeframe(
    last_update: str,
    timeframe_column: str = "",
) -> str:
    if not last_update and not timeframe_column:
        return ""

    # Prefer the pre-built timeframe column from the backend
    if timeframe_column and timeframe_column.strip():
        tf = timeframe_column.strip()
    elif last_update:
        tf = last_update.strip()
    else:
        return ""

    # Remove leading/trailing semicolons
    tf = tf.strip().rstrip(";").strip()

    # If the value is "Not Available", keep it as-is
    if tf.lower() in ("not available", "n/a", "na"):
        return "Not Available"

    # Ensure semicolons for multiple dates
    import re
    tf = re.sub(r"\s*;\s*", "; ", tf)

    return tf


def format_references(raw: str) -> str:
    if not raw:
        return "[PENDING HUMAN REVIEW]"
    return raw.strip().rstrip(";").strip()


def extract_field(data: dict, mapping: dict, key: str, default: str = "[PENDING HUMAN REVIEW]") -> str:
    """Extract a field from either the LLM data or the constructed mapping dict."""
    val = mapping.get(key, "") or ""
    if val:
        return val.strip()
    val = data.get(key, "") or ""
    if val:
        return str(val).strip()
    return default


def map_mapping_to_row(
    economy: str,
    indicator_id: str,
    mapping: dict,
    llm_data: dict,
) -> dict:
    source_leg = (mapping.get("source_legislation") or llm_data.get("source_legislation") or "")
    scope_val = (mapping.get("scope") or llm_data.get("scope") or "sectoral")
    last_update = (mapping.get("last_update") or llm_data.get("last_update") or "")
    source_url = (mapping.get("source_url") or llm_data.get("source_url") or "")
    features = mapping.get("features") or {}
    timeframe_col = features.get("_timeframe_column", "")

    act_and_practice = format_act_and_practice(source_leg)
    coverage_desc = (
        mapping.get("coverage") or llm_data.get("coverage") or ""
    )
    coverage_val = format_coverage(coverage_desc, scope_val)
    timeframe_val = format_timeframe(last_update, str(timeframe_col))
    refs_val = format_references(source_url)

    cluster_val = (
        mapping.get("cluster") or llm_data.get("cluster") or ""
    )
    name_val = (
        mapping.get("name") or llm_data.get("name") or ""
    )
    policy_desc_val = (
        mapping.get("policy_description") or llm_data.get("policy_description") or ""
    )
    region_val = (
        mapping.get("region") or llm_data.get("region") or derive_economy_region(economy)
    )
    cov_name_val = (
        mapping.get("cov_name") or derive_cov_name(scope_val)
    )

    return {
        "country": economy if economy else "[PENDING HUMAN REVIEW]",
        "Act.and.or.practice": act_and_practice,
        "Coverage": coverage_val,
        "Timeframe": timeframe_val,
        "References": refs_val,
        "cluster": cluster_val if cluster_val else "[PENDING HUMAN REVIEW]",
        "Region": region_val if region_val else "[PENDING HUMAN REVIEW]",
        "Cov.Name": cov_name_val,
        "name": name_val if name_val else "[PENDING HUMAN REVIEW]",
        "policy.description": policy_desc_val if policy_desc_val else "[PENDING HUMAN REVIEW]",
    }


def build_failed_row(economy: str, indicator_id: str) -> dict:
    return {
        "country": economy if economy else "[PENDING HUMAN REVIEW]",
        "Act.and.or.practice": "[PENDING HUMAN REVIEW]",
        "Coverage": "",
        "Timeframe": "",
        "References": "[PENDING HUMAN REVIEW]",
        "cluster": "[PENDING HUMAN REVIEW]",
        "Region": derive_economy_region(economy) if economy else "[PENDING HUMAN REVIEW]",
        "Cov.Name": "",
        "name": "[PENDING HUMAN REVIEW]",
        "policy.description": "[PENDING HUMAN REVIEW]",
    }


OUTPUT_COLUMNS = [
    "country",
    "Act.and.or.practice",
    "Coverage",
    "Timeframe",
    "References",
    "cluster",
    "Region",
    "Cov.Name",
    "name",
    "policy.description",
]


def main():
    log("═" * 60)
    log("RDTII Batch Processor — Legal Inventory Target Schema", CYAN)
    log("Output columns: " + ", ".join(OUTPUT_COLUMNS), CYAN)
    log("═" * 60)

    seed_file = sys.argv[1] if len(sys.argv) > 1 else "seed_tasks.csv"
    if not os.path.isfile(seed_file):
        log(f"FATAL: seed file not found: {seed_file}", RED)
        sys.exit(1)

    tasks = read_seed_tasks(seed_file)
    if not tasks:
        log(f"No tasks found in {seed_file}", YELLOW)
        sys.exit(0)

    log(f"\nProcessing {len(tasks)} task(s) ...\n")

    all_rows: list[dict] = []
    total_start = time.perf_counter()

    for i, task in enumerate(tasks, 1):
        economy = task["economy"]
        indicator_id = task["indicator_id"]
        source_url = task["source_url"]

        log(f"[{i}/{len(tasks)}] {economy} | indicator {indicator_id}")
        log(f"  URL: {source_url}")

        task_start = time.perf_counter()
        data = call_extract_api(source_url)
        elapsed = time.perf_counter() - task_start

        if data is None:
            log(f"  → FAILED ({elapsed:.1f}s)", RED)
            all_rows.append(build_failed_row(economy, indicator_id))
            continue

        mappings = data.get("mappings") or []
        rejected = data.get("rejected") or []

        if not mappings:
            log(f"  → No mappings returned ({elapsed:.1f}s)", YELLOW)
            row = build_failed_row(economy, indicator_id)
            row["Timeframe"] = "API returned no mappings"
            all_rows.append(row)
            continue

        matched = 0
        other = 0
        for apimap in mappings:
            mapping_indicator = apimap.get("indicator", "")
            if indicator_id and mapping_indicator == indicator_id:
                matched += 1
            elif indicator_id:
                other += 1

            row = map_mapping_to_row(economy, indicator_id, apimap, apimap)
            all_rows.append(row)

        parts = [f"{len(mappings)} mapping(s)"]
        if matched:
            parts.append(f"{matched} target")
        if other:
            parts.append(f"{other} other indicator(s)")
        parts.append(f"{len(rejected)} rejected")
        log(f"  → {', '.join(parts)} ({elapsed:.1f}s)", GREEN)

        # Log details for first few rows
        if matched and i <= 3:
            for row in all_rows[-matched:]:
                log(f"    └─ {row['country']} | {row['Act.and.or.practice'][:60]}...", CYAN)

        log("")

    total_elapsed = time.perf_counter() - total_start

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"final_rdtii_submission_{timestamp}.csv"

    log("Writing CSV ...", CYAN)
    df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    log(f"  → {out_path} ({len(all_rows)} rows, {os.path.getsize(out_path):,} bytes)", GREEN)

    # Count mandatory field gaps for [PENDING HUMAN REVIEW]
    pending_review_fields = [
        "Act.and.or.practice",
        "References",
        "cluster",
        "Region",
        "name",
        "policy.description",
    ]
    total_gaps = 0
    for field in pending_review_fields:
        gaps = sum(1 for r in all_rows if r.get(field, "") == "[PENDING HUMAN REVIEW]")
        total_gaps += gaps
        if gaps:
            log(f"  ⚠ {field}: {gaps} row(s) marked [PENDING HUMAN REVIEW]", YELLOW)

    success = sum(1 for r in all_rows if r["Act.and.or.practice"] != "[PENDING HUMAN REVIEW]")
    failed = len(all_rows) - success

    log("═" * 60)
    log(f"Done  |  Total rows: {len(all_rows)}  "
        f"|  Success: {success}  |  Failed: {failed}  "
        f"|  Pending review fields: {total_gaps}")
    log(f"Time  |  {total_elapsed:.1f}s total ({total_elapsed/len(tasks):.1f}s per task)")
    log(f"Output|  {out_path}")
    log("═" * 60)


if __name__ == "__main__":
    main()
