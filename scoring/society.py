"""
City-agnostic society fit scorer. Reads entity-resolved classified_listings
grouped by society_id, no city-specific logic (same pattern as
scoring/corridor.py). See scoring/society_config.py for the signal
definitions, proxies, and normalization caps (single source of truth,
backend-only).
"""

import sqlite3
from dataclasses import dataclass

from scoring.society_config import CAPS, PRICE_BAND_MAX_INR, PRICE_BAND_MIN_INR


@dataclass
class SocietyResult:
    society_id: int
    canonical_name: str
    listing_count: int
    sub_scores: dict[str, float]
    fit_score: float


def _fetch_society_listings(conn: sqlite3.Connection, city_id: str, corridor: str) -> dict[int, list[sqlite3.Row]]:
    rows = conn.execute(
        "SELECT cl.society_id, cl.price_inr, cl.possession_status, cl.mentions_rera, "
        "cl.days_since_posted "
        "FROM classified_listings cl "
        "JOIN raw_listings rl ON cl.raw_listing_id = rl.id "
        "WHERE rl.city_id = ? AND rl.corridor = ? AND cl.society_id IS NOT NULL",
        (city_id, corridor),
    ).fetchall()

    by_society: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        by_society.setdefault(row["society_id"], []).append(row)
    return by_society


def _score_one_society(listings: list[sqlite3.Row]) -> dict[str, float]:
    n = len(listings)

    in_band = sum(
        1 for r in listings if r["price_inr"] and PRICE_BAND_MIN_INR <= r["price_inr"] <= PRICE_BAND_MAX_INR
    )
    price_band_fit = in_band / n

    ready_to_move = sum(1 for r in listings if r["possession_status"] == "ready_to_move")
    possession_status = ready_to_move / n

    rera_mentions = sum(1 for r in listings if r["mentions_rera"])
    title_cleanliness = rera_mentions / n

    listing_density = min(n / CAPS.listing_density_cap, 1.0)

    recency_values = [r["days_since_posted"] for r in listings if r["days_since_posted"] is not None]
    if recency_values:
        resale_liquidity = sum(
            max(0.0, 1 - d / CAPS.recency_cap_days) for d in recency_values
        ) / len(recency_values)
    else:
        resale_liquidity = 0.5  # neutral fallback, no recency data available

    return {
        "price_band_fit": round(price_band_fit, 4),
        "resale_liquidity": round(resale_liquidity, 4),
        "listing_density": round(listing_density, 4),
        "title_cleanliness": round(title_cleanliness, 4),
        "possession_status": round(possession_status, 4),
    }


def rank_societies(conn: sqlite3.Connection, city_id: str, corridor: str) -> list[SocietyResult]:
    by_society = _fetch_society_listings(conn, city_id, corridor)
    society_names = {
        row["id"]: row["canonical_name"]
        for row in conn.execute(
            "SELECT id, canonical_name FROM societies WHERE city_id = ? AND corridor = ?",
            (city_id, corridor),
        ).fetchall()
    }

    results = []
    for society_id, listings in by_society.items():
        sub_scores = _score_one_society(listings)
        fit_score = round(sum(sub_scores.values()) / len(sub_scores), 4)
        results.append(
            SocietyResult(
                society_id=society_id,
                canonical_name=society_names.get(society_id, "Unknown"),
                listing_count=len(listings),
                sub_scores=sub_scores,
                fit_score=fit_score,
            )
        )

    return sorted(results, key=lambda r: r.fit_score, reverse=True)
