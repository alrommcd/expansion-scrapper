"""
Isolated Google Maps enrichment step (2026-07-06) for the society-fit layer.
Physically separate from scoring/society_fit.py on purpose: the three
deterministic metrics (supply, velocity, consistency) must be fully
computable with zero network calls, so a missing API key, a Maps outage, or
a quota error can never take the whole run down - this module is called
AFTER those metrics exist and only adds rating/review_count on top, one
society at a time, degrading any individual failure to "unavailable"
without touching the rows already resolved.

Uses the Places API Text Search endpoint (a REST call, not an LLM - this is
still the "no Gemini" deterministic-metrics constraint's sibling, not an
exception to it, since scoring itself never touches this data by inventing
values; it only ever plugs in whatever Google's API actually returned or
NULL).

Cached in the maps_cache table (storage/schema.sql), keyed on the exact
query string sent to the API, so re-runs never re-hit it for a query
already resolved (matched or not).
"""

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from scoring.society_fit_config import MAPS

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


@dataclass
class MapsLookupSubject:
    corridor: str
    society_normalized: str
    society_display: str
    city_name: str


@dataclass
class MapsResult:
    rating: float | None
    review_count: int | None
    rating_available: bool


def _cache_get(conn, query: str) -> dict | None:
    row = conn.execute(
        "SELECT matched, rating, review_count FROM maps_cache WHERE query = ?", (query,)
    ).fetchone()
    if row is None:
        return None
    return {"matched": bool(row[0]), "rating": row[1], "review_count": row[2]}


def _cache_set(conn, query: str, matched: bool, rating: float | None, review_count: int | None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO maps_cache (query, matched, rating, review_count, looked_up_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (query, int(matched), rating, review_count, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


class MapsApiUnavailable(Exception):
    """Raised for systemic failures (bad/rejected key, quota exceeded,
    malformed request, Google-side error) - deliberately distinct from a
    genuine zero-result match. The caller must NOT cache these: caching a
    systemic failure as "no match" would permanently poison that query even
    after the underlying cause (e.g. a missing key) is fixed."""


# Places API statuses that mean "the API itself couldn't serve this
# request" as opposed to "the API worked and found nothing."
_SYSTEMIC_FAILURE_STATUSES = {"REQUEST_DENIED", "OVER_QUERY_LIMIT", "INVALID_REQUEST", "UNKNOWN_ERROR"}


def _query_places_api(query: str, api_key: str) -> tuple[float | None, int | None]:
    """Returns (rating, review_count), both None for a genuine zero-result
    match. Raises MapsApiUnavailable for systemic failures - never returns
    (None, None) to mean "the key was rejected", only to mean "the API ran
    fine and there's genuinely no place matching this query"."""
    resp = requests.get(
        PLACES_TEXT_SEARCH_URL,
        params={"query": query, "key": api_key},
        timeout=MAPS.request_timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status in _SYSTEMIC_FAILURE_STATUSES:
        raise MapsApiUnavailable(f"Places API status={status}: {data.get('error_message', '')}")
    if status not in ("OK", "ZERO_RESULTS"):
        raise MapsApiUnavailable(f"Places API unexpected status={status}")
    results = data.get("results") or []
    if not results:
        return None, None
    top = results[0]
    return top.get("rating"), top.get("user_ratings_total")


def enrich_societies(
    conn, subjects: list[MapsLookupSubject]
) -> dict[tuple[str, str], MapsResult]:
    """Returns {(corridor, society_normalized): MapsResult}. Never raises -
    a missing key skips every lookup up front; a per-query failure (network,
    quota, bad response) degrades just that one subject and continues."""

    load_dotenv()
    api_key = os.getenv(MAPS.api_key_env)
    results: dict[tuple[str, str], MapsResult] = {}

    if not api_key:
        print(
            f"Maps enrichment SKIPPED for all {len(subjects)} societies - "
            f"{MAPS.api_key_env} not set. rating=NULL, rating_available=0 for all.",
            flush=True,
        )
        for s in subjects:
            results[(s.corridor, s.society_normalized)] = MapsResult(None, None, False)
        return results

    for s in subjects:
        key = (s.corridor, s.society_normalized)
        query = f"{s.society_display} {s.corridor} {s.city_name}"

        cached = _cache_get(conn, query)
        if cached is not None:
            if cached["matched"]:
                results[key] = MapsResult(cached["rating"], cached["review_count"], True)
            else:
                results[key] = MapsResult(None, None, False)
            continue

        try:
            rating, review_count = _query_places_api(query, api_key)
        except Exception as e:
            # Systemic failure (bad key, quota, network, unexpected status) -
            # deliberately NOT cached, so a later run (e.g. after fixing the
            # key) retries this query instead of staying stuck on today's
            # failure. Only a genuine zero-result match gets cached below.
            print(f"Maps lookup unavailable for '{query}': {e!r} - not cached, will retry next run.", flush=True)
            results[key] = MapsResult(None, None, False)
            time.sleep(MAPS.rate_limit_seconds)
            continue

        matched = rating is not None
        _cache_set(conn, query, matched, rating, review_count)
        results[key] = MapsResult(rating if matched else None, review_count if matched else None, matched)
        time.sleep(MAPS.rate_limit_seconds)

    return results
