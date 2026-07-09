"""
Runs society detail enrichment (scoring/society_enrichment.py) across every
qualifying society already in society_meta - the same set Society Finder
shows, so nothing is enriched that isn't already a real, scored society.
Reads society_meta directly (the locked table), never modifies it.

Usage: python build_society_enrichment.py
"""

import csv

from config.cities import CITIES
from scoring.society_enrichment import SocietyLookupSubject, enrich_societies_detail
from storage.db import get_connection, init_db

OUT_PATH = "output/society_detail_enrichment_all_cities.csv"
FIELDNAMES = [
    "city_id", "corridor", "society_normalized", "society_display", "matched", "official_url",
    "unit_count", "possession_status", "rera_number", "sales_contact", "project_description",
    "source", "confidence_note",
]


def _subjects(conn) -> list[SocietyLookupSubject]:
    rows = conn.execute(
        "SELECT city_id, corridor, society_normalized, society_display FROM society_meta ORDER BY city_id, corridor"
    ).fetchall()
    return [
        SocietyLookupSubject(
            city_id=r[0], city_name=CITIES[r[0]].city_name, corridor=r[1],
            society_normalized=r[2], society_display=r[3],
        )
        for r in rows
        if r[0] in CITIES
    ]


def run_all() -> int:
    init_db()
    conn = get_connection()
    subjects = _subjects(conn)
    print(f"Resolving detail enrichment for {len(subjects)} qualifying societies...", flush=True)
    results = enrich_societies_detail(conn, subjects)
    conn.close()

    matched = sum(1 for r in results.values() if r.matched)
    print(f"Matched {matched}/{len(subjects)} confidently.", flush=True)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for s in subjects:
            r = results[(s.city_id, s.corridor, s.society_normalized)]
            writer.writerow(
                {
                    "city_id": s.city_id,
                    "corridor": s.corridor,
                    "society_normalized": s.society_normalized,
                    "society_display": s.society_display,
                    "matched": int(r.matched),
                    "official_url": r.official_url or "",
                    "unit_count": r.unit_count or "",
                    "possession_status": r.possession_status or "",
                    "rera_number": r.rera_number or "",
                    "sales_contact": r.sales_contact or "",
                    "project_description": r.project_description or "",
                    "source": r.source or "",
                    "confidence_note": r.confidence_note,
                }
            )
    print(f"Wrote {len(subjects)} rows to {OUT_PATH}", flush=True)
    return len(subjects)


if __name__ == "__main__":
    run_all()
