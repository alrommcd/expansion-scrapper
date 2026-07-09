"""
CLI entry point. v1 command:

    python cli.py corridors --city pune

Prints the ranked corridor list (JSON) for the given city, using the
city-agnostic engine in scoring/corridor.py against that city's config.
"""

import argparse
import dataclasses
import json
import sys

from classify.pipeline import run_classification
from config.cities import get_city_config
from pipeline import build_plan
from scoring.absentee import score_listing_leads
from scoring.broker_list import compute_broker_list
from scoring.corridor import rank_corridors
from scoring.society_fit import compute_society_fit
from scoring.vacancy import score_vacancy
from scraper.corridor_discovery import discover_corridors
from scraper.magicbricks import scrape_corridor
from storage.db import get_connection, init_db, insert_raw_listing
from storage.entity_resolution import resolve_entities


def _get_corridor_candidate(city_id: str, corridor: str):
    city = get_city_config(city_id)
    candidate = next((c for c in city.corridor_candidates if c.name == corridor), None)
    if candidate is None:
        raise ValueError(f"Corridor '{corridor}' not found in {city_id} config")
    return candidate


def run_corridors(city_id: str) -> dict:
    city = get_city_config(city_id)
    results = rank_corridors(city.corridor_candidates)
    return {
        "city": city.city_name,
        "corridors": [
            {
                "name": r.name,
                "eligible": r.eligible,
                "composite_score": r.composite_score,
                "sub_scores": r.sub_scores,
                "failed_gates": r.failed_gates,
            }
            for r in results
        ],
    }


def run_scrape(city_id: str, corridor: str, max_listings: int, pages: int) -> dict:
    listings = scrape_corridor(
        city_slug=city_id, corridor=corridor, max_listings=max_listings, pages=pages
    )

    init_db()
    conn = get_connection()
    inserted_ids = []
    for listing in listings:
        raw_text = json.dumps(dataclasses.asdict(listing), ensure_ascii=False)
        row_id = insert_raw_listing(
            conn,
            city_id=city_id,
            corridor=corridor,
            source=listing.source,
            raw_text=raw_text,
            price_raw=listing.price_raw,
        )
        inserted_ids.append(row_id)
    conn.commit()
    conn.close()

    return {
        "city": city_id,
        "corridor": corridor,
        "scraped_count": len(listings),
        "inserted_row_ids": inserted_ids,
    }


def run_classify(city_id: str, corridor: str) -> dict:
    conn = get_connection()
    count = run_classification(conn, city_id, corridor)
    conn.close()
    return {"city": city_id, "corridor": corridor, "newly_classified": count}


def run_resolve(city_id: str, corridor: str) -> dict:
    candidate = _get_corridor_candidate(city_id, corridor)
    conn = get_connection()
    result = resolve_entities(conn, city_id, corridor, candidate.canonical_societies)
    conn.close()
    return {"city": city_id, "corridor": corridor, **result}


def _print_society_table(city_name: str, corridor: str, rows: list) -> None:
    print(f"\n{city_name} / {corridor} ({len(rows)} societies)")
    print(f"{'society':40}  {'fit':>5}  {'supply':>6}  {'velocity_d':>10}  {'cov':>6}  {'rating':>12}  {'candidates':>10}")
    for r in rows:
        rating_str = f"{r.rating:.1f} ({r.review_count})" if r.rating_available else "N/A"
        velocity_str = f"{r.resale_velocity_days:.1f}" if r.resale_velocity_days is not None else "N/A"
        contamination = "  *" if len(r.appears_in_corridors) > 1 else ""
        print(
            f"{r.society_display[:40]:40}  {r.society_fit_score:>5.1f}  {r.supply_depth:>6}  "
            f"{velocity_str:>10}  {r.price_consistency_cov:>6.3f}  {rating_str:>12}  "
            f"{r.candidate_count:>10}{contamination}"
        )
    print(
        "(candidate counts are an absentee-likelihood proxy, staleness-driven - not confirmed NRI/identity. "
        "* = society appears in 2+ corridors in this city, treat comps with caution)"
    )


