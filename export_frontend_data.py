"""
UI DATA EXPORT (2026-07-06, presentation layer only). Materializes static
JSON files for the web/ SPA to fetch client-side - this is the ONLY place
that bridges the Python engine to the frontend. It calls existing, already-
shipped functions (rank_corridors, _canonical_city_rows) and reads existing
tables/CSVs; it does not compute, redefine, or alter any of the four scores.
Re-run this after any pipeline re-run to refresh the UI's data.

sample_detail_url (see _exclusive_sample_urls) is the one field computed
fresh here rather than passed through - it's UI traceability metadata, not
a score, and needs a stricter guarantee (a URL exclusive to one poster
city-wide) than scoring/broker_list.py's own grouping provides, since that
grouping was built for counting listings, not for "can a human click this
and visually confirm who posted it."

Why a Python export step instead of a live backend: corridor fit_score has
never been persisted anywhere (scoring/corridor.py computes it on demand
from CityConfig seed data) - a browser can't call rank_corridors() directly,
and running a live API server is more than "no new backend required for a
demo" calls for. This script writes plain JSON once; the SPA is fully
static afterward.

Usage: python export_frontend_data.py
"""

import csv
import json
import os

from classify.parsing import parse_listing_type
from config.cities import CITIES
from scoring.broker_list import _BROKER_PLACEHOLDER_NAMES, _canonical_city_rows
from scoring.corridor import rank_corridors
from scoring.society_fit import _JUNK_SOCIETY_NAMES
from storage.db import get_connection
from storage.entity_resolution import normalize_name, normalize_society_name

OUT_DIR = os.path.join("web", "public", "data")


def _read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def export_cities() -> list[dict]:
    return [
        {
            "city_id": city_id,
            "city_name": city.city_name,
            "state": city.state,
            "corridor_count": len(city.corridor_candidates),
            "has_price_band": city.product_price_band_min_inr is not None
            and city.product_price_band_max_inr is not None,
        }
        for city_id, city in CITIES.items()
    ]


def export_corridors() -> list[dict]:
    rows = []
    for city_id, city in CITIES.items():
        candidates_by_name = {c.name: c for c in city.corridor_candidates}
        for r in rank_corridors(city.corridor_candidates):
            raw = candidates_by_name[r.name]
            rows.append(
                {
                    "city_id": city_id,
                    "corridor": r.name,
                    "eligible": r.eligible,
                    "failed_gates": r.failed_gates,
                    # display-scaled 0-10, same underlying 0-1 composite_score
                    # from scoring/corridor.py - not recomputed, just scaled
                    "fit_score": round(r.composite_score * 10, 1) if r.composite_score is not None else None,
                    "sub_scores": r.sub_scores,
                    # Raw gate inputs (2026-07-09), UI explanation-panel
                    # traceability only - not part of scoring, not recomputed,
                    # straight from the same CorridorCandidate rank_corridors()
                    # already consumed above. sub_scores.product_in_band and
                    # .clean_title ARE already these same two percentages;
                    # the other three sub_scores are normalized/capped
                    # transforms of these raw values (km/count/days), which
                    # is exactly why the raw numbers weren't visible anywhere
                    # in the export before now.
                    "raw_metrics": {
                        "pct_units_in_band": raw.pct_units_in_band,
                        "min_distance_to_demand_anchor_km": raw.min_distance_to_demand_anchor_km,
                        "rera_clean_pct": raw.rera_clean_pct,
                        "comp_count_90d": raw.comp_count_90d,
                        "avg_dom_days": raw.avg_dom_days,
                        "resale_txn_count_90d": raw.resale_txn_count_90d,
                    },
                }
            )
    return rows


def _society_detail_lookup() -> dict[tuple[str, str, str], dict]:
    try:
        rows = _read_csv("output/society_detail_enrichment_all_cities.csv")
    except FileNotFoundError:
        return {}
    return {(r["city_id"], r["corridor"], r["society_normalized"]): r for r in rows}


