"""
Corridor NAME discovery for a city: try NoBroker, fall back to the seeded
config/city_corridors.json. This only discovers corridor *names* - it does
not produce the CorridorCandidate metrics needed for the 5-gate fit score,
which still have to exist in config/cities/<city>.py (see that module's
docstring). A corridor NoBroker returns that isn't already in the Python
config can't be fit-scored yet; that gap is a known limitation, not
silently papered over.

NoBroker is a stub for now (2026-07-05 decision, DECISIONS.md): recon found
its location-autocomplete endpoint (nobroker.in/places/api/v1/autocomplete)
only works when called from within an active browser session - a bare
direct request 500s, it likely needs session cookies/CSRF set up by a real
page visit. A working version would mean driving the actual search UI via
Playwright each time, which is slower and more fragile than a clean API
call. Deferred rather than built now, per user instruction not to let this
block progress - the seed file carries the system either way.
"""

import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "config" / "city_corridors.json"


def discover_corridors_via_nobroker(city_id: str) -> list[str] | None:
    """Always returns None (stub, see module docstring). Must never raise -
    callers always fall back to the seed file on any failure."""
    return None


def _load_seed_corridors(city_id: str) -> list[str]:
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    key = city_id.strip().lower()
    if key not in data:
        available = ", ".join(sorted(data))
        raise ValueError(f"No seeded corridors for city '{city_id}'. Available: {available}")
    return data[key]


def discover_corridors(city_id: str) -> tuple[list[str], str]:
    """Returns (corridor_names, source), source is 'nobroker' or 'seed'."""
    corridors = discover_corridors_via_nobroker(city_id)
    if corridors:
        return corridors, "nobroker"
    return _load_seed_corridors(city_id), "seed"
