"""
Gemini classification for the free-text parts of a listing: society-name
cleanup and the tiered absentee/NRI signals. Gemini reads and classifies
only, it never assigns a score and never fills in a number (CLAUDE.md hard
rule) - price/area/BHK/listing_type are parsed deterministically in
classify/parsing.py instead.

Absentee/NRI flags cover Tier 1 (high confidence) and Tier 2 (medium
confidence) signals from the user's 2026-07-04 expansion (DECISIONS.md) of
the original 4-signal design (2026-07-03). Every flag here must be an
explicit textual signal, not an inference - this is unchanged from the
original design and still applies to every new flag added. Two Tier 3
signals (below-market price, NRI-heavy society) are comparative/config
signals computed in scoring/absentee.py, not asked of Gemini. A Tier 3
surname heuristic was explicitly declined (bias-prone, see DECISIONS.md).

Listings are classified in batches (one Gemini call per batch, not one per
listing): the free-tier quota for gemini-2.5-flash is 5 requests/minute, so
one-call-per-listing exhausts it almost immediately on any real corridor
(hit in testing 2026-07-03, see DECISIONS.md).
"""

import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from classify.schema import GeminiFlagsBatch

load_dotenv()

# gemini-2.5-flash's free tier caps at 20 requests/DAY (hit in testing,
# 2026-07-03, see DECISIONS.md). flash-lite carries a separate, higher
# free-tier daily quota, so it is used here instead of the full flash model.
MODEL = "gemini-2.5-flash-lite"
BATCH_SIZE = 10
MAX_RETRIES = 5
BASE_RETRY_DELAY_SECONDS = 15

BATCH_PROMPT_TEMPLATE = """You are classifying {n} real-estate resale listings.
For EACH listing, read its title, scraped society name, and free-text
description. Extract ONLY what is explicitly stated. Do not guess or infer
from indirect cues (e.g. do not assume NRI just because the price is high,
and do not infer anything from the owner's name).

Return exactly {n} items in the same order as the listings below, each
tagged with its listing_index (0-based, matching the numbering below).

Per-listing fields:
- society_name_normalized: the society/building name in clean, standard
  title case (e.g. "Tcg The Crown Greens" -> "TCG The Crown Greens"). If no
  society name is present or scraped, return null.

Tier 1 (explicit, high confidence):
- flag_nri_mention: true only if the text explicitly says the owner/seller
  is NRI, lives abroad, or is a "NRI seller".
- flag_poa_mention: true only if the text explicitly mentions Power of
  Attorney, POA, or an "attorney holder".
- flag_owner_abroad: true only if the text explicitly says the owner is
  abroad or overseas (distinct from the more generic "not local" below).

Tier 2 (explicit, medium confidence):
- flag_owner_not_local: true only if the text explicitly says the owner is
  not local, out of station, or residing in a different city (a generic
  version of "abroad" - use this when the text says "not local" etc but
  does not specify abroad/overseas).
- flag_visit_by_appointment_only: true only if the text explicitly says the
  property/owner is available for viewing only by appointment, or the
  owner is otherwise unavailable for a visit.
- flag_calling_hours_hint: true only if the text explicitly gives specific
  calling hours suggesting a timezone gap (e.g. "call after 7pm IST",
  "call only between X and Y").
- flag_long_vacant_or_tenanted: true only if the text explicitly mentions
  the property being vacant for a long period (6+ months), tenanted for a
  long period, or being re-listed / relisted.
- flag_investment_property_mention: true only if the text explicitly says
  the property IS CURRENTLY generating rental income, is tenanted, or was
  bought/is held as an investment (e.g. "currently rented at X/month",
  "good rental income", "owner treats this as an investment"). Do NOT
  count generic marketing boilerplate that invites the reader to "buy or
  invest in [city]" - that is a call-to-action on every listing, not a
  statement about this specific property's status.

If none of the source text supports a flag, it must be false.

Listings:
{listings_block}"""


def _format_listing(i: int, title: str | None, society_name_raw: str | None, description: str) -> str:
    return (
        f"[{i}]\n"
        f"Title: {title or '(none)'}\n"
        f"Society name as scraped: {society_name_raw or '(none)'}\n"
        f"Description: {description or '(none)'}\n"
    )


def _call_with_retry(fn):
    delay = BASE_RETRY_DELAY_SECONDS
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except (ServerError, ClientError) as e:
            if attempt == MAX_RETRIES - 1:
                raise
            is_retryable = isinstance(e, ServerError) or (
                isinstance(e, ClientError) and getattr(e, "code", None) == 429
            )
            if not is_retryable:
                raise
            time.sleep(delay + random.uniform(0, delay * 0.5))
            delay *= 2


def classify_flags_batch(
    client: genai.Client,
    listings: list[dict],
) -> list[GeminiFlagsBatch]:
    """`listings` is a list of dicts with keys: title, society_name_raw,
    description. Returns GeminiFlags in the same order as input."""

    listings_block = "\n".join(
        _format_listing(i, l.get("title"), l.get("society_name_raw"), l.get("description"))
        for i, l in enumerate(listings)
    )
    prompt = BATCH_PROMPT_TEMPLATE.format(n=len(listings), listings_block=listings_block)

    def _do_call():
        return client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiFlagsBatch,
            ),
        )

    response = _call_with_retry(_do_call)
    batch = GeminiFlagsBatch.model_validate_json(response.text)
    return sorted(batch.items, key=lambda item: item.listing_index)


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Copy .env.example to .env and fill it in.")
    return genai.Client(api_key=api_key)
