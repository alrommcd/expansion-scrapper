"""
MagicBricks listing scraper for one corridor. Verified selectors (recon,
2026-07-03): listing cards are `.mb-srp__card`, ~30 per page, server-rendered
on first load (no bot-block encountered). Structured fields live in
`[data-summary='<key>'] .mb-srp__card__summary--value` pairs; free-text
description lives in `.mb-srp__card--desc--text p`.

Pagination via `?page=N` (confirmed working, recon 2026-07-05, up to at
least page 20). Page 1 alone is all same-day-fresh listings (the only date
sort available is "Most Recent", there's no "oldest first"), so any
listing-age analysis (Layer 2B vacancy mapping) needs several pages, not
just page 1. A short delay between page loads keeps this from hammering
the site (still a "small-scale personal demo" per CLAUDE.md kickoff brief,
just wider than the original single-page samples).

Raw listing text may incidentally include the owner's name (MagicBricks
shows it next to "Contact Owner") - this is stored locally for
classification only. It must never appear in the final society-level
output (DPDP boundary, see PRD compliance note).

Society-name fallback (added 2026-07-06, found during the Hyderabad
production run, DECISIONS.md): Hyderabad's card layout has no
`data-summary='society'` element at all (confirmed live - its cards only
carry carpet-area/status/floor/transaction/furnishing/facing/overlooking/
ownership/parking/bathroom/balcony, never society), so every one of its
1050 scraped listings came back with `society_name_raw=None`. That silently
broke cross-corridor dedup (its signature key requires a society name) and
inflated Signal 1 (multi-property owner), which double-counted the same
undeduped physical listing under two corridor tags as two properties. The
project/society name is reliably present in the detail-page URL slug
instead (e.g. `.../my-home-bhooja-hitech-city-hyderabad-pdpid-...`), so
`_society_from_url` is tried as a fallback whenever the card-summary field
comes back empty. It cannot help the ~21% of rows where the href itself
failed to capture (a pre-existing, separate gap), and it's a heuristic
(strips the known corridor and city slugs off the URL, so a city/corridor
naming collision inside a project's own name could mis-parse) - but it's
strictly better than a guaranteed-None field for a whole city.
"""

import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CARD_SELECTOR = ".mb-srp__card"
DELAY_BETWEEN_PAGES_SECONDS = 1.5


@dataclass
class RawListing:
    source: str
    corridor: str
    title: str | None
    society_name_raw: str | None
    price_raw: str | None
    status: str | None
    transaction_type: str | None
    carpet_area_raw: str | None
    posted_by_raw: str | None
    posted_recency_raw: str | None
    description_raw: str
    detail_url: str | None


def slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def build_url(corridor_slug: str, city_slug: str, page: int = 1) -> str:
    base = f"https://www.magicbricks.com/flats-in-{corridor_slug}-{city_slug}-for-sale-pppfs"
    return base if page == 1 else f"{base}?page={page}"


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _summary_value(card, key: str) -> str | None:
    item = card.locator(f"[data-summary='{key}'] .mb-srp__card__summary--value")
    if item.count() > 0:
        return _normalize_whitespace(item.first.inner_text())
    return None


def _text_or_none(card, selector: str) -> str | None:
    loc = card.locator(selector)
    if loc.count() > 0:
        return _normalize_whitespace(loc.first.inner_text())
    return None


PDPID_RE = re.compile(r"-pdpid-[a-z0-9]+/?$", re.IGNORECASE)