def _exclusive_society_sample_urls(city_id: str, conn) -> dict[tuple[str, str], str | None]:
    """Society-level counterpart to _exclusive_sample_urls (brokers, below) -
    same "provably belongs to only this one" guarantee, grouped by (corridor,
    society_normalized) instead of (corridor, agent_normalized): a listing's
    detail_url only counts as a sample for a society if no OTHER society's
    listings also resolve to that same URL (the shared-project-overview-page
    risk documented on the broker version applies here identically).

    Deliberately NOT filtered to in-band listings the way scoring/
    society_fit.py's own grouping is - this isn't reproducing the score's
    inputs, it's finding any one real, verifiable example listing for the
    society, and most cities besides Pune have no configured price band at
    all (see CityConfig.product_price_band_min_inr), which would zero out
    coverage everywhere else if required.

    UI traceability only, computed here at export time - does not touch or
    alter scoring/society_fit.py's grouping or scores. Per explicit
    instruction: exactly one representative example, not full coverage -
    the frontend must label this as a sample, not as complete evidence for
    the society's score."""
    rows = _canonical_city_rows(conn, city_id)

    url_societies: dict[str, set[str]] = {}
    society_urls: dict[tuple[str, str], set[str]] = {}

    for corridor, d in rows:
        society_raw = d.get("society_name_raw")
        if not society_raw or society_raw.strip().lower() in _JUNK_SOCIETY_NAMES:
            continue
        normalized = normalize_society_name(society_raw)
        url = d.get("detail_url")
        if not url:
            continue

        url_societies.setdefault(url, set()).add(normalized)
        society_urls.setdefault((corridor, normalized), set()).add(url)

    result: dict[tuple[str, str], str | None] = {}
    for key, urls in society_urls.items():
        exclusive = sorted(u for u in urls if url_societies[u] == {key[1]})
        result[key] = exclusive[0] if exclusive else None
    return result


def export_societies() -> list[dict]:
    """sample_detail_url here is the same UI-traceability-only pattern as
    export_brokers()'s - one verifiable example listing, not the evidentiary
    basis for society_fit_score (which is a multi-listing aggregate, see
    scoring/society_fit.py). The frontend must label it as a sample."""
    rows = _read_csv("output/society_ranking_all_cities.csv")
    detail_by_key = _society_detail_lookup()

    conn = get_connection()
    sample_urls: dict[tuple[str, str, str], str | None] = {}
    for city_id in CITIES:
        for (corridor, society_normalized), url in _exclusive_society_sample_urls(city_id, conn).items():
            sample_urls[(city_id, corridor, society_normalized)] = url
    conn.close()

    out = []
    for r in rows:
        detail = detail_by_key.get((r["city_id"], r["corridor"], r["society_normalized"]))
        matched = bool(detail and detail["matched"] == "1")
        out.append(
            {
                "city_id": r["city_id"],
                "corridor": r["corridor"],
                "society_display": r["society_display"],
                "society_normalized": r["society_normalized"],
                "supply_depth": int(r["supply_depth"]),
                "resale_velocity_days": float(r["resale_velocity_days"]) if r["resale_velocity_days"] else None,
                "price_consistency_cov": float(r["price_consistency_cov"]) if r["price_consistency_cov"] else None,
                "rating": float(r["rating"]) if r["rating"] else None,
                "review_count": int(r["review_count"]) if r["review_count"] else None,
                "rating_available": r["rating_available"] == "1",
                "society_fit_score": float(r["society_fit_score"]) if r["society_fit_score"] else None,
                "appears_in_corridors": r["appears_in_corridors"].split(";") if r["appears_in_corridors"] else [],
                "candidate_count": int(r["candidate_count"]) if r["candidate_count"] else 0,
                "candidate_listing_ids": [
                    int(x) for x in r["candidate_listing_ids"].split(";") if x
                ],
                "sample_detail_url": sample_urls.get(
                    (r["city_id"], r["corridor"], r["society_normalized"])
                ),
                # Detail enrichment (2026-07-06) - additive, degrades to
                # unavailable/None when no confident source was found or
                # GOOGLE_MAPS_API_KEY isn't set. See scoring/society_enrichment.py.
                "detail_available": matched,
                "official_url": (detail or {}).get("official_url") or None,
                "unit_count": (detail or {}).get("unit_count") or None,
                "possession_status": (detail or {}).get("possession_status") or None,
                "rera_number": (detail or {}).get("rera_number") or None,
                "sales_contact": (detail or {}).get("sales_contact") or None,
                "project_description": (detail or {}).get("project_description") or None,
                "detail_source": (detail or {}).get("source") or None,
                "detail_confidence_note": (detail or {}).get("confidence_note") or None,
            }
        )
    return out


