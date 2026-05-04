"""
Seed Chapter 1 data into PostgreSQL for one country.
Populates: countries, rdtii_pillars tables.
"""

import json
import os
import sys
import uuid
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# ── Config ────────────────────────────────────────────────────
DATASET_PATH = Path(__file__).parent / "rdtii-database" / "documents" / "DataSet" / "ESCAP-RDTII" / "rdtii_dataset.json"
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "rdtii"),
    "user": os.getenv("POSTGRES_USER", "rdtii_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "rdtii_password"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}
TARGET_COUNTRY = "Singapore"
TARGET_CHAPTER = 1

# ── Country metadata ──────────────────────────────────────────
COUNTRY_CODES = {
    "Armenia": "ARM", "Australia": "AUS", "China": "CHN", "Indonesia": "IDN",
    "India": "IND", "Japan": "JPN", "Kazakhstan": "KAZ", "Cambodia": "KHM",
    "Lao PDR": "LAO", "Nepal": "NPL", "New Zealand": "NZL", "Pakistan": "PAK",
    "Philippines": "PHL", "Russian Federation": "RUS", "Singapore": "SGP",
    "Thailand": "THA", "Türkiye": "TUR", "Vanuatu": "VUT",
}


def load_dataset():
    with open(DATASET_PATH) as f:
        return json.load(f)


def seed_countries(cur, dataset):
    """Insert all 18 countries if not already present."""
    rows = []
    for c in dataset["countries"]:
        code = COUNTRY_CODES.get(c["country"], c["country"][:3].upper())
        rows.append((code, c["country"], "Asia-Pacific", True))

    cur.execute("SELECT code FROM countries")
    existing = {row[0] for row in cur.fetchall()}

    to_insert = [r for r in rows if r[0] not in existing]
    if to_insert:
        execute_values(
            cur,
            "INSERT INTO countries (code, name, region, is_escap_member) VALUES %s",
            to_insert,
        )
        print(f"  Inserted {len(to_insert)} countries")
    else:
        print("  Countries already seeded")


def seed_pillars(cur, dataset, country_name, chapter):
    """Insert chapter indicators as pillar rows for one country."""
    country_data = next((c for c in dataset["countries"] if c["country"] == country_name), None)
    if not country_data:
        print(f"  Country '{country_name}' not found in dataset")
        return 0

    indicators = [i for i in country_data["indicators"] if i.get("chapter") == chapter]
    if not indicators:
        print(f"  Chapter {chapter} not found for {country_name}")
        return 0

    # Clear existing for this country+chapter to allow re-seeding
    cur.execute("""
        DELETE FROM rdtii_pillars
        WHERE pillar_number = %s AND country_code = %s
    """, (chapter, COUNTRY_CODES.get(country_name, "XXX")))

    rows = []
    for ind in indicators:
        question = str(ind.get("question", ""))
        pillar_name = f"Chapter {chapter}"
        criterion_id = f"{country_name}_{question}"
        criterion_name = ind.get("source_legislation", question)
        indicator_id = f"{criterion_id}_ind"
        indicator_desc = ind.get("question_description", "")
        weight = ind.get("individual_indicator_score")
        ops = ind.get("overall_pillar_score")
        references = json.dumps(ind.get("references", []))
        country_code = COUNTRY_CODES.get(country_name, "XXX")

        rows.append((
            str(uuid.uuid4()), chapter, pillar_name, country_code,
            criterion_id, criterion_name,
            indicator_id, indicator_desc,
            weight, ops, references,
        ))

    execute_values(
        cur,
        """
        INSERT INTO rdtii_pillars (
            pillar_id, pillar_number, pillar_name, country_code,
            criterion_id, criterion_name,
            indicator_id, indicator_description,
            weight_score, overall_pillar_score, "references"
        ) VALUES %s
        """,
        rows,
    )

    print(f"  Inserted {len(rows)} indicators for {country_name} Chapter {chapter}")
    return len(rows)


def show_seeded_data(cur, country_name, chapter):
    """Print seeded pillar data to verify."""
    cur.execute("""
        SELECT pillar_number, country_code, criterion_id, criterion_name,
               indicator_description, weight_score, overall_pillar_score, "references"
        FROM rdtii_pillars
        WHERE pillar_number = %s
        ORDER BY criterion_id
    """, (chapter,))

    rows = cur.fetchall()
    code = COUNTRY_CODES.get(country_name, "XXX")
    print(f"\n{'─' * 80}")
    print(f"Seeded: {country_name} ({code}) — Chapter {chapter}")
    print(f"{'─' * 80}")
    for row in rows:
        pillar_num, cc, crit_id, crit_name, ind_desc, weight, ops, refs = row
        print(f"\n  [ID]      {crit_id}")
        print(f"  [Text]    {crit_name[:120]}")
        print(f"  [Desc]    {ind_desc[:120]}")
        print(f"  [Score]   {weight}    [OPS]   {ops}")
        print(f"  [Refs]    {refs}")


def main():
    print(f"Connecting to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        dataset = load_dataset()

        print("\n[1/2] Seeding countries...")
        seed_countries(cur, dataset)

        print(f"\n[2/2] Seeding {TARGET_COUNTRY} Chapter {TARGET_CHAPTER}...")
        count = seed_pillars(cur, dataset, TARGET_COUNTRY, TARGET_CHAPTER)

        if count > 0:
            show_seeded_data(cur, TARGET_COUNTRY, TARGET_CHAPTER)

        conn.commit()
        print(f"\nDone. {count} indicators imported.")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
