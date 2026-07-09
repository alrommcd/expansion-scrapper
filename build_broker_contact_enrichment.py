"""
Runs broker contact enrichment (scoring/broker_contact_enrichment.py) across
every unique (city, agent_normalized) pair already in broker_meta - one
lookup per real-world business, not per corridor row, since the same agency
active in two corridors of the same city is the same business to look up
once. Reads broker_meta directly (the locked table), never modifies it.

Usage: python build_broker_contact_enrichment.py
"""

import csv
from collections import Counter

from config.cities import CITIES
from scoring.broker_contact_enrichment import BrokerLookupSubject, enrich_brokers
from storage.db import get_connection, init_db

OUT_PATH = "output/broker_contact_enrichment_all_cities.csv"
FIELDNAMES = ["city_id", "agent_normalized", "agent_display", "matched", "phone", "website", "address", "source", "confidence_note"]


def _unique_subjects(conn) -> list[BrokerLookupSubject]:
    """One subject per real-world (city, agent_normalized) business - NOT
    `SELECT DISTINCT city_id, agent_normalized, agent_display`, which
    double-counts an agent whose corridors disagree on capitalization (found
    2026-07-06: Bangalore's "global edifice infra" is spelled "GLOBAL EDIFICE
    INFRA" in one corridor's broker_meta row and "Global Edifice Infra" in
    another - same normalized key, two DISTINCT display spellings, which
    would have queried the Places API twice for the same business). Groups
    in Python and picks the most common display spelling across all of that
    agent's corridors, same tie-break broker_list.py already uses within one
    corridor."""
    rows = conn.execute(
        "SELECT city_id, agent_normalized, agent_display FROM broker_meta ORDER BY city_id, agent_normalized"
    ).fetchall()

    display_counts: dict[tuple[str, str], Counter] = {}
    for city_id, agent_normalized, agent_display in rows:
        key = (city_id, agent_normalized)
        display_counts.setdefault(key, Counter())[agent_display] += 1

    return [
        BrokerLookupSubject(
            city_id=city_id,
            city_name=CITIES[city_id].city_name,
            agent_normalized=agent_normalized,
            agent_display=counts.most_common(1)[0][0],
        )
        for (city_id, agent_normalized), counts in sorted(display_counts.items())
        if city_id in CITIES
    ]


def run_all() -> int:
    init_db()
    conn = get_connection()
    subjects = _unique_subjects(conn)
    print(f"Resolving contact info for {len(subjects)} unique brokers/agencies...", flush=True)
    results = enrich_brokers(conn, subjects)
    conn.close()

    matched = sum(1 for r in results.values() if r.matched)
    print(f"Matched {matched}/{len(subjects)} confidently.", flush=True)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for s in subjects:
            r = results[(s.city_id, s.agent_normalized)]
            writer.writerow(
                {
                    "city_id": s.city_id,
                    "agent_normalized": s.agent_normalized,
                    "agent_display": s.agent_display,
                    "matched": int(r.matched),
                    "phone": r.phone or "",
                    "website": r.website or "",
                    "address": r.address or "",
                    "source": r.source or "",
                    "confidence_note": r.confidence_note,
                }
            )
    print(f"Wrote {len(subjects)} rows to {OUT_PATH}", flush=True)
    return len(subjects)


if __name__ == "__main__":
    run_all()
