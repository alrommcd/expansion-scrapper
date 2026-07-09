"""
Cross-corridor listing deduplication. Confirmed need (2026-07-06,
DECISIONS.md): adjacent MagicBricks locality searches can return the same
physical property under both corridor tags - Hadapsar/Magarpatta Road
showed 53.6% overlap (39 duplicate listings in the current 870-row Pune
dataset). Matches on (society, price) as the primary key, confirmed with
description similarity (corridor names stripped first, since template
substitution of the locality name is the only expected difference between
two scrapes of the same physical listing) to guard against coincidental
matches - a large project can have many units at the same price that are
genuinely different apartments, not duplicates.

Duplicates are marked via `duplicate_of_id`, not deleted - which corridors
a property appeared in stays queryable (`SELECT DISTINCT corridor FROM
raw_listings WHERE id = ? OR duplicate_of_id = ?`). Per-corridor scoring
(vacancy, absentee) deliberately keeps counting every corridor a property
was visible in - a broker searching either locality would see the same
listing, so that's still real information for that corridor. Dedup exists
to fix analyses that break under double-counting the SAME property as two
distinct ones, e.g. Signal 1 (multi-property owner).

DESCRIPTION_SIMILARITY_THRESHOLD is a judgment call, not a certainty
(2026-07-06, DECISIONS.md): checked against real confirmed-duplicate pairs
(same address/RERA number/specs, manually verified), similarity ranged
from 0.55 to 1.0 depending on how much MagicBricks' template system
reworded otherwise-identical facts. 0.6 catches most real duplicates
without reaching into territory where two genuinely different units in
the same large project (generic templated text, no shared specifics)
could get falsely merged.

Owner-name fallback (added 2026-07-06, found during the first full-scale
production run): descriptions are sometimes empty for one side of a real
duplicate pair (a scraping gap on MagicBricks' end, not ours), and the
original "never merge on empty text" guard then left genuine duplicates
unmerged - which is worse than a missed merge here, because Signal 1
(multi-property owner) then miscounts the same single listing, appearing
twice under the same owner name, as one owner with two properties. An
exact match on owner name is strong corroborating evidence on top of an
already-matching (society, price, area) signature, so it's accepted as an
alternate confirmation path when description similarity can't be computed.

Clustering, not star-comparison (also found 2026-07-06, same production
run, same underlying bug's second half): a signature group can contain
MORE than one real listing at that exact (society, price, area) - e.g.
two different owners who each listed the identical unit type at the
identical price in a large project. The original code compared every
listing in a group only against the group's first (lowest-id) member, so
if listing #1 was owner X and listings #2/#3 were a genuine duplicate
pair from owner Y, #2 and #3 were each compared only against #1 (no
match, different owner/text) and their mutual match was never checked.
Fixed by greedily clustering within each signature group instead: each
listing joins the first existing cluster it's a confirmed duplicate of, or
starts a new cluster if it doesn't match any - so multiple genuine
sub-clusters within one signature group are each found independently.

Area dropped from the signature key entirely (2026-07-06, found via a
user audit of the full 5-city output): the "None fallback" above only
bridges two listings that BOTH lack a parseable area - it never bridges a
listing with a real area against one without, because they land in
different dict keys ((society, price, 1234) vs (society, price, None))
and are never even placed in the same group to compare. Caught concretely
in Bangalore: id 6122 (carpet_area_raw='3700 sqft') and id 6327
(carpet_area_raw=None) were the same 'Rudrani Aum Apartment' listing at
the same price, same owner, near-identical description, same detail_url -
a duplicate obvious enough that Signal 1 (multi-property owner) was
double-counting it as two properties, but invisible to dedup purely
because area was present on one side and missing on the other. The
signature key is now (society, price) alone; area is no longer a
bucketing criterion at all. This does not loosen what counts as a
confirmed duplicate - _is_confirmed_duplicate still requires description
similarity >= threshold or an exact owner-name match - it only removes a
coincidental reason two genuine duplicates could fail to ever be compared.
"""

import difflib
import json
import sqlite3
from dataclasses import dataclass

from classify.parsing import parse_price_inr
from storage.entity_resolution import normalize_name

DESCRIPTION_SIMILARITY_THRESHOLD = 0.6


@dataclass
class DuplicateGroup:
    canonical_id: int
    duplicate_ids: list[int]
    corridors_seen: list[str]
    similarity_scores: list[float]