def _society_from_url(url: str | None, all_corridor_slugs: list[str], city_slug: str) -> str | None:
    """Parses the project/society slug out of a MagicBricks detail URL,
    e.g. '.../my-home-bhooja-hitech-city-hyderabad-pdpid-xyz' -> 'My Home
    Bhooja'. Returns None if nothing is left after stripping the known
    city/pdpid/corridor suffixes.

    Strips against every corridor in the city, not just the corridor being
    searched: a listing's URL always embeds its true locality (e.g.
    '...-kondapur-hyderabad-...'), which for a cross-corridor duplicate
    differs from whichever corridor search happened to surface it (e.g.
    found via both the Gachibowli and Kondapur searches). Stripping only
    the search corridor would leave the Gachibowli-found copy as "Indis
    Viva City Kondapur" and the Kondapur-found copy as "Indis Viva City" -
    different signatures that dedup would never compare, silently
    recreating the exact cross-corridor bug this fallback needs to avoid.

    Rejects non-detail-page hrefs before parsing (2026-07-07, found live in
    Chennai/Bangalore data): a card's first <a> is sometimes a shortlist/
    compare icon with href="javascript:void(0)" or "#", not the project
    link. That string has no "/" and no dash-delimited slug, so without
    this check it survives every stripping step below unchanged and gets
    title-cased into a fake society ("Javascript:void(0)") that then scores
    like a real one - see DECISIONS.md 2026-07-07."""
    if not url:
        return None
    scheme = urlsplit(url).scheme
    if scheme and scheme not in ("http", "https"):
        return None
    if "/" not in url:
        return None
    last_segment = url.rsplit("/", 1)[-1]
    if "-" not in last_segment:
        return None
    path = PDPID_RE.sub("", last_segment)
    if path.endswith(f"-{city_slug}"):
        path = path[: -len(f"-{city_slug}")]
    for corridor_slug in sorted(all_corridor_slugs, key=len, reverse=True):
        suffix = f"-{corridor_slug}"
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    path = path.strip("-")
    if not path:
        return None
    return " ".join(word.capitalize() for word in path.split("-"))


def _scrape_page(
    context, city_slug: str, corridor: str, page_num: int, all_corridor_slugs: list[str]
) -> list[RawListing]:
    url = build_url(slugify(corridor), city_slug, page=page_num)
    page = context.new_page()
    listings: list[RawListing] = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        cards = page.locator(CARD_SELECTOR)
        for i in range(cards.count()):
            card = cards.nth(i)
            try:
                detail_url = card.locator("a").first.get_attribute("href", timeout=3000)
            except Exception:
                detail_url = None
            society_name_raw = _summary_value(card, "society") or _society_from_url(
                detail_url, all_corridor_slugs, city_slug
            )
            listings.append(
                RawListing(
                    source="magicbricks",
                    corridor=corridor,
                    title=_text_or_none(card, ".mb-srp__card--title"),
                    society_name_raw=society_name_raw,
                    price_raw=_text_or_none(card, ".mb-srp__card__price--amount"),
                    status=_summary_value(card, "status"),
                    transaction_type=_summary_value(card, "transaction"),
                    carpet_area_raw=_summary_value(card, "carpet-area"),
                    posted_by_raw=_text_or_none(card, ".mb-srp__card__ads--name"),
                    posted_recency_raw=_text_or_none(card, ".mb-srp__card__photo__fig--post"),
                    description_raw=_text_or_none(card, ".mb-srp__card--desc--text p") or "",
                    detail_url=detail_url,
                )
            )
    finally:
        page.close()
    return listings


def scrape_corridor(
    city_slug: str,
    corridor: str,
    max_listings: int = 30,
    pages: int = 1,
    all_corridors: list[str] | None = None,
) -> list[RawListing]:
    """Scrapes `pages` pages (~30 listings each) for one corridor. `pages=1`
    (the default) reproduces the original single-page sample; `max_listings`
    still caps the total returned, applied after all requested pages are
    fetched. `all_corridors` (every corridor name in the city, including
    this one) is used only for the society-name-from-URL fallback - pass
    it whenever the caller has the full city config available, so
    cross-corridor duplicates still resolve to the same fallback society
    name regardless of which corridor search found them."""

    all_corridor_slugs = [slugify(c) for c in (all_corridors or [corridor])]
    listings: list[RawListing] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)

        for page_num in range(1, pages + 1):
            listings.extend(_scrape_page(context, city_slug, corridor, page_num, all_corridor_slugs))
            if page_num < pages:
                time.sleep(DELAY_BETWEEN_PAGES_SECONDS)

        browser.close()

    return listings[:max_listings] if max_listings else listings
