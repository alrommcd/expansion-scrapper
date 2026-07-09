"""
Society detail enrichment (2026-07-06), an ADDITIVE layer on top of the
locked society_meta table (scoring/society_fit.py) - never touches it, never
changes society_fit_score or its 4 metrics. Tries to locate each qualifying
society's official project page and pull whatever is actually published:
unit count, possession status, RERA number, a sales contact, a project
description.

Page discovery reuses the SAME Google Places API key already integrated for
society ratings (scoring/maps_enrichment.py) and now also broker contact
enrichment (scoring/broker_contact_enrichment.py), rather than adding a
second paid search-API dependency the user hasn't chosen/configured. This is
a deliberate scoping-down of "search by name+city+official" to "the
confidently-matched Google Places business listing's website" - Places API
is the legitimate-API path the brief itself names as acceptable, and reusing
one already-integrated key is simpler than introducing a new one without
sign-off. Flagged here as an assumption, not hidden: if a dedicated search
API (Google Custom Search, Bing, SerpAPI) is added later, this module's
`_find_official_url` is the only function that would need to change.

Same confidence gate as broker enrichment (name overlap + locality match
against the Places result) before treating a website as "official" -
otherwise "no confident match", never a guess. The page itself is fetched
ONCE per society (no recursive crawling of the site), cached in
society_detail_enrichment so a re-run never re-fetches a society already
resolved (matched or not) - only a systemic API failure stays uncached, for
a retry next run.

Field extraction from the fetched page is deliberately conservative: RERA
number requires the literal string "RERA" nearby, not just a digit pattern
that happens to look like one (a project's phone number or a random ID could
otherwise false-positive). Sales contact reuses the SAME Places Details
phone number already fetched for the confidence check, rather than
regex-scraping a phone off arbitrary page HTML (more reliable, and it's the
same legitimate business-contact data class already accepted for brokers).
Any field not found stays None / "not found on page" - never invented.
"""

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from scoring.broker_contact_enrichment import _significant_words
from scoring.society_fit_config import MAPS

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
_SYSTEMIC_FAILURE_STATUSES = {"REQUEST_DENIED", "OVER_QUERY_LIMIT", "INVALID_REQUEST", "UNKNOWN_ERROR"}

_ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS society_detail_enrichment (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    society_normalized TEXT NOT NULL,
    society_display TEXT NOT NULL,
    matched INTEGER NOT NULL,
    official_url TEXT,
    unit_count TEXT,
    possession_status TEXT,
    rera_number TEXT,
    sales_contact TEXT,
    project_description TEXT,
    source TEXT,
    confidence_note TEXT NOT NULL,
    looked_up_at TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, society_normalized)
);
"""

_UNIT_COUNT_RE = re.compile(r"\b(\d{1,4})\s*(?:units|apartments|flats)\b", re.IGNORECASE)
_RERA_RE = re.compile(r"\b([A-Z]{1,3}\d{10,13})\b")
_POSSESSION_KEYWORDS = ["ready to move", "under construction", "possession by", "possession in", "ready for possession"]
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL
)


@dataclass
class SocietyLookupSubject:
    city_id: str
    city_name: str
    corridor: str
    society_normalized: str
    society_display: str


@dataclass
class SocietyDetailResult:
    matched: bool
    official_url: str | None
    unit_count: str | None
    possession_status: str | None
    rera_number: str | None
    sales_contact: str | None
    project_description: str | None
    source: str | None
    confidence_note: str


class DetailApiUnavailable(Exception):
    """Systemic Places API failure - never cached, same reasoning as the
    sibling exception in scoring/broker_contact_enrichment.py and
    scoring/maps_enrichment.py."""


def _text_search(query: str, api_key: str) -> dict | None:
    resp = requests.get(
        PLACES_TEXT_SEARCH_URL, params={"query": query, "key": api_key}, timeout=MAPS.request_timeout_seconds
    )
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status in _SYSTEMIC_FAILURE_STATUSES:
        raise DetailApiUnavailable(f"Places Text Search status={status}: {data.get('error_message', '')}")
    if status not in ("OK", "ZERO_RESULTS"):
        raise DetailApiUnavailable(f"Places Text Search unexpected status={status}")
    results = data.get("results") or []
    return results[0] if results else None


def _place_details(place_id: str, api_key: str) -> dict:
    resp = requests.get(
        PLACES_DETAILS_URL,
        params={"place_id": place_id, "fields": "website,formatted_phone_number,formatted_address", "key": api_key},
        timeout=MAPS.request_timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status in _SYSTEMIC_FAILURE_STATUSES:
        raise DetailApiUnavailable(f"Places Details status={status}: {data.get('error_message', '')}")
    if status != "OK":
        raise DetailApiUnavailable(f"Places Details unexpected status={status}")
    return data.get("result") or {}


def _extract_fields(html: str) -> dict[str, str | None]:
    unit_match = _UNIT_COUNT_RE.search(html)
    rera_match = None
    for m in _RERA_RE.finditer(html):
        window = html[max(0, m.start() - 60) : m.end() + 10]
        if "rera" in window.lower():
            rera_match = m.group(1)
            break
    possession = next((kw for kw in _POSSESSION_KEYWORDS if kw in html.lower()), None)

    desc = None
    meta_match = _META_DESC_RE.search(html)
    if meta_match:
        desc = meta_match.group(1).strip()[:300]
    else:
        title_match = _TITLE_RE.search(html)
        if title_match:
            desc = re.sub(r"\s+", " ", title_match.group(1)).strip()[:300]

    return {
        "unit_count": unit_match.group(1) if unit_match else None,
        "possession_status": possession,
        "rera_number": rera_match,
        "project_description": desc,
    }


def _fetch_official_page(url: str) -> dict[str, str | None]:
    try:
        resp = requests.get(url, timeout=MAPS.request_timeout_seconds, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        return {"unit_count": None, "possession_status": None, "rera_number": None, "project_description": f"page fetch failed: {e!r}"}
    return _extract_fields(resp.text)


def _resolve_one(subject: SocietyLookupSubject, api_key: str) -> SocietyDetailResult:
    query = f"{subject.society_display} {subject.corridor} {subject.city_name}"
    top = _text_search(query, api_key)

    if top is None:
        return SocietyDetailResult(False, None, None, None, None, None, None, None, "No Places result for this query")

    candidate_name = top.get("name", "")
    candidate_address = top.get("formatted_address", "")
    name_overlap = _significant_words(subject.society_display) & _significant_words(candidate_name)
    locality_ok = subject.city_name.lower() in candidate_address.lower()

    if not name_overlap or not locality_ok:
        return SocietyDetailResult(
            False, None, None, None, None, None, None, None,
            f"Places result '{candidate_name}' ({candidate_address}) didn't confidently match "
            f"'{subject.society_display}' in {subject.city_name} - name overlap: {sorted(name_overlap)}, "
            f"locality match: {locality_ok}",
        )

    details = _place_details(top["place_id"], api_key)
    website = details.get("website")
    phone = details.get("formatted_phone_number")

    if not website:
        return SocietyDetailResult(
            True, None, None, None, None, phone, None, "Google Places",
            f"Matched '{candidate_name}' via Places but it has no website on file - no page to extract from",
        )

    fields = _fetch_official_page(website)
    return SocietyDetailResult(
        True, website, fields["unit_count"], fields["possession_status"], fields["rera_number"],
        phone, fields["project_description"], "Google Places + official page",
        f"Matched '{candidate_name}', page fetched from {website}",
    )


def _cache_get(conn, city_id: str, corridor: str, society_normalized: str) -> SocietyDetailResult | None:
    row = conn.execute(
        "SELECT matched, official_url, unit_count, possession_status, rera_number, sales_contact, "
        "project_description, source, confidence_note FROM society_detail_enrichment "
        "WHERE city_id = ? AND corridor = ? AND society_normalized = ?",
        (city_id, corridor, society_normalized),
    ).fetchone()
    if row is None:
        return None
    return SocietyDetailResult(bool(row[0]), row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8])


def _cache_set(conn, subject: SocietyLookupSubject, result: SocietyDetailResult) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO society_detail_enrichment ("
        "city_id, corridor, society_normalized, society_display, matched, official_url, unit_count, "
        "possession_status, rera_number, sales_contact, project_description, source, confidence_note, "
        "looked_up_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            subject.city_id, subject.corridor, subject.society_normalized, subject.society_display,
            int(result.matched), result.official_url, result.unit_count, result.possession_status,
            result.rera_number, result.sales_contact, result.project_description, result.source,
            result.confidence_note, datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def enrich_societies_detail(
    conn, subjects: list[SocietyLookupSubject]
) -> dict[tuple[str, str, str], SocietyDetailResult]:
    """Returns {(city_id, corridor, society_normalized): SocietyDetailResult}.
    Never raises - a missing key skips every lookup up front; a per-subject
    systemic failure degrades just that one and continues, uncached."""
    conn.executescript(_ENSURE_SCHEMA_SQL)
    conn.commit()

    load_dotenv()
    api_key = os.getenv(MAPS.api_key_env)
    results: dict[tuple[str, str, str], SocietyDetailResult] = {}

    if not api_key:
        print(
            f"Society detail enrichment SKIPPED for all {len(subjects)} societies - "
            f"{MAPS.api_key_env} not set. Every society shows no enrichment.",
            flush=True,
        )
        for s in subjects:
            results[(s.city_id, s.corridor, s.society_normalized)] = SocietyDetailResult(
                False, None, None, None, None, None, None, None, f"{MAPS.api_key_env} not set, lookup skipped"
            )
        return results

    for s in subjects:
        key = (s.city_id, s.corridor, s.society_normalized)
        cached = _cache_get(conn, s.city_id, s.corridor, s.society_normalized)
        if cached is not None:
            results[key] = cached
            continue

        try:
            result = _resolve_one(s, api_key)
        except Exception as e:
            print(f"Detail lookup unavailable for '{s.society_display}': {e!r} - not cached, will retry next run.", flush=True)
            results[key] = SocietyDetailResult(False, None, None, None, None, None, None, None, f"Lookup failed: {e!r}")
            time.sleep(MAPS.rate_limit_seconds)
            continue

        _cache_set(conn, s, result)
        results[key] = result
        time.sleep(MAPS.rate_limit_seconds)

    return results