def _strip_locality_tokens(text: str, corridors: list[str]) -> str:
    normalized = (text or "").lower()
    for c in corridors:
        normalized = normalized.replace(c.lower(), "")
    return normalized


def _description_similarity(a: str, b: str, corridors: list[str]) -> float:
    # Two empty descriptions look identical to SequenceMatcher (ratio 1.0),
    # but that's an absence of evidence, not a match - never confirm a
    # merge without real text to compare.
    if not a or not b:
        return 0.0
    a_clean = _strip_locality_tokens(a, corridors)
    b_clean = _strip_locality_tokens(b, corridors)
    return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()


def _signature(d: dict) -> tuple | None:
    """(society, price) when both are parseable. Carpet area is
    deliberately NOT part of the key (see module docstring, 2026-07-06) -
    it used to be a third tuple element, but that let two listings of the
    same real duplicate silently land in different buckets whenever only
    one side had a parseable area, so they were never even compared.
    Dropping it only widens who gets COMPARED - _is_confirmed_duplicate
    still requires real evidence (description similarity or exact owner
    match) before merging anything in a bucket."""
    society = d.get("society_name_raw")
    price = parse_price_inr(d.get("price_raw"))
    if not society or price is None:
        return None
    return (normalize_name(society), price)


def _owner_name(d: dict) -> str | None:
    posted_by = d.get("posted_by_raw")
    if not posted_by or ":" not in posted_by:
        return None
    name = posted_by.split(":", 1)[1].strip()
    return normalize_name(name) if name else None


def _is_confirmed_duplicate(a: dict, b: dict, corridors: list[str]) -> tuple[bool, float]:
    sim = _description_similarity(a.get("description_raw"), b.get("description_raw"), corridors)
    if sim >= DESCRIPTION_SIMILARITY_THRESHOLD:
        return True, sim
    owner_a, owner_b = _owner_name(a), _owner_name(b)
    if owner_a and owner_b and owner_a == owner_b:
        return True, sim
    return False, sim


def find_duplicate_groups(
    conn: sqlite3.Connection, city_id: str, all_corridor_names: list[str]
) -> list[DuplicateGroup]:
    rows = conn.execute(
        "SELECT id, raw_text FROM raw_listings WHERE city_id = ? AND duplicate_of_id IS NULL ORDER BY id",
        (city_id,),
    ).fetchall()

    by_signature: dict[tuple, list[tuple[int, dict]]] = {}
    for row_id, raw_text in rows:
        d = json.loads(raw_text)
        sig = _signature(d)
        if sig is None:
            continue
        by_signature.setdefault(sig, []).append((row_id, d))

    groups = []
    for sig, listings in by_signature.items():
        if len(listings) < 2:
            continue

        clusters: list[dict] = []  # each: rep_id, rep_d, duplicate_ids, sims, corridors
        for row_id, d in listings:
            joined = None
            for cluster in clusters:
                confirmed, sim = _is_confirmed_duplicate(cluster["rep_d"], d, all_corridor_names)
                if confirmed:
                    joined = (cluster, sim)
                    break
            if joined is not None:
                cluster, sim = joined
                cluster["duplicate_ids"].append(row_id)
                cluster["sims"].append(round(sim, 4))
                cluster["corridors"].add(d.get("corridor"))
            else:
                clusters.append(
                    {
                        "rep_id": row_id,
                        "rep_d": d,
                        "duplicate_ids": [],
                        "sims": [],
                        "corridors": {d.get("corridor")},
                    }
                )

        for cluster in clusters:
            if cluster["duplicate_ids"]:
                groups.append(
                    DuplicateGroup(
                        canonical_id=cluster["rep_id"],
                        duplicate_ids=cluster["duplicate_ids"],
                        corridors_seen=sorted(c for c in cluster["corridors"] if c),
                        similarity_scores=cluster["sims"],
                    )
                )
    return groups


def apply_dedup(conn: sqlite3.Connection, groups: list[DuplicateGroup]) -> int:
    total_marked = 0
    for group in groups:
        for dup_id in group.duplicate_ids:
            conn.execute(
                "UPDATE raw_listings SET duplicate_of_id = ? WHERE id = ?",
                (group.canonical_id, dup_id),
            )
            total_marked += 1
    conn.commit()
    return total_marked