def run_societies(city_id: str, corridor: str | None) -> None:
    """Society-level product-fit layer (rung 3). Distinct score from
    corridor fit_score and absentee_score - see scoring/society_fit.py."""
    city = get_city_config(city_id)
    conn = get_connection()
    run_result = compute_society_fit(conn, city)
    conn.close()

    if run_result.status == "skipped_no_price_band":
        print(run_result.message)
        return

    if not run_result.results:
        print(run_result.message)
        return

    if corridor:
        rows = [r for r in run_result.results if r.corridor == corridor]
        if not rows:
            print(f"{city.city_name} / {corridor}: 0 qualifying societies.")
            return
        _print_society_table(city.city_name, corridor, rows)
        return

    # No --corridor given: show every corridor that passed the 5-gate
    # corridor engine (rung 2), in its ranked order - the corridors HouseEazy
    # would actually drill into next.
    corridor_results = rank_corridors(city.corridor_candidates)
    eligible_names = [r.name for r in corridor_results if r.eligible]
    if not eligible_names:
        print(f"{city.city_name}: no corridors are eligible (all failed at least one gate) - nothing to show.")
        return

    by_corridor: dict[str, list] = {}
    for r in run_result.results:
        by_corridor.setdefault(r.corridor, []).append(r)

    for corridor_name in eligible_names:
        rows = by_corridor.get(corridor_name, [])
        if not rows:
            print(f"\n{city.city_name} / {corridor_name}: 0 qualifying societies.")
            continue
        _print_society_table(city.city_name, corridor_name, rows)


def _print_broker_table(city_name: str, corridor: str, rows: list) -> None:
    print(f"\n{city_name} / {corridor} ({len(rows)} brokers)")
    print(f"{'agent':40}  {'company':25}  {'phone':15}  {'listings':>8}  {'score':>5}")
    for r in rows:
        print(
            f"{r.agent_display[:40]:40}  {(r.company or 'N/A')[:25]:25}  "
            f"{(r.phone or 'N/A'):15}  {r.listing_count:>8}  {r.broker_activity_score:>5.1f}"
        )
    print("(phone/company are NULL by design - MagicBricks gates phone behind a click-through and does not expose a separate company field, see scoring/broker_list.py)")


def run_brokers(city_id: str, corridor: str | None) -> None:
    """Broker-list layer (rung 3b): agents/brokers active in a corridor.
    Straight extraction+count, distinct from fit_score/absentee_score/
    society_fit_score - see scoring/broker_list.py."""
    city = get_city_config(city_id)
    conn = get_connection()
    run_result = compute_broker_list(conn, city)
    conn.close()

    if run_result.status == "no_data" or not run_result.results:
        print(run_result.message)
        return

    if corridor:
        rows = [r for r in run_result.results if r.corridor == corridor]
        if not rows:
            print(f"{city.city_name} / {corridor}: 0 brokers found.")
            return
        _print_broker_table(city.city_name, corridor, rows)
        return

    by_corridor: dict[str, list] = {}
    for r in run_result.results:
        by_corridor.setdefault(r.corridor, []).append(r)

    for corridor_name in sorted(by_corridor):
        _print_broker_table(city.city_name, corridor_name, by_corridor[corridor_name])


def run_leads(city_id: str, corridor: str) -> dict:
    candidate = _get_corridor_candidate(city_id, corridor)
    conn = get_connection()
    leads = score_listing_leads(conn, city_id, corridor, candidate.nri_heavy_societies)
    conn.close()
    leads_sorted = sorted(leads, key=lambda lead: lead.score, reverse=True)
    return {
        "city": city_id,
        "corridor": corridor,
        "leads": [
            {
                "classified_listing_id": lead.classified_listing_id,
                "society_name": lead.society_name,
                "score": lead.score,
                "tier": lead.tier,
                "tier_label": lead.tier_label,
                "matched_signals": lead.matched_signals,
            }
            for lead in leads_sorted
        ],
    }


def run_discover(city_id: str) -> dict:
    corridors, source = discover_corridors(city_id)

    configured_names = set()
    try:
        city = get_city_config(city_id)
        configured_names = {c.name for c in city.corridor_candidates}
    except ValueError:
        pass  # city has a seed corridor list but no CorridorCandidate config yet

    return {
        "city": city_id,
        "source": source,
        "corridors": corridors,
        "scoreable_now": [c for c in corridors if c in configured_names],
        "not_yet_scoreable": [c for c in corridors if c not in configured_names],
    }


def run_vacancy(city_id: str, corridor: str) -> dict:
    candidate = _get_corridor_candidate(city_id, corridor)
    conn = get_connection()
    results = score_vacancy(conn, city_id, corridor, candidate.canonical_societies)
    conn.close()
    return {
        "city": city_id,
        "corridor": corridor,
        "societies": [
            {
                "society_name": r.society_name,
                "total_listings": r.total_listings,
                "stale_listings_60d": r.stale_listings_60d,
                "stale_listings_90d": r.stale_listings_90d,
                "avg_days_since_posted": r.avg_days_since_posted,
                "vacancy_rate_90d": r.vacancy_rate_90d,
                "rera_units": r.rera_units,
                "nri_probability_score": r.nri_probability_score,
                "sample_confidence": r.sample_confidence,
            }
            for r in results
        ],
    }


