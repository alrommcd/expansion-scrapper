"""Deterministic parsers for MagicBricks' near-structured fields. No LLM
involved here, on purpose (see classify/schema.py docstring)."""

import datetime
import re

_LAC = 100_000
_CR = 10_000_000


def parse_price_inr(price_raw: str | None) -> int | None:
    if not price_raw:
        return None
    m = re.search(r"([\d.]+)\s*(Lac|Cr)", price_raw, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    multiplier = _CR if unit == "cr" else _LAC
    return round(value * multiplier)


def parse_area_sqft(carpet_area_raw: str | None) -> int | None:
    if not carpet_area_raw:
        return None
    m = re.search(r"([\d,]+)\s*sqft", carpet_area_raw, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def parse_bhk(title: str | None) -> int | None:
    if not title:
        return None
    m = re.search(r"(\d+)\s*BHK", title, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


def parse_listing_type(posted_by_raw: str | None) -> str:
    if not posted_by_raw:
        return "unknown"
    prefix = posted_by_raw.split(":", 1)[0].strip().lower()
    if prefix == "owner":
        return "owner"
    if prefix in ("dealer", "agent", "builder"):
        return "agent"
    return "unknown"


def parse_mentions_rera(description: str | None) -> bool:
    if not description:
        return False
    return bool(re.search(r"rera", description, re.IGNORECASE))


def parse_days_since_posted(recency_raw: str | None, today: "datetime.date | None" = None) -> int | None:
    """Parses MagicBricks' 'Posted: Yesterday' / 'Updated today' / 'Updated
    15 hours ago' / 'Updated 3 days ago' style text into a day count.

    Once a listing is old enough, MagicBricks switches to an absolute date
    ("Posted: May 07, '26") instead of a relative one - confirmed by recon
    on deep pagination (2026-07-05, see DECISIONS.md). That's the only way
    to see listing age beyond a few weeks from a single scrape, so it's
    parsed here too."""

    if not recency_raw:
        return None
    normalized = recency_raw.strip().lower()
    if "today" in normalized:
        return 0
    if "yesterday" in normalized:
        return 1
    m = re.search(r"(\d+)\s*hour", normalized)
    if m:
        return 0
    m = re.search(r"(\d+)\s*day", normalized)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*week", normalized)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*month", normalized)
    if m:
        return int(m.group(1)) * 30

    m = re.search(r"([A-Za-z]{3})\s+(\d{1,2}),?\s*'?(\d{2,4})", recency_raw.strip())
    if m:
        try:
            month_str, day_str, year_str = m.groups()
            year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
            posted_date = datetime.datetime.strptime(f"{month_str} {day_str} {year}", "%b %d %Y").date()
            reference = today or datetime.date.today()
            return max((reference - posted_date).days, 0)
        except ValueError:
            return None
    return None


def parse_possession_status(status_raw: str | None) -> str:
    if not status_raw:
        return "unknown"
    normalized = status_raw.strip().lower()
    if "ready" in normalized:
        return "ready_to_move"
    if "under construction" in normalized:
        return "under_construction"
    return "unknown"


# Country codes named explicitly in the 2026-07-04 NRI-signal expansion
# (US/Canada, UK, UAE, Australia, Singapore). Text-only: this checks the
# free text already scraped, it does not fetch a phone number hidden behind
# MagicBricks' "Get Phone No." click-through (declined, see DECISIONS.md).
_INTL_COUNTRY_CODES = r"\+1|\+44|\+971|\+61|\+65"


def parse_international_contact_hint(*texts: str | None) -> bool:
    combined = " ".join(t for t in texts if t)
    if not combined:
        return False
    return bool(re.search(rf"(?:{_INTL_COUNTRY_CODES})[\s-]?\d", combined))
