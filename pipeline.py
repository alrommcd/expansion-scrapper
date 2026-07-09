"""
City-level orchestration (Phase B): discover corridors for a city, plan or
run the scrape+score loop across all of them. This is the city-agnostic
entry point - swapping city_id must change every downstream step
(corridors, URLs, scoring) with zero code edits, only config data.

`build_plan` is read-only (no network, no DB writes) - it's what --dry-run
calls to prove that swapping cities changes everything correctly before
anything gets scraped.
"""

from dataclasses import dataclass

from config.cities import get_city_config
from scraper.corridor_discovery import discover_corridors
from scraper.magicbricks import build_url, slugify


@dataclass
class CorridorPlanItem:
    corridor: str
    scoreable_now: bool  # True if a matching CorridorCandidate exists (needed for Fit Score)
    sample_url: str


def build_plan(city_id: str) -> dict:
    city = get_city_config(city_id)
    corridor_names, discovery_source = discover_corridors(city_id)
    candidates_by_name = {c.name: c for c in city.corridor_candidates}

    plan = [
        CorridorPlanItem(
            corridor=name,
            scoreable_now=name in candidates_by_name,
            sample_url=build_url(slugify(name), city_id, page=1),
        )
        for name in corridor_names
    ]

    return {
        "city_id": city_id,
        "city_name": city.city_name,
        "config_source": f"config/cities/{city_id}.py",
        "discovery_source": discovery_source,
        "plan": plan,
    }