def print_dry_run(city_id: str) -> None:
    result = build_plan(city_id)
    print(f"CITY: {result['city_name']}")
    print(f"Corridors loaded: {len(result['plan'])}")
    for item in result["plan"]:
        flag = "" if item.scoreable_now else "  [NOT YET SCOREABLE - no CorridorCandidate config]"
        print(f"  - {item.corridor}{flag}")
    if result["plan"]:
        sample = result["plan"][0]
        print(f"Sample generated URL: {sample.sample_url}")
    print(f"Corridor discovery source: {result['discovery_source']}")
    print(f"Config source: {result['config_source']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="HouseEazy expansion intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    corridors_parser = subparsers.add_parser("corridors", help="Rank corridors for a city")
    corridors_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")

    discover_parser = subparsers.add_parser("discover", help="Discover corridor names for a city")
    discover_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape listings for one corridor")
    scrape_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    scrape_parser.add_argument("--corridor", required=True, help="Corridor name, e.g. 'Hinjewadi'")
    scrape_parser.add_argument("--max", type=int, default=30, help="Max listings to scrape")
    scrape_parser.add_argument("--pages", type=int, default=1, help="Number of result pages to scrape (~30 listings/page)")

    classify_parser = subparsers.add_parser("classify", help="Classify scraped listings for one corridor")
    classify_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    classify_parser.add_argument("--corridor", required=True, help="Corridor name, e.g. 'Hinjewadi'")

    resolve_parser = subparsers.add_parser("resolve", help="Resolve listings to canonical societies")
    resolve_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    resolve_parser.add_argument("--corridor", required=True, help="Corridor name, e.g. 'Hinjewadi'")

    societies_parser = subparsers.add_parser(
        "societies", help="Society-level product-fit ranking (rung 3: city -> corridor -> society)"
    )
    societies_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    societies_parser.add_argument(
        "--corridor", required=False, default=None,
        help="Corridor name, e.g. 'Hinjewadi'. Omit to show every eligible corridor in the city.",
    )

    brokers_parser = subparsers.add_parser(
        "brokers", help="Broker-list ranking (rung 3b: agents/brokers active in a corridor)"
    )
    brokers_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    brokers_parser.add_argument(
        "--corridor", required=False, default=None,
        help="Corridor name, e.g. 'Hinjewadi'. Omit to show every corridor with broker data.",
    )

    leads_parser = subparsers.add_parser("leads", help="Per-listing NRI lead scores")
    leads_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    leads_parser.add_argument("--corridor", required=True, help="Corridor name, e.g. 'Hinjewadi'")

    vacancy_parser = subparsers.add_parser("vacancy", help="Layer 2B: society vacancy/staleness map")
    vacancy_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    vacancy_parser.add_argument("--corridor", required=True, help="Corridor name, e.g. 'Hinjewadi'")

    run_parser = subparsers.add_parser("run", help="Full city pipeline: discover, scrape, score all corridors")
    run_parser.add_argument("--city", required=True, help="City id, e.g. 'pune'")
    run_parser.add_argument("--dry-run", action="store_true", help="Show the plan only, scrape/touch nothing")

    args = parser.parse_args()

    if args.command == "corridors":
        try:
            output = run_corridors(args.city)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(output, indent=2))
    elif args.command == "discover":
        try:
            output = run_discover(args.city)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(output, indent=2))
    elif args.command == "scrape":
        output = run_scrape(args.city, args.corridor, args.max, args.pages)
        print(json.dumps(output, indent=2))
    elif args.command == "classify":
        output = run_classify(args.city, args.corridor)
        print(json.dumps(output, indent=2))
    elif args.command == "resolve":
        try:
            output = run_resolve(args.city, args.corridor)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(output, indent=2))
    elif args.command == "societies":
        try:
            run_societies(args.city, args.corridor)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "brokers":
        try:
            run_brokers(args.city, args.corridor)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "leads":
        try:
            output = run_leads(args.city, args.corridor)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    elif args.command == "vacancy":
        try:
            output = run_vacancy(args.city, args.corridor)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    elif args.command == "run":
        if args.dry_run:
            try:
                print_dry_run(args.city)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("Error: 'run' without --dry-run is not implemented yet (Part 3, pending go-ahead).", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
