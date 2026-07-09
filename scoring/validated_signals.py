"""
The validated absentee-candidate signal set (2026-07-06, DECISIONS.md),
run identically across every city - this is the "Asset 1" production
pipeline, not a diagnostic. Two signals, both requiring canonical
(deduped) listings:

- Signal 1, multi-property owner (high-confidence slice only): same
  normalized owner name posted 2+ owner-listings, restricted to
  distinctive (2+ word) names. Single-word common first names are
  excluded - verified during diagnosis that these are dominated by
  coincidental name collisions (Sanjay, Akshay, etc), not real repeat
  owners.
- Signal 3, never-occupied (refined keyword set): "never used", "unused",
  "never occupied", "possession not taken" on ready-to-move listings.
  Deliberately drops the bare "brand new" keyword from the original
  5-keyword list - manual verification during diagnosis found "brand new"
  alone was responsible for every false positive found (marketing
  boilerplate: "your brand new home", "brand new electronics"), while
  every confirmed-genuine hit also had one of the four remaining keywords
  co-occurring. This refinement lets the rule run unsupervised at
  production scale without re-introducing that false-positive pattern.

Staleness (90d+) is NOT a qualifying signal here - it's carried as a
supporting/tie-breaker column only, per explicit user instruction. A row
only appears in the output because of Signal 1 or Signal 3.
"""

import json
import sqlite3
from dataclasses import dataclass

from classify.parsing import parse_days_since_posted, parse_listing_type
from storage.entity_resolution import normalize_name

NEVER_OCCUPIED_KEYWORDS = ["never used", "unused", "never occupied", "possession not taken"]

# Not real names - MagicBricks' own placeholder text when it fails to render
# the actual poster's name (2026-07-06, DECISIONS.md: found via a shared-URL
# audit - "Owner: Magicbricks User" / "Owner: MB User" appeared on 5 totally
# unrelated listings across 4 cities, different societies/prices/corridors,
# and both pass the 2+ word distinctiveness filter since they're two-word
# strings. Excluded by exact normalized match, not substring, to avoid
# over-broad filtering of real names.
PLACEHOLDER_OWNER_NAMES = {"mb user", "magicbricks user"}


@dataclass
class SignalRow:
    listing_id: int
    city_id: str
    corridor: str
    society: str
    signal_matched: str  # 'multi_property_owner' | 'never_occupied'
    score: int | str
    days_since_posted: int | None
    detail_url: str | None
    # What actually produced the match, not just the label (2026-07-06,
    # "show the evidence" round) - purely additive, populated from data
    # already computed in-memory during detection below. Never changes
    # which listings qualify or the thresholds that gate them.
    evidence: str = ""


def _canonical_rows(conn: sqlite3.Connection, city_id: str) -> list[tuple[int, str, dict]]:
    rows = conn.execute(
        "SELECT id, corridor, raw_text FROM raw_listings WHERE city_id = ? AND duplicate_of_id IS NULL",
        (city_id,),
    ).fetchall()
    return [(rid, corridor, json.loads(raw)) for rid, corridor, raw in rows]


def find_multi_property_owners(conn: sqlite3.Connection, city_id: str) -> list[SignalRow]:
    rows = _canonical_rows(conn, city_id)

    owner_groups: dict[str, list[tuple[int, str, dict]]] = {}
    for rid, corridor, d in rows:
        posted_by = d.get("posted_by_raw")
        if parse_listing_type(posted_by) != "owner":
            continue
        name = posted_by.split(":", 1)[1].strip() if posted_by and ":" in posted_by else None
        if not name:
            continue
        key = normalize_name(name)
        if key in PLACEHOLDER_OWNER_NAMES:
            continue
        owner_groups.setdefault(key, []).append((rid, corridor, d))

    results = []
    for name_key, listings in owner_groups.items():
        if len(listings) < 2 or len(name_key.split()) < 2:
            continue  # not multi-property, or a single-word name (common-first-name collision risk)
        property_count = len(listings)
        sibling_ids = [rid for rid, _corridor, _d in listings]
        for rid, corridor, d in listings:
            others = [i for i in sibling_ids if i != rid]
            results.append(
                SignalRow(
                    listing_id=rid,
                    city_id=city_id,
                    corridor=corridor,
                    society=d.get("society_name_raw") or "",
                    signal_matched="multi_property_owner",
                    score=property_count,
                    days_since_posted=parse_days_since_posted(d.get("posted_recency_raw")),
                    detail_url=d.get("detail_url"),
                    evidence=(
                        f"Same owner name '{name_key}' also posted on listing(s) "
                        f"{', '.join(f'#{i}' for i in others)}"
                    ),
                )
            )
    return results


def find_never_occupied(conn: sqlite3.Connection, city_id: str) -> list[SignalRow]:
    rows = _canonical_rows(conn, city_id)

    results = []
    for rid, corridor, d in rows:
        status = (d.get("status") or "").lower()
        if "ready" not in status:
            continue
        desc = (d.get("description_raw") or "").lower()
        matched_keywords = [kw for kw in NEVER_OCCUPIED_KEYWORDS if kw in desc]
        if not matched_keywords:
            continue
        results.append(
            SignalRow(
                listing_id=rid,
                city_id=city_id,
                corridor=corridor,
                society=d.get("society_name_raw") or "",
                signal_matched="never_occupied",
                score="confirmed_genuine",
                days_since_posted=parse_days_since_posted(d.get("posted_recency_raw")),
                detail_url=d.get("detail_url"),
                evidence=f"Description matched keyword(s): {', '.join(repr(k) for k in matched_keywords)}",
            )
        )
    return results


def find_validated_candidates(conn: sqlite3.Connection, city_id: str) -> list[SignalRow]:
    return find_multi_property_owners(conn, city_id) + find_never_occupied(conn, city_id)
