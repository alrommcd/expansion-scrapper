"""
Production pipeline (Track 1, 2026-07-06): for one city, scrape every
corridor to a minimum listing count, dedup, run the validated signal set,
recover detail-page address/owner info for flagged candidates only, write
a per-city CSV. Run once per city with the same code (city-agnostic) -
see DECISIONS.md for the per-city URL-pattern fixes this required.

Usage: python run_production_pipeline.py <city_id>
"""

import csv
import dataclasses
import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

from config.cities import get_city_config
from scraper.magicbricks import scrape_corridor
from storage.db import get_connection, init_db, insert_raw_listing
from storage.listing_dedup import find_duplicate_groups, apply_dedup
from scoring.validated_signals import find_validated_candidates

MIN_LISTINGS_PER_CORRIDOR = 200
PAGES_PER_CORRIDOR = 7  # ~30/page, 7 pages clears the 200 minimum
DELAY_BETWEEN_CORRIDORS_SECONDS = 3

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def scrape_city(city_id: str) -> None:
    city = get_city_config(city_id)
    init_db()
    conn = get_connection()

    print(f"=== Scraping {city.city_name} ({len(city.corridor_candidates)} corridors) ===", flush=True)
    for i, candidate in enumerate(city.corridor_candidates, 1):
        corridor = candidate.name
        print(f"[{i}/{len(city.corridor_candidates)}] {corridor} - scraping...", flush=True)
        try:
            listings = scrape_corridor(
                city_slug=city_id,
                corridor=corridor,
                max_listings=1000,
                pages=PAGES_PER_CORRIDOR,
                all_corridors=[c.name for c in city.corridor_candidates],
            )
        except Exception as e:
            print(f"[{i}/{len(city.corridor_candidates)}] {corridor} - BLOCKED/ERROR: {e!r}", flush=True)
            continue

        for listing in listings:
            raw_text = json.dumps(dataclasses.asdict(listing), ensure_ascii=False)
            insert_raw_listing(
                conn,
                city_id=city_id,
                corridor=corridor,
                source=listing.source,
                raw_text=raw_text,
                price_raw=listing.price_raw,
            )
        conn.commit()
        status = "OK" if len(listings) >= MIN_LISTINGS_PER_CORRIDOR else "BELOW MINIMUM"
        print(f"[{i}/{len(city.corridor_candidates)}] {corridor} - {len(listings)} listings scraped ({status})", flush=True)
        time.sleep(DELAY_BETWEEN_CORRIDORS_SECONDS)

    conn.close()


def dedup_city(city_id: str) -> dict:
    city = get_city_config(city_id)
    conn = get_connection()
    all_corridor_names = [c.name for c in city.corridor_candidates]
    groups = find_duplicate_groups(conn, city_id, all_corridor_names)
    marked = apply_dedup(conn, groups)
    total = conn.execute("SELECT COUNT(*) FROM raw_listings WHERE city_id = ?", (city_id,)).fetchone()[0]
    canonical = conn.execute(
        "SELECT COUNT(*) FROM raw_listings WHERE city_id = ? AND duplicate_of_id IS NULL", (city_id,)
    ).fetchone()[0]
    conn.close()
    print(f"Dedup: total={total} canonical={canonical} marked_duplicate={marked}", flush=True)
    return {"total": total, "canonical": canonical, "marked_duplicate": marked}


ADDRESS_PIN_RE = re.compile(r"[A-Za-z0-9,.\-\s]{10,100}\b\d{6}\b")
OWNER_RE = re.compile(r"Owner:\s*([A-Za-z .]{2,40})")


