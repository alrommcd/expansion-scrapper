"""
Layer 2B: society-level vacancy/staleness mapping (user's 2026-07-05 pivot,
DECISIONS.md). Deliberately reads raw_listings directly and does NOT go
through classify/pipeline.py's Gemini step - listing age, price, and
society name are all near-structured MagicBricks fields, so this whole
layer is deterministic parsing + fuzzy entity resolution, no LLM call.

Output per society: total_listings, stale counts at 60d/90d, average
listing age, vacancy_rate (share of listings stale 90d+), and a heuristic
nri_probability_score combining vacancy_rate and average age. rera_units
is always None in v1 - MahaRERA cross-reference (Layer 2C) is blocked
(network-unreachable from this environment) and paused, see PROGRESS.md.
"""

import difflib
import json
import sqlite3
from dataclasses import dataclass

from classify.parsing import parse_days_since_posted
from scoring.vacancy_config import AVG_AGE_CAP_DAYS, STALE_THRESHOLD_60D, STALE_THRESHOLD_90D
from storage.entity_resolution import FUZZY_MATCH_CUTOFF, normalize_name


@dataclass
class SocietyVacancyResult:
    society_name: str
    total_listings: int
    stale_listings_60d: int
    stale_listings_90d: int
    avg_days_since_posted: float
    vacancy_rate_90d: float
    rera_units: int | None
    nri_probability_score: float  # heuristic, 0-1, see module docstring
    sample_confidence: str  # 'low' (<3 listings) | 'medium' (3-9) | 'high' (10+) - a rate computed off 1 listing is noise, not a rank


def _sample_confidence(n: int) -> str:
    if n < 3:
        return "low"
    if n < 10:
        return "medium"
    return "high"


def _match_society(society_name_raw: str | None, canonical_lookup: dict[str, str]) -> str | None:
    if not society_name_raw:
        return None
    key = normalize_name(society_name_raw)
    if key in canonical_lookup:
        return canonical_lookup[key]
    close = difflib.get_close_matches(key, canonical_lookup.keys(), n=1, cutoff=FUZZY_MATCH_CUTOFF)
    return canonical_lookup[close[0]] if close else None


def score_vacancy(
    conn: sqlite3.Connection, city_id: str, corridor: str, canonical_societies: list[str]
) -> list[SocietyVacancyResult]:
    canonical_lookup = {normalize_name(name): name for name in canonical_societies}

    rows = conn.execute(
        "SELECT raw_text FROM raw_listings WHERE city_id = ? AND corridor = ?",
        (city_id, corridor),
    ).fetchall()

    by_society: dict[str, list[int]] = {}
    for (raw_text,) in rows:
        d = json.loads(raw_text)
        canonical = _match_society(d.get("society_name_raw"), canonical_lookup)
        if canonical is None:
            continue
        days = parse_days_since_posted(d.get("posted_recency_raw"))
        if days is None:
            continue
        by_society.setdefault(canonical, []).append(days)

    results = []
    for society_name, ages in by_society.items():
        n = len(ages)
        stale_60d = sum(1 for a in ages if a >= STALE_THRESHOLD_60D)
        stale_90d = sum(1 for a in ages if a >= STALE_THRESHOLD_90D)
        avg_age = sum(ages) / n
        vacancy_rate_90d = stale_90d / n

        avg_age_score = min(avg_age / AVG_AGE_CAP_DAYS, 1.0)
        nri_probability_score = round((vacancy_rate_90d + avg_age_score) / 2, 4)

        results.append(
            SocietyVacancyResult(
                society_name=society_name,
                total_listings=n,
                stale_listings_60d=stale_60d,
                stale_listings_90d=stale_90d,
                avg_days_since_posted=round(avg_age, 1),
                vacancy_rate_90d=round(vacancy_rate_90d, 4),
                rera_units=None,  # Layer 2C blocked/paused, see PROGRESS.md
                nri_probability_score=nri_probability_score,
                sample_confidence=_sample_confidence(n),
            )
        )

    return sorted(results, key=lambda r: r.nri_probability_score, reverse=True)
