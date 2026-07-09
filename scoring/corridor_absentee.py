"""
Corridor-level Absentee Score (Phase B). 100% deterministic, reads
raw_listings directly - no Gemini, no classification pipeline dependency.
This is a NEW, separate scorer from scoring/absentee.py (which does
per-listing Tier 1/2/3 point scoring on classified_listings for the
society drill-down); this one aggregates straight from raw scrape data for
the city-wide corridor pass, matching the Phase B design decision to keep
Gemini out of that pass entirely.

vacancy_pct is text-based only ("vacant" / "immediate possession" literal
mentions). The user asked for a stronger proxy - listings where
possession_date is in the past but still actively listed - but that field
does not exist in our scraped data: MagicBricks exposes a status category
(ready_to_move / under_construction), not a possession date, and a check
of all 870 currently-scraped Pune listings found 0 with a structured
possession date and only 2 mentioning one in free text. Skipped per
instruction not to fabricate, see DECISIONS.md 2026-07-05.

distressed_pct requires a listing to be BOTH 15%+ below the corridor's
median price-per-sqft AND listed 60+ days - a cheap listing that sells
fast isn't distressed, it was priced right.

avg_age_days is still computed and returned here for information (it's a
useful number to see in a report), but as of 2026-07-05 it no longer feeds
absentee_score - see corridor_absentee_config.py docstring for why.
"""

import json
import sqlite3
import statistics
from dataclasses import dataclass

from classify.parsing import parse_area_sqft, parse_days_since_posted, parse_price_inr
from scoring.corridor_absentee_config import (
    DISTRESSED_BELOW_MARKET_RATIO,
    DISTRESSED_MIN_AGE_DAYS,
    STALE_90D_THRESHOLD_DAYS,
    absentee_score_from_raw,
    compute_raw,
)


@dataclass
class CorridorAbsenteeResult:
    corridor: str
    total_listings: int
    avg_age_days: float | None
    stale_90d_pct: float | None
    vacancy_pct: float | None
    distressed_pct: float | None
    absentee_score: float | None  # None if required inputs are missing - never fabricated


def _vacancy_text_hit(description: str | None) -> bool:
    if not description:
        return False
    text = description.lower()
    return "vacant" in text or "immediate possession" in text


def score_corridor_absentee(conn: sqlite3.Connection, city_id: str, corridor: str) -> CorridorAbsenteeResult:
    rows = conn.execute(
        "SELECT raw_text FROM raw_listings WHERE city_id = ? AND corridor = ?",
        (city_id, corridor),
    ).fetchall()

    n = len(rows)
    if n == 0:
        return CorridorAbsenteeResult(corridor, 0, None, None, None, None, None)

    ages: list[int] = []
    vacancy_hits = 0
    prices_per_sqft: list[float] = []
    parsed_listings = []

    for (raw_text,) in rows:
        d = json.loads(raw_text)
        age = parse_days_since_posted(d.get("posted_recency_raw"))
        price = parse_price_inr(d.get("price_raw"))
        area = parse_area_sqft(d.get("carpet_area_raw"))
        pps = price / area if price and area else None

        if age is not None:
            ages.append(age)
        if _vacancy_text_hit(d.get("description_raw")):
            vacancy_hits += 1
        if pps is not None:
            prices_per_sqft.append(pps)

        parsed_listings.append({"age": age, "pps": pps})

    avg_age_days = sum(ages) / len(ages) if ages else None
    stale_90d_pct = (
        100 * sum(1 for a in ages if a >= STALE_90D_THRESHOLD_DAYS) / len(ages) if ages else None
    )
    vacancy_pct = 100 * vacancy_hits / n

    median_pps = statistics.median(prices_per_sqft) if prices_per_sqft else None
    if median_pps is not None:
        distressed_count = sum(
            1
            for listing in parsed_listings
            if listing["pps"] is not None
            and listing["age"] is not None
            and listing["pps"] < median_pps * DISTRESSED_BELOW_MARKET_RATIO
            and listing["age"] >= DISTRESSED_MIN_AGE_DAYS
        )
        distressed_pct = 100 * distressed_count / n
    else:
        distressed_pct = None

    if stale_90d_pct is not None and distressed_pct is not None:
        raw = compute_raw(stale_90d_pct, vacancy_pct, distressed_pct)
        absentee_score = absentee_score_from_raw(raw)
    else:
        absentee_score = None

    return CorridorAbsenteeResult(
        corridor=corridor,
        total_listings=n,
        avg_age_days=round(avg_age_days, 2) if avg_age_days is not None else None,
        stale_90d_pct=round(stale_90d_pct, 2) if stale_90d_pct is not None else None,
        vacancy_pct=round(vacancy_pct, 2),
        distressed_pct=round(distressed_pct, 2) if distressed_pct is not None else None,
        absentee_score=absentee_score,
    )
