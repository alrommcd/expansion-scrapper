"""
Runs the society-level product-fit layer (scoring/society_fit.py) across
every registered city with the exact same code path, and writes one
combined CSV - proof of city-agnosticism per the 2026-07-06 hard
constraint: no city gets special-cased, a city either has a
product_price_band configured (config/cities/<city>.py) and gets scored, or
it doesn't and is skipped with a clear reason - never scored against
another city's band.

Usage: python build_society_ranking.py
"""

import csv

from config.cities import CITIES
from scoring.society_fit import compute_society_fit
from storage.db import get_connection, init_db

OUT_PATH = "output/society_ranking_all_cities.csv"

FIELDNAMES = [
    "city_id", "corridor", "society_display", "society_normalized",
    "supply_depth", "resale_velocity_days", "price_consistency_cov",
    "rating", "review_count", "rating_available", "society_fit_score",
    "appears_in_corridors", "candidate_count", "candidate_listing_ids",
]


def run_all_cities() -> list:
    init_db()
    conn = get_connection()

    run_results = []
    for city_id, city in CITIES.items():
        run_result = compute_society_fit(conn, city)
        run_results.append(run_result)

        rated = sum(1 for r in run_result.results if r.rating_available)
        total = len(run_result.results)
        print(f"[{city_id}] {run_result.message}", flush=True)
        if run_result.status == "ok" and total:
            print(f"[{city_id}]   Google Maps rating: {rated}/{total} matched, {total - rated}/{total} NULL", flush=True)

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
                        "society_display": r.society_display,
                        "society_normalized": r.society_normalized,
                        "supply_depth": r.supply_depth,
                        "resale_velocity_days": r.resale_velocity_days,
                        "price_consistency_cov": r.price_consistency_cov,
                        "rating": r.rating,
                        "review_count": r.review_count,
                        "rating_available": int(r.rating_available),
                        "society_fit_score": r.society_fit_score,
                        "appears_in_corridors": ";".join(r.appears_in_corridors),
                        "candidate_count": r.candidate_count,
                        "candidate_listing_ids": ";".join(str(i) for i in r.candidate_listing_ids),
                    }
                )
                total_rows += 1
    return total_rows


if __name__ == "__main__":
    results = run_all_cities()
    n = write_csv(results)
    print(f"\nWrote {n} rows to {OUT_PATH}", flush=True)
