"""
Society-level absentee/NRI lead scorer (Layer 3, Tier-A only). Tiered
point scoring per the user's 2026-07-04 spec (DECISIONS.md): Tier 1 flags
= 40 pts each, Tier 2 = 20 pts each, Tier 3 = 10 pts each, scored per
listing then aggregated to society level.

This is explicitly a low-confidence heuristic proxy, not a factual claim
about any individual owner (CLAUDE.md kickoff brief compliance note). It is
also never surfaced with named individuals, only an aggregate score per
society (DPDP boundary) - listing-level detail here stays internal to the
CLI/analysis output, matched_brokers in the final joined table carries no
owner names or contact info.

Two Tier 3 signals are computed here rather than in classify/: they are
comparative/config-driven, not intrinsic to one listing in isolation.
- below_market_price: listing price-per-sqft vs the corridor median. User
  override of the "never infer NRI from price" rule (see
  scoring/absentee_config.py docstring for the false-positive risk noted
  at the time).
- nri_heavy_society: matched against an explicit user-curated list (city
  config), never an inferred/guessed list. Empty by default.
"""

import sqlite3
import statistics
from dataclasses import dataclass

from scoring.absentee_config import (
    MAX_POSSIBLE_SCORE,
    TIER1_FLAGS,
    TIER1_POINTS,
    TIER2_FLAGS,
    TIER2_POINTS,
    TIER3_POINTS,
    BELOW_MARKET_RATIO,
    lead_tier,
)
from storage.entity_resolution import normalize_name

ALL_FLAG_COLUMNS = TIER1_FLAGS + TIER2_FLAGS


@dataclass
class ListingLead:
    classified_listing_id: int
    society_id: int
    society_name: str
    score: int
    tier: str
    tier_label: str
    matched_signals: list[str]


@dataclass
class AbsenteeResult:
    society_id: int
    canonical_name: str
    listing_count: int
    avg_score: float
    hot_count: int
    warm_count: int
    cold_count: int
    absentee_density: float  # avg_score normalized 0-1 against MAX_POSSIBLE_SCORE, heuristic


def _corridor_median_price_per_sqft(rows: list[sqlite3.Row]) -> float | None:
    values = [
        r["price_inr"] / r["area_sqft"]
        for r in rows
        if r["price_inr"] and r["area_sqft"]
    ]
    return statistics.median(values) if values else None


def _score_listing(row: sqlite3.Row, is_below_market: bool, is_nri_heavy_society: bool) -> tuple[int, list[str]]:
    matched = []
    score = 0

    for flag in TIER1_FLAGS:
        if row[flag]:
            score += TIER1_POINTS
            matched.append(flag)
    for flag in TIER2_FLAGS:
        if row[flag]:
            score += TIER2_POINTS
            matched.append(flag)
    if is_below_market:
        score += TIER3_POINTS
        matched.append("below_market_price")
    if is_nri_heavy_society:
        score += TIER3_POINTS
        matched.append("nri_heavy_society")

    return score, matched


def score_listing_leads(
    conn: sqlite3.Connection, city_id: str, corridor: str, nri_heavy_societies: list[str] | None = None
) -> list[ListingLead]:
    nri_heavy_normalized = {normalize_name(n) for n in (nri_heavy_societies or [])}

    rows = conn.execute(
        f"SELECT cl.id, cl.society_id, cl.price_inr, cl.area_sqft, {', '.join(ALL_FLAG_COLUMNS)} "
        "FROM classified_listings cl "
        "JOIN raw_listings rl ON cl.raw_listing_id = rl.id "
        "WHERE rl.city_id = ? AND rl.corridor = ? AND cl.society_id IS NOT NULL",
        (city_id, corridor),
    ).fetchall()

    society_names = {
        r["id"]: r["canonical_name"]
        for r in conn.execute(
            "SELECT id, canonical_name FROM societies WHERE city_id = ? AND corridor = ?",
            (city_id, corridor),
        ).fetchall()
    }

    median_pps = _corridor_median_price_per_sqft(rows)

    leads = []
    for row in rows:
        is_below_market = (
            median_pps is not None
            and row["price_inr"]
            and row["area_sqft"]
            and (row["price_inr"] / row["area_sqft"]) < median_pps * BELOW_MARKET_RATIO
        )
        society_name = society_names.get(row["society_id"], "Unknown")
        is_nri_heavy_society = normalize_name(society_name) in nri_heavy_normalized

        score, matched = _score_listing(row, is_below_market, is_nri_heavy_society)
        tier, tier_label = lead_tier(score)

        leads.append(
            ListingLead(
                classified_listing_id=row["id"],
                society_id=row["society_id"],
                society_name=society_name,
                score=score,
                tier=tier,
                tier_label=tier_label,
                matched_signals=matched,
            )
        )

    return leads


def score_absentee_density(
    conn: sqlite3.Connection, city_id: str, corridor: str, nri_heavy_societies: list[str] | None = None
) -> list[AbsenteeResult]:
    leads = score_listing_leads(conn, city_id, corridor, nri_heavy_societies)

    by_society: dict[int, list[ListingLead]] = {}
    for lead in leads:
        by_society.setdefault(lead.society_id, []).append(lead)

    results = []
    for society_id, society_leads in by_society.items():
        scores = [lead.score for lead in society_leads]
        avg_score = round(sum(scores) / len(scores), 2)
        results.append(
            AbsenteeResult(
                society_id=society_id,
                canonical_name=society_leads[0].society_name,
                listing_count=len(society_leads),
                avg_score=avg_score,
                hot_count=sum(1 for lead in society_leads if lead.tier == "hot"),
                warm_count=sum(1 for lead in society_leads if lead.tier == "warm"),
                cold_count=sum(1 for lead in society_leads if lead.tier == "cold"),
                absentee_density=round(avg_score / MAX_POSSIBLE_SCORE, 4),
            )
        )

    return sorted(results, key=lambda r: r.avg_score, reverse=True)
