"""
Resolves each classified listing's free-text society name to one canonical
society_id from the corridor's canonical list (city config). This is the
join key for the whole spine (PRD architecture: society is the spine).

Unmatched listings are logged, not silently dropped (PRD requirement).
Match rate below 80% is a red flag per the verification plan.
"""

import difflib
import re
import sqlite3

FUZZY_MATCH_CUTOFF = 0.85


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


# Trailing generic suffixes MagicBricks society names carry (2026-07-06,
# society_fit layer): "Phase N"/"Phase <roman numeral>", "<letter/number>
# Wing", "CHS", "Society", "Apartment(s)" - stripped one at a time, repeated
# until none match, so a compound tail like "... Phase 1 CHS" reduces fully
# instead of only peeling the outermost layer. Real examples that motivated
# each pattern (config/cities/pune.py canonical_societies): "Pragati
# Apartment", "Vilas Prime Panache C Wing", "High Mount Phase 2", "Kul
# Ecoloch Phase I", "Paramount Madhupushpa Phase 1 CHS".
_SOCIETY_TRAILING_NOISE = [
    re.compile(r"\bco[- ]?op(?:erative)?\s*housing\s*society\b\.?$"),
    re.compile(r"\bchs\b\.?$"),
    re.compile(r"\bsociety\b\.?$"),
    re.compile(r"\bapartments?\b\.?$"),
    re.compile(r"\bphase\s*-?\s*(?:\d+|[ivx]+)\b\.?$"),
    re.compile(r"\b(?:[a-z]|\d+)\s*wing\b\.?$"),
    re.compile(r"\bwing\s*-?\s*(?:[a-z]|\d+)\b\.?$"),
]


def normalize_society_name(name: str) -> str:
    """Grouping key for the society-fit layer: normalize_name() plus
    stripping trailing noise words, so e.g. 'Well Wisher Kiara Terrezo' and
    a hypothetical 'Well Wisher Kiara Terrezo Phase 2' merge into one
    society. Never strips down to an empty string - if a name is nothing
    but noise words, the un-stripped base is kept instead."""
    base = normalize_name(name)
    current = base
    changed = True
    while changed:
        changed = False
        for pattern in _SOCIETY_TRAILING_NOISE:
            reduced = pattern.sub("", current).strip()
            if reduced and reduced != current:
                current = reduced
                changed = True
    return current or base


def seed_societies(
    conn: sqlite3.Connection, city_id: str, corridor: str, canonical_societies: list[str]
) -> dict[str, int]:
    name_to_id: dict[str, int] = {}
    for name in canonical_societies:
        existing = conn.execute(
            "SELECT id FROM societies WHERE city_id = ? AND corridor = ? AND canonical_name = ?",
            (city_id, corridor, name),
        ).fetchone()
        if existing:
            society_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO societies (city_id, corridor, canonical_name) VALUES (?, ?, ?)",
                (city_id, corridor, name),
            )
            society_id = cur.lastrowid
        name_to_id[normalize_name(name)] = society_id
    conn.commit()
    return name_to_id


def resolve_entities(
    conn: sqlite3.Connection, city_id: str, corridor: str, canonical_societies: list[str]
) -> dict:
    name_to_id = seed_societies(conn, city_id, corridor, canonical_societies)

    rows = conn.execute(
        "SELECT cl.id, cl.society_name_as_written FROM classified_listings cl "
        "JOIN raw_listings rl ON cl.raw_listing_id = rl.id "
        "WHERE rl.city_id = ? AND rl.corridor = ? AND cl.society_id IS NULL",
        (city_id, corridor),
    ).fetchall()

    matched = 0
    no_society_name = 0
    unmatched: list[tuple[int, str]] = []

    for row in rows:
        name = row["society_name_as_written"]
        if not name:
            no_society_name += 1
            continue

        key = normalize_name(name)
        society_id = name_to_id.get(key)
        if society_id is None:
            close = difflib.get_close_matches(
                key, name_to_id.keys(), n=1, cutoff=FUZZY_MATCH_CUTOFF
            )
            if close:
                society_id = name_to_id[close[0]]

        if society_id is not None:
            conn.execute(
                "UPDATE classified_listings SET society_id = ? WHERE id = ?",
                (society_id, row["id"]),
            )
            matched += 1
        else:
            unmatched.append((row["id"], name))

    conn.commit()

    named_total = len(rows) - no_society_name
    return {
        "total_listings": len(rows),
        "no_society_name": no_society_name,
        "matched": matched,
        "unmatched": [{"classified_listing_id": rid, "society_name_as_written": n} for rid, n in unmatched],
        "match_rate_of_named": round(matched / named_total, 4) if named_total > 0 else None,
    }