def _exclusive_sample_urls(city_id: str, conn) -> dict[tuple[str, str], str | None]:
    """For each (corridor, agent_normalized) in this city, returns a
    detail_url that is BOTH (a) from a canonical row whose own posted_by_raw
    normalizes to that exact agent, AND (b) not shared by any OTHER poster
    anywhere in the city, OWNER OR AGENT - never a "nearby" or
    same-corridor listing.

    (b) matters on top of (a): confirmed empirically (2026-07-06) that large
    projects' detail_url is a shared project-overview page, not a per-unit
    page - e.g. one Gera World of Joy URL in Kharadi is the canonical
    detail_url for FOUR different canonical rows: two owners (Tushar Makkar,
    Tushar Mane) and two agents (Sai Realtors, Vighnaharta Properties). Sai
    Realtors genuinely has an exact posted_by_raw match on that URL - the
    row exists - but the page itself doesn't exclusively belong to Sai
    Realtors, so a human opening it can't confirm Sai Realtors posted it
    from the page alone. Excluding shared URLs entirely, even when the
    requesting agent has a genuine exact-match row, is what makes the "open
    the link and confirm the name" test actually hold up.

    First cut of this function only checked for sharing between AGENTS
    (matching on parse_listing_type == "agent" before ever building the
    exclusivity set) - re-verifying against real data afterward found many
    of the same shared-project-page collisions still slipping through
    specifically when the OTHER poster on a shared URL was an OWNER, not
    another agent (e.g. "Property Bay" the agent and "Shanky" the owner
    both linking to the same page). The page doesn't care about that
    distinction - a human looking at it would still see a name that isn't
    the broker's - so poster identity for exclusivity purposes now spans
    BOTH owner and agent rows, not just agent-vs-agent. Placeholder names
    (PLACEHOLDER_OWNER_NAMES-family) are excluded from counting as a
    "competing" poster, same as elsewhere in this project - they're the
    site's own fallback text, not a real second identity to collide with.

    This is UI-traceability-only, computed here at export time - does not
    touch or alter scoring/broker_list.py's grouping or scores."""
    rows = _canonical_city_rows(conn, city_id)

    # url -> set of distinct normalized poster names referencing it, city-wide,
    # regardless of owner/agent role
    url_posters: dict[str, set[str]] = {}
    # (corridor, agent_normalized) -> set of urls posted by exactly that agent
    agent_urls: dict[tuple[str, str], set[str]] = {}

    for corridor, d in rows:
        posted_by = d.get("posted_by_raw")
        role = parse_listing_type(posted_by)
        if role not in ("owner", "agent"):
            continue
        name = posted_by.split(":", 1)[1].strip() if posted_by and ":" in posted_by else None
        if not name:
            continue
        normalized = normalize_name(name)
        url = d.get("detail_url")
        if not url:
            continue

        # Every distinct posted_by name blocks exclusivity here, including
        # platform placeholders ("Magicbricks User", bare "Real Estate") -
        # deliberately NOT filtered out the way they are for grouping/scoring
        # elsewhere. A placeholder string sharing this URL is still a second
        # name a human would see on the page, so it still breaks the "confirm
        # this exact page belongs to this one broker" guarantee even though
        # it isn't a real competing identity. Only excluded from being a
        # valid CANDIDATE broker below (agent_urls), never from counting
        # against someone else's exclusivity.
        url_posters.setdefault(url, set()).add(normalized)
        if role == "agent" and normalized not in _BROKER_PLACEHOLDER_NAMES:
            agent_urls.setdefault((corridor, normalized), set()).add(url)

    result: dict[tuple[str, str], str | None] = {}
    for key, urls in agent_urls.items():
        exclusive = sorted(u for u in urls if url_posters[u] == {key[1]})
        result[key] = exclusive[0] if exclusive else None
    return result


def _broker_contact_lookup() -> dict[tuple[str, str], dict]:
    try:
        rows = _read_csv("output/broker_contact_enrichment_all_cities.csv")
    except FileNotFoundError:
        return {}
    return {(r["city_id"], r["agent_normalized"]): r for r in rows}


