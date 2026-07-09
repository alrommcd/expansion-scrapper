"""
Society-level PRODUCT-FIT layer (rung 3: city -> corridor -> society ->
people, 2026-07-06). Answers "is this a GOOD SOCIETY for the product" - a
score fully separate from corridor fit_score (scoring/corridor.py) and from
absentee_score (scoring/validated_signals.py). All three stay distinct
numbers, never merged.

Four metrics per qualifying society (city+corridor scoped, in-band listings
only, minimum sample size MIN_LISTINGS):
  1. supply_depth      - count of in-band canonical listings (comp density proxy)
  2. resale_velocity   - avg days_since_posted (lower = more liquid)
  3. price_consistency - coefficient of variation of in-band price (lower = tighter)
  4. rating/review_count - Google Maps (scoring/maps_enrichment.py), may be NULL

Normalization is PERCENTILE RANK WITHIN THE CITY, not fixed thresholds - the
same code has to produce a meaningful 0-10 spread whether a city's raw
numbers run high or low, which is the whole point of staying city-agnostic.
Weights (user-specified): supply .30, velocity .30, consistency .20, rating
.20. When rating is unavailable for a society, the other three are
re-normalized to sum to 1 rather than silently zeroing the rating slice.

Reuses existing code rather than re-deriving it: parse_price_inr and
parse_days_since_posted (classify/parsing.py), the canonical-rows-only
query shape (same pattern as scoring/validated_signals.py's
_canonical_rows), normalize_society_name (storage/entity_resolution.py),
and find_validated_candidates (scoring/validated_signals.py) for the
Track-1 link. Never re-scrapes MagicBricks, never calls Gemini - the only
network call anywhere in this layer is the isolated Maps enrichment step.
"""

import json
import math
import sqlite3
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from classify.parsing import parse_days_since_posted, parse_price_inr
from config.city_config import CityConfig
from scoring.maps_enrichment import MapsLookupSubject, MapsResult, enrich_societies
from scoring.society_fit_config import (
    MIN_LISTINGS,
    WEIGHT_CONSISTENCY,
    WEIGHT_RATING,
    WEIGHT_SUPPLY,
    WEIGHT_VELOCITY,
)
from scoring.stats_utils import percentile_ranks
from scoring.validated_signals import find_validated_candidates
from storage.entity_resolution import normalize_society_name

_ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS society_meta (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    society_normalized TEXT NOT NULL,
    society_display TEXT NOT NULL,
    supply_depth INTEGER NOT NULL,
    resale_velocity_days REAL,
    price_consistency_cov REAL,
    rating REAL,
    review_count INTEGER,
    rating_available INTEGER NOT NULL DEFAULT 0,
    society_fit_score REAL,
    appears_in_corridors TEXT,
    last_computed TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, society_normalized)
);
CREATE TABLE IF NOT EXISTS maps_cache (
    query TEXT PRIMARY KEY,
    matched INTEGER NOT NULL,
    rating REAL,
    review_count INTEGER,
    looked_up_at TEXT NOT NULL
);
"""


@dataclass
class SocietyFitResult:
    city_id: str
    corridor: str
    society_display: str
    society_normalized: str
    supply_depth: int
    resale_velocity_days: float | None
    price_consistency_cov: float | None
    rating: float | None
    review_count: int | None
    rating_available: bool
    society_fit_score: float
    appears_in_corridors: list[str]
    candidate_listing_ids: list[int] = field(default_factory=list)

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_listing_ids)


@dataclass
class CityFitRunResult:
    city_id: str
    status: str  # "ok" | "skipped_no_price_band"
    message: str
    results: list[SocietyFitResult] = field(default_factory=list)


def _canonical_city_rows(conn: sqlite3.Connection, city_id: str) -> list[tuple[int, str, dict]]:
    rows = conn.execute(
        "SELECT id, corridor, raw_text FROM raw_listings WHERE city_id = ? AND duplicate_of_id IS NULL",
        (city_id,),
    ).fetchall()
    return [(rid, corridor, json.loads(raw)) for rid, corridor, raw in rows]


# Junk "society names" from a since-fixed scraper fallback bug
# (scraper/magicbricks.py's _society_from_url, 2026-07-07): when a listing
# card's first <a> was a shortlist/compare icon (href="javascript:void(0)")
# rather than the real detail link, the fallback title-cased that literal
# string into a fake society name that then scored like a real one (found
# live in Chennai/Bangalore data - see DECISIONS.md 2026-07-07). The
# scraper now rejects that input before ever producing it, but rows scraped
# before the fix still carry it in raw_listings.raw_text - this keeps them
# out of scoring without requiring a re-scrape. Exact match, not substring,
# same convention as PLACEHOLDER_OWNER_NAMES (scoring/validated_signals.py).
_JUNK_SOCIETY_NAMES = {"javascript:void(0)"}


def _group_in_band_listings(
    rows: list[tuple[int, str, dict]], price_min: int, price_max: int
) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = {}
    for _rid, corridor, d in rows:
        society_raw = d.get("society_name_raw")
        if not society_raw or society_raw.strip().lower() in _JUNK_SOCIETY_NAMES:
            continue
        price = parse_price_inr(d.get("price_raw"))
        if price is None or not (price_min <= price <= price_max):
            continue

        normalized = normalize_society_name(society_raw)
        key = (corridor, normalized)
        group = groups.setdefault(key, {"display_names": Counter(), "prices": [], "days": []})
        group["display_names"][society_raw] += 1
        group["prices"].append(price)
        group["days"].append(parse_days_since_posted(d.get("posted_recency_raw")))
    return groups


def _raw_metrics_for(group: dict) -> dict:
    prices = group["prices"]
    days_values = [d for d in group["days"] if d is not None]
    return {
        "society_display": group["display_names"].most_common(1)[0][0],
        "supply_depth": len(prices),
        "resale_velocity_days": round(sum(days_values) / len(days_values), 1) if days_values else None,
        "price_consistency_cov": (
            round(statistics.stdev(prices) / statistics.mean(prices), 4) if len(prices) >= 2 else 0.0
        ),
    }


def _rating_weighted_value(mr: MapsResult | None) -> float | None:
    if mr is None or not mr.rating_available or mr.rating is None:
        return None
    return (mr.rating / 5.0) * math.log(1 + (mr.review_count or 0))


def _weighted_fit_score(
    supply_norm: float, velocity_norm: float, consistency_norm: float, rating_norm: float | None
) -> float:
    if rating_norm is None:
        total_w = WEIGHT_SUPPLY + WEIGHT_VELOCITY + WEIGHT_CONSISTENCY
        weighted_sum = (
            supply_norm * WEIGHT_SUPPLY
            + velocity_norm * WEIGHT_VELOCITY
            + consistency_norm * WEIGHT_CONSISTENCY
        ) / total_w
    else:
        weighted_sum = (
            supply_norm * WEIGHT_SUPPLY
            + velocity_norm * WEIGHT_VELOCITY
            + consistency_norm * WEIGHT_CONSISTENCY
            + rating_norm * WEIGHT_RATING
        )
    return round(10 * weighted_sum, 1)


def _link_absentee_candidates(
    conn: sqlite3.Connection, city_id: str
) -> dict[tuple[str, str], list[int]]:
    """Track-1 link (step 7): candidates are absentee-likelihood proxies,
    staleness-driven - NOT confirmed NRI/identity. Computed live via the
    same validated signal function Track 1 ships with, never re-derived."""
    candidates_by_key: dict[tuple[str, str], list[int]] = {}
    for cand in find_validated_candidates(conn, city_id):
        if not cand.society:
            continue
        key = (cand.corridor, normalize_society_name(cand.society))
        candidates_by_key.setdefault(key, []).append(cand.listing_id)
    return candidates_by_key


def _write_society_meta(conn: sqlite3.Connection, results: list[SocietyFitResult]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for r in results:
        conn.execute(
            "INSERT OR REPLACE INTO society_meta ("
            "city_id, corridor, society_normalized, society_display, supply_depth, "
            "resale_velocity_days, price_consistency_cov, rating, review_count, "
            "rating_available, society_fit_score, appears_in_corridors, last_computed"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.city_id, r.corridor, r.society_normalized, r.society_display, r.supply_depth,
                r.resale_velocity_days, r.price_consistency_cov, r.rating, r.review_count,
                int(r.rating_available), r.society_fit_score,
                json.dumps(r.appears_in_corridors), now,
            ),
        )
    conn.commit()


def compute_society_fit(conn: sqlite3.Connection, city: CityConfig) -> CityFitRunResult:
    conn.executescript(_ENSURE_SCHEMA_SQL)
    conn.commit()

    # Clear this city's slice unconditionally before recomputing, on every
    # call path (found as a real bug in the sibling broker_list.py module,
    # 2026-07-06, and fixed here too since the identical risk applies: a
    # society that qualified in a past run but doesn't anymore - e.g. after
    # a dedup/normalization fix narrows the qualifying set - must not linger
    # as a stale row. INSERT OR REPLACE only ever touches rows sharing the
    # new run's primary key, never removes rows the new run doesn't produce.
    conn.execute("DELETE FROM society_meta WHERE city_id = ?", (city.city_id,))
    conn.commit()

    if city.product_price_band_min_inr is None or city.product_price_band_max_inr is None:
        return CityFitRunResult(
            city_id=city.city_id,
            status="skipped_no_price_band",
            message=(
                f"{city.city_name}: no product_price_band configured in "
                f"config/cities/{city.city_id}.py - skipped. Not scored with "
                f"another city's band."
            ),
        )

    price_min = city.product_price_band_min_inr
    price_max = city.product_price_band_max_inr

    rows = _canonical_city_rows(conn, city.city_id)
    groups = _group_in_band_listings(rows, price_min, price_max)
    qualifying = {k: g for k, g in groups.items() if len(g["prices"]) >= MIN_LISTINGS}

    if not qualifying:
        return CityFitRunResult(
            city_id=city.city_id,
            status="ok",
            message=f"{city.city_name}: 0 societies qualified (need {MIN_LISTINGS}+ in-band canonical listings).",
        )

    # city-wide: which corridors does each normalized society qualify under (contamination flag, step 8)
    society_to_corridors: dict[str, set[str]] = {}
    for corridor, normalized in qualifying:
        society_to_corridors.setdefault(normalized, set()).add(corridor)

    raw_metrics = {key: _raw_metrics_for(g) for key, g in qualifying.items()}
    keys = list(qualifying.keys())

    # Isolated Google Maps enrichment - may fully degrade to NULL, never raises.
    subjects = [
        MapsLookupSubject(
            corridor=corridor,
            society_normalized=normalized,
            society_display=raw_metrics[(corridor, normalized)]["society_display"],
            city_name=city.city_name,
        )
        for corridor, normalized in keys
    ]
    maps_results = enrich_societies(conn, subjects)

    # --- percentile-rank normalization within the city ---
    supply_ranks = dict(zip(keys, percentile_ranks([raw_metrics[k]["supply_depth"] for k in keys])))

    velocity_known = [k for k in keys if raw_metrics[k]["resale_velocity_days"] is not None]
    velocity_ranks: dict[tuple[str, str], float] = {}
    if velocity_known:
        vranks = percentile_ranks([raw_metrics[k]["resale_velocity_days"] for k in velocity_known])
        for k, rank in zip(velocity_known, vranks):
            velocity_ranks[k] = 1 - rank  # lower days = better

    consistency_ranks_raw = percentile_ranks([raw_metrics[k]["price_consistency_cov"] for k in keys])
    consistency_ranks = {k: 1 - r for k, r in zip(keys, consistency_ranks_raw)}  # lower CoV = better

    rating_weighted = {k: v for k in keys if (v := _rating_weighted_value(maps_results.get(k))) is not None}
    rating_ranks: dict[tuple[str, str], float] = {}
    if rating_weighted:
        rkeys = list(rating_weighted.keys())
        rranks = percentile_ranks([rating_weighted[k] for k in rkeys])
        rating_ranks = dict(zip(rkeys, rranks))

    candidates_by_key = _link_absentee_candidates(conn, city.city_id)

    results: list[SocietyFitResult] = []
    for key in keys:
        corridor, normalized = key
        rm = raw_metrics[key]
        mr = maps_results.get(key)

        supply_norm = supply_ranks[key]
        velocity_norm = velocity_ranks.get(key, 0.5)  # neutral fallback: no parseable posting-age data at all
        consistency_norm = consistency_ranks[key]
        rating_norm = rating_ranks.get(key) if key in rating_weighted else None

        fit_score = _weighted_fit_score(supply_norm, velocity_norm, consistency_norm, rating_norm)

        results.append(
            SocietyFitResult(
                city_id=city.city_id,
                corridor=corridor,
                society_display=rm["society_display"],
                society_normalized=normalized,
                supply_depth=rm["supply_depth"],
                resale_velocity_days=rm["resale_velocity_days"],
                price_consistency_cov=rm["price_consistency_cov"],
                rating=mr.rating if mr else None,
                review_count=mr.review_count if mr else None,
                rating_available=bool(mr and mr.rating_available),
                society_fit_score=fit_score,
                appears_in_corridors=sorted(society_to_corridors[normalized]),
                candidate_listing_ids=candidates_by_key.get(key, []),
            )
        )

    _write_society_meta(conn, results)
    results.sort(key=lambda r: r.society_fit_score, reverse=True)

    return CityFitRunResult(
        city_id=city.city_id,
        status="ok",
        message=f"{city.city_name}: {len(results)} societies qualified.",
        results=results,
    )
