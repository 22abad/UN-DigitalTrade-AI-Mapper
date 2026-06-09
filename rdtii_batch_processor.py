#!/usr/bin/env python3
"""
rdtii_batch_processor.py — Standalone batch client for the RDTII AI Mapper.

Reads seed_tasks.csv → calls POST /api/extract for each row → maps response
to the RDTII 2.1 submission format → writes final_rdtii_submission_*.csv.

RDTII 2.1 output columns (per assignment02 Format Requirements):
    Pillar_ID, Indicator_ID, Cat_Score, Raw Score, Act and/or practice,
    Coverage, Impact or comments on Acts or practices, Timeframe,
    References, Note

Usage:
    python rdtii_batch_processor.py
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
REQUEST_TIMEOUT = int(os.getenv("RDTII_TIMEOUT", "120"))  # seconds
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log(msg: str, color: str = ""):
    print(f"{color}{msg}{RESET}", flush=True)


def read_seed_tasks(path: str = "seed_tasks.csv") -> list[dict]:
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
    return tasks


def call_extract_api(source_url: str) -> dict | None:
    try:
        resp = requests.post(
            API_URL,
            data={"source_url": source_url},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        log(f"  TIMEOUT after {REQUEST_TIMEOUT}s", RED)
    except requests.exceptions.RequestException as e:
        log(f"  API error: {e}", RED)
    except Exception as e:
        log(f"  Unexpected error: {e}", RED)
    return None


def map_mapping_to_row(
    economy: str,
    indicator_id: str,
    mapping: dict,
) -> dict:
    return {
        "Economy": economy,
        "Pillar_ID": mapping.get("pillar", ""),
        "Indicator_ID": mapping.get("indicator", indicator_id),
        "Cat_Score": "",
        "Raw Score": mapping.get("score", ""),
        "Act and/or practice": mapping.get("source_legislation", ""),
        "Coverage": mapping.get("scope", ""),
        "Impact or comments on Acts or practices": mapping.get("impact", ""),
        "Timeframe": mapping.get("last_update", ""),
        "References": mapping.get("source_url", ""),
        "Note": "",
    }


def build_failed_row(economy: str, indicator_id: str) -> dict:
    return {
        "Economy": economy,
        "Pillar_ID": "",
        "Indicator_ID": indicator_id,
        "Cat_Score": "",
        "Raw Score": "FAILED",
        "Act and/or practice": "",
        "Coverage": "",
        "Impact or comments on Acts or practices": "",
        "Timeframe": "",
        "References": "",
        "Note": "API call failed or timed out",
    }


OUTPUT_COLUMNS = [
    "Economy",
    "Pillar_ID",
    "Indicator_ID",
    "Cat_Score",
    "Raw Score",
    "Act and/or practice",
    "Coverage",
    "Impact or comments on Acts or practices",
    "Timeframe",
    "References",
    "Note",
]


def main():
    log("╔══════════════════════════════════════════════╗")
    log("║  RDTII 2.1 Batch Processor — Assignment 02  ║")
    log("╚══════════════════════════════════════════════╝")

    seed_file = sys.argv[1] if len(sys.argv) > 1 else "seed_tasks.csv"
    if not os.path.isfile(seed_file):
        log(f"ERROR: seed file not found: {seed_file}", RED)
        sys.exit(1)

    tasks = read_seed_tasks(seed_file)
    if not tasks:
        log(f"No tasks found in {seed_file}", YELLOW)
        sys.exit(0)

    log(f"Loaded {len(tasks)} task(s) from {seed_file}\n")

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
            all_rows.append(build_failed_row(economy, indicator_id))
            continue

        matched = 0
        other = 0
        for mapping in mappings:
            mapping_indicator = mapping.get("indicator", "")
            if indicator_id and mapping_indicator == indicator_id:
                matched += 1
            elif indicator_id:
                other += 1
            row = map_mapping_to_row(economy, indicator_id, mapping)
            all_rows.append(row)

        parts = [f"{len(mappings)} mapping(s)"]
        if matched:
            parts.append(f"{matched} target")
        if other:
            parts.append(f"{other} other indicator(s)")
        parts.append(f"{len(rejected)} rejected")
        log(f"  → {', '.join(parts)} ({elapsed:.1f}s)", GREEN)

        log("")

    total_elapsed = time.perf_counter() - total_start

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"final_rdtii_submission_{timestamp}.csv"

    df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    success = sum(
        1 for r in all_rows if r["Raw Score"] != "FAILED"
    )
    failed = len(all_rows) - success

    log("═" * 50)
    log(f"Done  |  Total rows: {len(all_rows)}  "
        f"|  Success: {success}  |  Failed: {failed}")
    log(f"Time  |  {total_elapsed:.1f}s total")
    log(f"Output|  {out_path}")
    log("═" * 50)


if __name__ == "__main__":
    main()