def export_brokers() -> list[dict]:
    """sample_detail_url is UI traceability only, added here at export time -
    it is not part of broker_activity_score and was never in broker_meta or
    the shipped CSV. See _exclusive_sample_urls for why a plain "this agent
    has a row with this URL" check isn't sufficient by itself."""
    csv_rows = {
        (r["city_id"], r["corridor"], r["agent_normalized"]): r
        for r in _read_csv("output/broker_list_all_cities.csv")
    }

    conn = get_connection()
    sample_urls: dict[tuple[str, str, str], str | None] = {}
    for city_id in CITIES:
        for (corridor, agent_normalized), url in _exclusive_sample_urls(city_id, conn).items():
            sample_urls[(city_id, corridor, agent_normalized)] = url
    conn.close()

    contact_by_key = _broker_contact_lookup()

    out = []
    for (city_id, corridor, agent_normalized), r in csv_rows.items():
        contact = contact_by_key.get((city_id, agent_normalized))
        contact_matched = bool(contact and contact["matched"] == "1")
        out.append(
            {
                "city_id": city_id,
                "corridor": corridor,
                "agent_display": r["agent_display"],
                "agent_normalized": agent_normalized,
                "phone": r["phone"] or None,
                "company": r["company"] or None,
                "listing_count": int(r["listing_count"]),
                "broker_activity_score": float(r["broker_activity_score"]),
                "sample_detail_url": sample_urls.get((city_id, corridor, agent_normalized)),
                # Contact enrichment (2026-07-06) - additive, degrades to
                # unavailable/None when no confident source was found or
                # GOOGLE_MAPS_API_KEY isn't set. See
                # scoring/broker_contact_enrichment.py.
                "contact_available": contact_matched,
                "contact_phone": (contact or {}).get("phone") or None,
                "contact_website": (contact or {}).get("website") or None,
                "contact_address": (contact or {}).get("address") or None,
                "contact_source": (contact or {}).get("source") or None,
                "contact_confidence_note": (contact or {}).get("confidence_note") or None,
            }
        )
    return out


def export_absentee_candidates() -> list[dict]:
    rows = _read_csv("output/absentee_candidates_all_cities.csv")
    out = []
    for r in rows:
        out.append(
            {
                "listing_id": int(r["listing_id"]),
                "city_id": r["city_id"],
                "corridor": r["corridor"],
                "society": r["society"] or None,
                "signal_matched": r["signal_matched"],
                "score": r["score"],
                "days_since_posted": int(r["days_since_posted"]) if r["days_since_posted"] else None,
                "detail_url": r["detail_url"] or None,
                "address_recovered": r["address_recovered"] or None,
                "owner_note": r["owner_note"] or None,
                "traceable": bool(r["detail_url"]),
                # What actually produced the match (2026-07-06) - real
                # sibling listing_ids or matched keyword(s), not just the
                # signal label. See scoring/validated_signals.py.
                "evidence": r.get("evidence") or "signal matched, detail not retained",
            }
        )
    return out


def export_nri_directory() -> list[dict]:
    return _read_csv("output/nri_community_directory.csv")


def export_stats(cities, corridors, societies, brokers, candidates, directory) -> dict:
    cities_with_data = {c["city_id"] for c in cities}
    cities_fully_scored = {c["city_id"] for c in cities if c["has_price_band"]}
    return {
        "total_brokers_indexed": len(brokers),
        "total_absentee_candidates": len(candidates),
        "total_cities_live": len(cities_with_data),
        "total_cities_fully_scored": len(cities_fully_scored),
        "total_directory_links": len(directory),
        "total_corridors_ranked": len(corridors),
        "total_societies_scored": len(societies),
        # Enrichment coverage (2026-07-06) - how many resolved confidently,
        # not how many were attempted. 0 here means GOOGLE_MAPS_API_KEY
        # wasn't set for this run, not that the enrichment code is broken.
        "total_brokers_contact_resolved": sum(1 for b in brokers if b["contact_available"]),
        "total_societies_detail_resolved": sum(1 for s in societies if s["detail_available"]),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    cities = export_cities()
    corridors = export_corridors()
    societies = export_societies()
    brokers = export_brokers()
    candidates = export_absentee_candidates()
    directory = export_nri_directory()
    stats = export_stats(cities, corridors, societies, brokers, candidates, directory)

    files = {
        "cities.json": cities,
        "corridors.json": corridors,
        "societies.json": societies,
        "brokers.json": brokers,
        "absentee_candidates.json": candidates,
        "nri_directory.json": directory,
        "stats.json": stats,
    }
    for name, data in files.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"wrote {path} ({len(data) if isinstance(data, list) else 1} {'rows' if isinstance(data, list) else 'object'})")


if __name__ == "__main__":
    main()
