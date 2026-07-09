"""
Combines each city's `output/absentee_candidates_{city_id}_full.csv` (written
by run_production_pipeline.py) into one cross-city deliverable. Pure file
merge, no scraping/DB access, safe to run any time after all five per-city
CSVs exist.

Usage: python combine_city_outputs.py
"""

import csv

CITY_IDS = ["pune", "mumbai", "bangalore", "hyderabad", "chennai"]
FIELDNAMES = [
    "listing_id", "city_id", "corridor", "society", "signal_matched", "score",
    "days_since_posted", "detail_url", "address_recovered", "owner_note", "evidence",
]
OUT_PATH = "output/absentee_candidates_all_cities.csv"


def combine() -> int:
    total_rows = 0
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for city_id in CITY_IDS:
            in_path = f"output/absentee_candidates_{city_id}_full.csv"
            with open(in_path, encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f)
                city_rows = 0
                for row in reader:
                    writer.writerow(row)
                    city_rows += 1
            print(f"{city_id}: {city_rows} rows", flush=True)
            total_rows += city_rows
    print(f"Wrote {total_rows} total rows to {OUT_PATH}", flush=True)
    return total_rows


if __name__ == "__main__":
    combine()
