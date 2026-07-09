"""Orchestrates classification: pulls unclassified raw_listings for a
city/corridor, applies deterministic parsing + Gemini flags (in batches,
to respect the free-tier rate limit), writes to classified_listings."""

import json
import sqlite3
import time
from datetime import datetime, timezone

from classify.gemini_client import BATCH_SIZE, classify_flags_batch, get_client
from classify.parsing import (
    parse_area_sqft,
    parse_bhk,
    parse_days_since_posted,
    parse_international_contact_hint,
    parse_listing_type,
    parse_mentions_rera,
    parse_possession_status,
    parse_price_inr,
)
from classify.schema import ListingClassification

SLEEP_BETWEEN_BATCHES_SECONDS = 13  # keeps us under the 5 requests/minute free-tier quota


def _fetch_unclassified(conn: sqlite3.Connection, city_id: str, corridor: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, raw_text FROM raw_listings "
        "WHERE city_id = ? AND corridor = ? "
        "AND id NOT IN (SELECT raw_listing_id FROM classified_listings)",
        (city_id, corridor),
    ).fetchall()


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def run_classification(conn: sqlite3.Connection, city_id: str, corridor: str) -> int:
    rows = _fetch_unclassified(conn, city_id, corridor)
    if not rows:
        return 0

    client = get_client()
    now = datetime.now(timezone.utc).isoformat()
    total_classified = 0
    batches = _chunks(rows, BATCH_SIZE)

    for batch_num, row_batch in enumerate(batches):
        parsed = [json.loads(row["raw_text"]) for row in row_batch]
        gemini_inputs = [
            {
                "title": d.get("title"),
                "society_name_raw": d.get("society_name_raw"),
                "description": d.get("description_raw") or "",
            }
            for d in parsed
        ]
        flags_list = classify_flags_batch(client, gemini_inputs)

        for row, d, flags in zip(row_batch, parsed, flags_list):
            classification = ListingClassification(
                society_name_as_written=flags.society_name_normalized or d.get("society_name_raw"),
                price_inr=parse_price_inr(d.get("price_raw")),
                area_sqft=parse_area_sqft(d.get("carpet_area_raw")),
                bhk=parse_bhk(d.get("title")),
                listing_type=parse_listing_type(d.get("posted_by_raw")),
                possession_status=parse_possession_status(d.get("status")),
                days_since_posted=parse_days_since_posted(d.get("posted_recency_raw")),
                mentions_rera=parse_mentions_rera(d.get("description_raw")),
                flag_nri_mention=flags.flag_nri_mention,
                flag_poa_mention=flags.flag_poa_mention,
                flag_owner_abroad=flags.flag_owner_abroad,
                flag_owner_not_local=flags.flag_owner_not_local,
                flag_visit_by_appointment_only=flags.flag_visit_by_appointment_only,
                flag_calling_hours_hint=flags.flag_calling_hours_hint,
                flag_long_vacant_or_tenanted=flags.flag_long_vacant_or_tenanted,
                flag_investment_property_mention=flags.flag_investment_property_mention,
                flag_international_contact_hint=parse_international_contact_hint(
                    d.get("title"), d.get("description_raw")
                ),
            )
            conn.execute(
                "INSERT INTO classified_listings "
                "(raw_listing_id, society_name_as_written, price_inr, area_sqft, bhk, "
                "listing_type, possession_status, days_since_posted, mentions_rera, "
                "flag_nri_mention, flag_poa_mention, flag_owner_abroad, "
                "flag_international_contact_hint, flag_owner_not_local, "
                "flag_visit_by_appointment_only, flag_calling_hours_hint, "
                "flag_long_vacant_or_tenanted, flag_investment_property_mention, classified_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    classification.society_name_as_written,
                    classification.price_inr,
                    classification.area_sqft,
                    classification.bhk,
                    classification.listing_type,
                    classification.possession_status,
                    classification.days_since_posted,
                    int(classification.mentions_rera),
                    int(classification.flag_nri_mention),
                    int(classification.flag_poa_mention),
                    int(classification.flag_owner_abroad),
                    int(classification.flag_international_contact_hint),
                    int(classification.flag_owner_not_local),
                    int(classification.flag_visit_by_appointment_only),
                    int(classification.flag_calling_hours_hint),
                    int(classification.flag_long_vacant_or_tenanted),
                    int(classification.flag_investment_property_mention),
                    now,
                ),
            )
            total_classified += 1

        conn.commit()

        is_last_batch = batch_num == len(batches) - 1
        if not is_last_batch:
            time.sleep(SLEEP_BETWEEN_BATCHES_SECONDS)

    return total_classified
