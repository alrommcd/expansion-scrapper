"""
Broker contact enrichment (2026-07-06), an ADDITIVE layer on top of the
locked broker_meta table (scoring/broker_list.py) - never touches it.
broker_meta's phone/company stay NULL by design (MagicBricks itself never
exposes them); this module instead tries to resolve each unique
(city, agent_normalized) pair against a legitimate public business source -
Google's Places API, the same key already used for society ratings
(scoring/maps_enrichment.py) - rather than scraping raw Google search
result pages or a second directory site with no prior reachability recon.

Same isolation and honesty pattern as scoring/maps_enrichment.py, deliberately
copied rather than re-derived: cached, never raises, a missing API key skips
every lookup up front, and a systemic API failure (bad key, quota) is never
cached, only a genuine resolved-or-not result is.

Confidence gate (the "don't guess" rule this project has held to since
sample_detail_url): a Places Text Search hit is only accepted if BOTH (a)
the returned place's name shares a significant word with the broker's
posted name, and (b) the returned address mentions the city. Either check
failing means "unavailable", never a low-confidence guess. Phone/website/
address for an accepted match come from the Place Details endpoint (Text
Search alone doesn't return them) - one extra call per confident candidate
only, not per lookup, to keep the added API cost proportional to actual hits.
"""

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from scoring.society_fit_config import MAPS

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

_SYSTEMIC_FAILURE_STATUSES = {"REQUEST_DENIED", "OVER_QUERY_LIMIT", "INVALID_REQUEST", "UNKNOWN_ERROR"}

_ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS broker_contact_enrichment (
    city_id TEXT NOT NULL,
    agent_normalized TEXT NOT NULL,
    agent_display TEXT NOT NULL,
    matched INTEGER NOT NULL,
    phone TEXT,
    website TEXT,
    address TEXT,
    source TEXT,
    confidence_note TEXT NOT NULL,
    looked_up_at TEXT NOT NULL,
    PRIMARY KEY (city_id, agent_normalized)
);
"""

_STOPWORDS = {"real", "estate", "realty", "realtors", "properties", "property", "consultants", "consultancy", "agency", "group"}


def _significant_words(name: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", name.lower())
    sig = {w for w in words if w not in _STOPWORDS and len(w) > 2}
    return sig or set(words)  # if everything was a stopword, fall back to all words rather than an empty set


@dataclass
class BrokerLookupSubject:
    city_id: str
    city_name: str
    agent_normalized: str
    agent_display: str


@dataclass
class BrokerContactResult:
    matched: bool
    phone: str | None
    website: str | None
    address: str | None
    source: str | None  # e.g. "Google Places"
    confidence_note: str


class ContactApiUnavailable(Exception):
    """Systemic failure (bad/rejected key, quota, malformed request,
    Google-side error) - distinct from a genuine no-match, and never cached,
    for the same reason as scoring/maps_enrichment.py's identical exception:
    caching a systemic failure as "no match" would permanently poison the
    query even after the underlying cause is fixed."""


def _text_search(query: str, api_key: str) -> dict | None:
    """Returns the top result dict (name, formatted_address, place_id), or
    None for a genuine zero-result search. Raises ContactApiUnavailable for
    systemic failures."""
    resp = requests.get(
        PLACES_TEXT_SEARCH_URL, params={"query": query, "key": api_key}, timeout=MAPS.request_timeout_seconds
    )
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status in _SYSTEMIC_FAILURE_STATUSES:
        raise ContactApiUnavailable(f"Places Text Search status={status}: {data.get('error_message', '')}")
    if status not in ("OK", "ZERO_RESULTS"):
        raise ContactApiUnavailable(f"Places Text Search unexpected status={status}")
    results = data.get("results") or []
    return results[0] if results else None


def _place_details(place_id: str, api_key: str) -> dict:
    resp = requests.get(
        PLACES_DETAILS_URL,
        params={
            "place_id": place_id,
            "fields": "formatted_phone_number,website,formatted_address",
            "key": api_key,
        },
        timeout=MAPS.request_timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status in _SYSTEMIC_FAILURE_STATUSES:
        raise ContactApiUnavailable(f"Places Details status={status}: {data.get('error_message', '')}")
    if status != "OK":
        raise ContactApiUnavailable(f"Places Details unexpected status={status}")
    return data.get("result") or {}


def _resolve_one(subject: BrokerLookupSubject, api_key: str) -> BrokerContactResult:
    query = f"{subject.agent_display} real estate {subject.city_name}"
    top = _text_search(query, api_key)

    if top is None:
        return BrokerContactResult(False, None, None, None, None, "No Places result for this query")

    candidate_name = top.get("name", "")
    candidate_address = top.get("formatted_address", "")

    name_overlap = _significant_words(subject.agent_display) & _significant_words(candidate_name)
    locality_ok = subject.city_name.lower() in candidate_address.lower()

    if not name_overlap or not locality_ok:
        return BrokerContactResult(
            False, None, None, None, None,
            f"Places result '{candidate_name}' ({candidate_address}) didn't confidently match "
            f"'{subject.agent_display}' in {subject.city_name} - name overlap: {sorted(name_overlap)}, "
            f"locality match: {locality_ok}",
        )

    details = _place_details(top["place_id"], api_key)
    phone = details.get("formatted_phone_number")
    website = details.get("website")
    address = details.get("formatted_address") or candidate_address
    if not phone and not website:
        return BrokerContactResult(
            True, None, None, address, "Google Places",
            f"Matched '{candidate_name}' but Places had no phone or website on file, address only",
        )
    return BrokerContactResult(
        True, phone, website, address, "Google Places",
        f"Matched '{candidate_name}' - name overlap {sorted(name_overlap)}, locality confirmed",
    )


def _cache_get(conn, city_id: str, agent_normalized: str) -> BrokerContactResult | None:
    row = conn.execute(
        "SELECT matched, phone, website, address, source, confidence_note FROM broker_contact_enrichment "
        "WHERE city_id = ? AND agent_normalized = ?",
        (city_id, agent_normalized),
    ).fetchone()
    if row is None:
        return None
    return BrokerContactResult(bool(row[0]), row[1], row[2], row[3], row[4], row[5])


def _cache_set(conn, subject: BrokerLookupSubject, result: BrokerContactResult) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO broker_contact_enrichment ("
        "city_id, agent_normalized, agent_display, matched, phone, website, address, source, "
        "confidence_note, looked_up_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            subject.city_id, subject.agent_normalized, subject.agent_display, int(result.matched),
            result.phone, result.website, result.address, result.source, result.confidence_note,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def enrich_brokers(conn, subjects: list[BrokerLookupSubject]) -> dict[tuple[str, str], BrokerContactResult]:
    """Returns {(city_id, agent_normalized): BrokerContactResult}. Never
    raises - a missing key skips every lookup up front; a per-subject
    systemic failure degrades just that one and continues, uncached."""
    conn.executescript(_ENSURE_SCHEMA_SQL)
    conn.commit()

    load_dotenv()
    api_key = os.getenv(MAPS.api_key_env)
    results: dict[tuple[str, str], BrokerContactResult] = {}

    if not api_key:
        print(
            f"Broker contact enrichment SKIPPED for all {len(subjects)} brokers - "
            f"{MAPS.api_key_env} not set. Every broker shows unavailable contact info.",
            flush=True,
        )
        for s in subjects:
            results[(s.city_id, s.agent_normalized)] = BrokerContactResult(
                False, None, None, None, None, f"{MAPS.api_key_env} not set, lookup skipped"
            )
        return results

    for s in subjects:
        key = (s.city_id, s.agent_normalized)
        cached = _cache_get(conn, s.city_id, s.agent_normalized)
        if cached is not None:
            results[key] = cached
            continue

        try:
            result = _resolve_one(s, api_key)
        except Exception as e:
            print(f"Contact lookup unavailable for '{s.agent_display}': {e!r} - not cached, will retry next run.", flush=True)
            results[key] = BrokerContactResult(False, None, None, None, None, f"Lookup failed: {e!r}")
            time.sleep(MAPS.rate_limit_seconds)
            continue

        _cache_set(conn, s, result)
        results[key] = result
        time.sleep(MAPS.rate_limit_seconds)

    return results
