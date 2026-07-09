"""
Runs the broker-list layer (scoring/broker_list.py) across every registered
city with the exact same code path, and writes one combined CSV. Unlike
the society-fit layer, broker extraction needs no per-city config (no price
band, no minimum threshold) - it runs on whatever scraped data exists for a
city, or reports "no data" cleanly if a city hasn't been scraped yet.

Usage: python build_broker_list.py
"""

import csv

from config.cities import CITIES
from scoring.broker_list import compute_broker_list
from storage.db import get_connection, init_db

OUT_PATH = "output/broker_list_all_cities.csv"

FIELDNAMES = [
    "city_id", "corridor", "agent_display", "agent_normalized",
    "phone", "company", "listing_count", "broker_activity_score",
]


def run_all_cities() -> list:
    init_db()
    conn = get_connection()

    run_results = []
    for city_id, city in CITIES.items():
        run_result = compute_broker_list(conn, city)
        run_results.append(run_result)
        print(f"[{city_id}] {run_result.message}", flush=True)

    conn.close()
    return run_results


def write_csv(run_results: list) -> int:
    total_rows = 0
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for run_result in run_results:
            for r in run_result.results:
                writer.writerow(
                    {
                        "city_id": r.city_id,
                        "corridor": r.corridor,
                        "agent_display": r.agent_display,
                        "agent_normalized": r.agent_normalized,
                        "phone": r.phone or "",
                        "company": r.company or "",
                        "listing_count": r.listing_count,
                        "broker_activity_score": r.broker_activity_score,
                    }
                )
                total_rows += 1
    return total_rows


if __name__ == "__main__":
    results = run_all_cities()
    n = write_csv(results)
    print(f"\nWrote {n} rows to {OUT_PATH}", flush=True)
