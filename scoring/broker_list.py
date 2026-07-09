"""
BROKER-LIST layer (rung 3b: agents/brokers active in a corridor, worth
reaching out to, 2026-07-06). A straight extraction+count - no
signal-discovery judgment, no privacy line (agents publish contact info to
be found, unlike the owner-residence questions this project has repeatedly
declined). broker_activity_score is a fourth, independent number - never
merged with corridor fit_score, absentee_score, or society_fit_score.

Reuses the SAME owner/agent distinction the multi_property_owner signal
relies on (classify/parsing.py's parse_listing_type: 'owner' vs 'agent',
where 'agent' covers dealer/agent/builder prefixes uniformly) rather than
inventing a finer split - brokers here are exactly the rows
parse_listing_type() calls 'agent'. Also reuses PLACEHOLDER_OWNER_NAMES
(scoring/validated_signals.py) since "Magicbricks User"/"MB User" are
generic site placeholders regardless of which prefix they appear under.

phone and company are ALWAYS NULL here, by design, not by omission -
confirmed live (2026-07-06) on real MagicBricks pages before writing any
code:
  - Every agent card shows a "Get Phone No." action button, never a
    rendered number - the same click-through gate already documented for
    owner phone numbers (DECISIONS.md 2026-07-05). No number is present in
    the card HTML, the detail-page body text, or the action-button HTML.
  - posted_by_raw (the only poster-identity field the scraper captures)
    does not separate a person's name from an agency's name into two
    fields - the same text is sometimes clearly a person ("Shubham")
    and sometimes clearly a company ("Dream Home Real Estate
    Consultancy"), with no structural marker distinguishing which. Both
    columns are reserved in broker_meta for if/when a source exposes them
    for real, but nothing is guessed to fill them in now.
No scraper change was needed for this layer: agent identity (posted_by_raw)
was already captured by scraper/magicbricks.py before this task started.

Double-count guard (step 3 of the brief): counts DISTINCT listings by
detail_url within an agent's group, on top of (not instead of) the existing
duplicate_of_id canonical filter - belt-and-suspenders against the same
project-page-URL-sharing trap already found and fixed for Signal 1
(DECISIONS.md 2026-07-06, Hyderabad/Bangalore incidents).
"""

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from classify.parsing import parse_listing_type
from config.city_config import CityConfig
from scoring.stats_utils import percentile_ranks
from scoring.validated_signals import PLACEHOLDER_OWNER_NAMES
from storage.entity_resolution import normalize_name

# Broker-layer-local additions to the shared placeholder set (2026-07-06,
# found during this layer's own dry-run, both confirmed by checking the raw
# rows behind them): bare "Agent: Magicbricks" (3 rows, 2 unrelated
# cities/societies/prices) and bare "Agent: Real Estate" (5 rows, 3 unrelated
# cities/societies/prices) are generic platform/category labels, not real
# one-off agency names - neither is a specific proper noun a real business
# would register under, and both recur across completely unrelated listings.
# Both slip through here in a way they never could for the owner-side
# signal in validated_signals.py, because that signal already requires 2+
# word names (excludes ALL single-word names as a common-first-name-
# collision guard) - "magicbricks" alone is one word and was already
# harmless there, and "real estate" doesn't appear under the Owner: prefix
# at all (checked directly, 0 rows), so it never reached that signal
# either. Brokers have no word-count filter (legitimate agencies commonly
# go by one word, e.g. "Rushub"), so both need their own exclusion here.
# Added locally rather than to PLACEHOLDER_OWNER_NAMES itself, to avoid
# touching the already-shipped, audited Track 1 signal for an issue that
# doesn't affect it.
_BROKER_PLACEHOLDER_NAMES = PLACEHOLDER_OWNER_NAMES | {"magicbricks", "real estate"}

_ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS broker_meta (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    agent_normalized TEXT NOT NULL,
    agent_display TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    listing_count INTEGER NOT NULL,
    broker_activity_score REAL,
    last_computed TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, agent_normalized)
);
"""


@dataclass
class BrokerResult:
    city_id: str
    corridor: str
    agent_display: str
    agent_normalized: str
    phone: str | None
    company: str | None
    listing_count: int
    broker_activity_score: float


@dataclass
class CityBrokerRunResult:
    city_id: str
    status: str  # "ok" | "no_data"
    message: str
    results: list[BrokerResult] = field(default_factory=list)


def _canonical_city_rows(conn: sqlite3.Connection, city_id: str) -> list[tuple[str, dict]]:
    rows = conn.execute(
        "SELECT corridor, raw_text FROM raw_listings WHERE city_id = ? AND duplicate_of_id IS NULL",
        (city_id,),
    ).fetchall()
    return [(corridor, json.loads(raw)) for corridor, raw in rows]


def _group_brokers(rows: list[tuple[str, dict]]) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = {}
    for corridor, d in rows:
        posted_by = d.get("posted_by_raw")
        if parse_listing_type(posted_by) != "agent":
            continue
        name = posted_by.split(":", 1)[1].strip() if posted_by and ":" in posted_by else None
        if not name:
            continue
        normalized = normalize_name(name)
        if normalized in _BROKER_PLACEHOLDER_NAMES:
            continue

        key = (corridor, normalized)
        group = groups.setdefault(key, {"display_names": Counter(), "urls": set(), "no_url_count": 0})
        group["display_names"][name] += 1
        detail_url = d.get("detail_url")
        if detail_url:
            group["urls"].add(detail_url)
        else:
            group["no_url_count"] += 1
    return groups


def compute_broker_list(conn: sqlite3.Connection, city: CityConfig) -> CityBrokerRunResult:
    conn.executescript(_ENSURE_SCHEMA_SQL)
    conn.commit()

    # Clear this city's slice unconditionally before recomputing, on every
    # call path - a broker/name that qualified in a past run (e.g. before a
    # placeholder exclusion existed) but doesn't qualify anymore, or a city
    # that used to have data and legitimately has none now, must not leave
    # stale rows behind. INSERT-only (upsert) can never express "this row
    # shouldn't exist anymore," only "update/add this row."
    conn.execute("DELETE FROM broker_meta WHERE city_id = ?", (city.city_id,))
    conn.commit()

    rows = _canonical_city_rows(conn, city.city_id)
    if not rows:
        return CityBrokerRunResult(
            city_id=city.city_id,
            status="no_data",
            message=f"{city.city_name}: no scraped listings for this city yet.",
        )

    groups = _group_brokers(rows)
    if not groups:
        return CityBrokerRunResult(
            city_id=city.city_id,
            status="ok",
            message=f"{city.city_name}: 0 brokers found (no agent/dealer/builder-posted listings).",
        )

    listing_counts: dict[tuple[str, str], int] = {}
    display_names: dict[tuple[str, str], str] = {}
    for key, g in groups.items():
        # Distinct-by-detail_url, plus one for each row that never had a
        # capturable URL (a separate, pre-existing gap - can't be
        # deduped further without a URL to compare, but also isn't
        # double-counted, since each such row is still one distinct scrape).
        listing_counts[key] = len(g["urls"]) + g["no_url_count"]
        display_names[key] = g["display_names"].most_common(1)[0][0]

    keys = list(groups.keys())
    scores = dict(
        zip(keys, (round(10 * r, 1) for r in percentile_ranks([listing_counts[k] for k in keys])))
    )

    results = [
        BrokerResult(
            city_id=city.city_id,
            corridor=corridor,
            agent_display=display_names[(corridor, normalized)],
            agent_normalized=normalized,
            phone=None,    # always NULL - see module docstring
            company=None,  # always NULL - see module docstring
            listing_count=listing_counts[(corridor, normalized)],
            broker_activity_score=scores[(corridor, normalized)],
        )
        for corridor, normalized in keys
    ]

    _write_broker_meta(conn, results)
    results.sort(key=lambda r: r.broker_activity_score, reverse=True)

    return CityBrokerRunResult(
        city_id=city.city_id,
        status="ok",
        message=f"{city.city_name}: {len(results)} brokers found.",
        results=results,
    )


def _write_broker_meta(conn: sqlite3.Connection, results: list[BrokerResult]) -> None:
    """Inserts this run's rows. The corresponding DELETE for this city
    already happened unconditionally at the top of compute_broker_list, on
    every call path (including the early-return "no brokers found" cases) -
    see that function's comment for why an upsert-only write isn't enough."""
    now = datetime.now(timezone.utc).isoformat()
    for r in results:
        conn.execute(
            "INSERT INTO broker_meta ("
            "city_id, corridor, agent_normalized, agent_display, phone, company, "
            "listing_count, broker_activity_score, last_computed"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.city_id, r.corridor, r.agent_normalized, r.agent_display, r.phone, r.company,
                r.listing_count, r.broker_activity_score, now,
            ),
        )
    conn.commit()