def recover_detail_pages(candidates: list) -> dict:
    """For each flagged candidate with a detail_url, visit it once and try
    to recover a genuine (non-RERA-number) address fragment and confirm
    whether the flagged owner name appears on the page."""

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)

        seen_urls = {}
        for cand in candidates:
            url = cand.detail_url
            if not url:
                results[cand.listing_id] = {"address": "UNAVAILABLE - no detail_url captured", "owner_note": "N/A"}
                continue
            if url in seen_urls:
                results[cand.listing_id] = seen_urls[url]
                continue

            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(1500)
                body_text = page.inner_text("body")

                raw_matches = ADDRESS_PIN_RE.findall(body_text)
                genuine = [m for m in raw_matches if "RERA" not in m and "P521" not in m and "P511" not in m]
                address = genuine[0].strip() if genuine else "UNAVAILABLE - no street-level address on page"

                owners_found = OWNER_RE.findall(body_text)
                entry = {"address": address, "owner_note": f"Owners visible on page: {owners_found[:8]}"}
            except Exception as e:
                entry = {"address": f"UNAVAILABLE - page error: {e!r}", "owner_note": "N/A"}
            page.close()

            seen_urls[url] = entry
            results[cand.listing_id] = entry

        browser.close()
    return results


def regenerate_evidence_column(city_id: str) -> str:
    """Adds the `evidence` column to an ALREADY-shipped
    absentee_candidates_{city_id}_full.csv without re-scraping or
    re-running recover_detail_pages (no Playwright/network needed) - the
    raw listings behind these candidates are already in expansion.db, so
    find_validated_candidates can be re-run DB-only to recompute the same
    candidate set (same rows, now with the new evidence field) and merge it
    onto the existing file's address_recovered/owner_note, which stay
    untouched. Used once, 2026-07-06, to backfill evidence into the 5
    already-shipped per-city CSVs after validated_signals.py gained the
    field, without redoing the live detail-page recovery step."""
    conn = get_connection()
    candidates = find_validated_candidates(conn, city_id)
    conn.close()
    evidence_by_id = {c.listing_id: c.evidence for c in candidates}

    in_path = f"output/absentee_candidates_{city_id}_full.csv"
    with open(in_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = [
        "listing_id", "city_id", "corridor", "society", "signal_matched", "score",
        "days_since_posted", "detail_url", "address_recovered", "owner_note", "evidence",
    ]
    with open(in_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row["evidence"] = evidence_by_id.get(int(row["listing_id"])) or "signal matched, detail not retained"
            writer.writerow(row)

    print(f"Backfilled evidence for {len(rows)} rows in {in_path}", flush=True)
    return in_path


def run_full_city_pipeline(city_id: str) -> str:
    scrape_city(city_id)
    dedup_stats = dedup_city(city_id)

    conn = get_connection()
    candidates = find_validated_candidates(conn, city_id)
    conn.close()
    print(f"Validated candidates found: {len(candidates)}", flush=True)

    detail_info = recover_detail_pages(candidates)

    out_path = f"output/absentee_candidates_{city_id}_full.csv"
    fieldnames = [
        "listing_id", "city_id", "corridor", "society", "signal_matched", "score",
        "days_since_posted", "detail_url", "address_recovered", "owner_note", "evidence",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cand in candidates:
            info = detail_info.get(cand.listing_id, {"address": "UNAVAILABLE", "owner_note": "N/A"})
            writer.writerow({
                "listing_id": cand.listing_id,
                "city_id": cand.city_id,
                "corridor": cand.corridor,
                "society": cand.society,
                "signal_matched": cand.signal_matched,
                "score": cand.score,
                "days_since_posted": cand.days_since_posted,
                "detail_url": cand.detail_url or "",
                "address_recovered": info["address"],
                "owner_note": info["owner_note"],
                "evidence": cand.evidence or "signal matched, detail not retained",
            })

    print(f"Wrote {len(candidates)} rows to {out_path}", flush=True)
    print(f"SUMMARY city={city_id} scraped_total={dedup_stats['total']} canonical={dedup_stats['canonical']} validated_candidates={len(candidates)}", flush=True)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--evidence-only":
        regenerate_evidence_column(sys.argv[1])
    else:
        run_full_city_pipeline(sys.argv[1])
