-- SQLite schema for the expansion agent. Not yet wired up (Milestone 1 is
-- corridor ranking only, which runs on in-memory seed data). Created now
-- because Milestone 2 (scraper) writes directly into raw_listings, and the
-- shape is already fixed by the approved PRD.

CREATE TABLE IF NOT EXISTS raw_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    source TEXT NOT NULL,          -- e.g. '99acres', 'magicbricks', 'nobroker'
    source_listing_id TEXT,
    raw_text TEXT NOT NULL,
    price_raw TEXT,
    duplicate_of_id INTEGER REFERENCES raw_listings(id),  -- NULL = canonical; set when the same physical property was seen under another corridor (see storage/listing_dedup.py)
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classified_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_listing_id INTEGER NOT NULL REFERENCES raw_listings(id),
    society_name_as_written TEXT,
    society_id INTEGER REFERENCES societies(id),  -- NULL until entity-resolved
    price_inr INTEGER,
    area_sqft INTEGER,
    bhk INTEGER,
    listing_type TEXT,             -- 'owner' | 'agent' | 'unknown'
    possession_status TEXT,        -- 'ready_to_move' | 'under_construction' | 'unknown'
    days_since_posted INTEGER,     -- parsed from source's 'posted/updated X ago' text, NULL if unparseable
    mentions_rera INTEGER DEFAULT 0,  -- deterministic keyword parse, feeds society title-cleanliness signal
    -- Absentee/NRI signals (tiered 2026-07-04, see DECISIONS.md). Tier 1/2
    -- below are Gemini judgment calls on explicit text; flag_international_
    -- contact_hint is a deterministic regex check (not a fetched phone
    -- number). Two Tier 3 signals (below-market price, NRI-heavy society)
    -- are comparative/config-driven and computed at scoring time instead
    -- of stored here.
    flag_nri_mention INTEGER DEFAULT 0,            -- Tier 1
    flag_poa_mention INTEGER DEFAULT 0,             -- Tier 1
    flag_owner_abroad INTEGER DEFAULT 0,            -- Tier 1
    flag_international_contact_hint INTEGER DEFAULT 0,  -- Tier 1, deterministic
    flag_owner_not_local INTEGER DEFAULT 0,         -- Tier 2
    flag_visit_by_appointment_only INTEGER DEFAULT 0,  -- Tier 2
    flag_calling_hours_hint INTEGER DEFAULT 0,      -- Tier 2
    flag_long_vacant_or_tenanted INTEGER DEFAULT 0, -- Tier 2
    flag_investment_property_mention INTEGER DEFAULT 0,  -- Tier 2
    igr_confidence REAL,           -- reserved for v2 IGR layer, not populated in v1
    classified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS societies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    rera_registered INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS brokers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    name TEXT NOT NULL,
    source TEXT NOT NULL,          -- directory the broker was compiled from
    rating REAL,
    review_count INTEGER,
    last_active_at TEXT
);

CREATE TABLE IF NOT EXISTS broker_society_links (
    broker_id INTEGER NOT NULL REFERENCES brokers(id),
    society_id INTEGER NOT NULL REFERENCES societies(id),
    listing_count INTEGER DEFAULT 0,
    PRIMARY KEY (broker_id, society_id)
);

CREATE TABLE IF NOT EXISTS society_scores (
    society_id INTEGER PRIMARY KEY REFERENCES societies(id),
    fit_score REAL NOT NULL,
    absentee_score REAL NOT NULL,  -- heuristic, low-confidence, see DECISIONS.md
    computed_at TEXT NOT NULL
);

-- Society-level PRODUCT-FIT layer (rung 3: city -> corridor -> society ->
-- people), added 2026-07-06. Deliberately separate from society_scores
-- above (the older, unpopulated classified_listings-based table) and from
-- corridor fit_score / absentee_score - three distinct numbers, never
-- merged. One row per (city, corridor, normalized society name); the same
-- physical society can have two rows if it genuinely straddles two
-- corridors (see appears_in_corridors), which is intentional, not a bug.
CREATE TABLE IF NOT EXISTS society_meta (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    society_normalized TEXT NOT NULL,
    society_display TEXT NOT NULL,
    supply_depth INTEGER NOT NULL,          -- count of in-band canonical listings
    resale_velocity_days REAL,              -- avg days_since_posted across in-band canonical listings
    price_consistency_cov REAL,             -- stdev/mean of in-band price, lower = tighter
    rating REAL,                            -- Google Maps star rating, NULL if unavailable
    review_count INTEGER,                   -- Google Maps review count, NULL if unavailable
    rating_available INTEGER NOT NULL DEFAULT 0,
    society_fit_score REAL,                 -- 0-10, see scoring/society_fit.py
    appears_in_corridors TEXT,               -- JSON array; 2+ entries = cross-corridor contamination flag
    last_computed TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, society_normalized)
);

-- Cache for Google Maps Places lookups so re-runs don't re-hit the API for
-- the same society/corridor/city query. Keyed on the exact query string
-- sent to the API, not on society_normalized, since the query text (display
-- name + corridor + city) is what the API actually sees.
CREATE TABLE IF NOT EXISTS maps_cache (
    query TEXT PRIMARY KEY,
    matched INTEGER NOT NULL,   -- 0/1: did the API return a plausible match at all
    rating REAL,
    review_count INTEGER,
    looked_up_at TEXT NOT NULL
);

-- BROKER-LIST layer (rung 3b: agents/brokers active in a corridor), added
-- 2026-07-06. A straight extraction+count, not a signal-discovery score -
-- broker_activity_score is a fourth, independent number, never merged with
-- fit_score / absentee_score / society_fit_score. phone and company are
-- schema-reserved but always NULL today: confirmed live that MagicBricks
-- gates an agent's phone behind a "Get Phone No." click-through (same gate
-- already documented for owner phone numbers) and does not expose a
-- separate company field distinct from the posted-by name - see
-- scoring/broker_list.py docstring and DECISIONS.md.
CREATE TABLE IF NOT EXISTS broker_meta (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    agent_normalized TEXT NOT NULL,
    agent_display TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    listing_count INTEGER NOT NULL,         -- distinct canonical listings (by detail_url where present)
    broker_activity_score REAL,             -- 0-10, percentile rank of listing_count within the city
    last_computed TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, agent_normalized)
);

-- Broker CONTACT enrichment (2026-07-06), additive on top of the locked
-- broker_meta above - never modifies it. One row per real-world business
-- (city + agent_normalized, not per corridor - the same agency active in
-- two corridors is one lookup, not two). Sourced from Google Places API
-- only (same key as maps_cache below); matched=0 means "no confident
-- source found", never a low-confidence guess - see
-- scoring/broker_contact_enrichment.py.
CREATE TABLE IF NOT EXISTS broker_contact_enrichment (
    city_id TEXT NOT NULL,
    agent_normalized TEXT NOT NULL,
    agent_display TEXT NOT NULL,
    matched INTEGER NOT NULL,
    phone TEXT,
    website TEXT,
    address TEXT,
    source TEXT,                    -- e.g. "Google Places"
    confidence_note TEXT NOT NULL,  -- always populated, explains match or non-match
    looked_up_at TEXT NOT NULL,
    PRIMARY KEY (city_id, agent_normalized)
);

-- Society DETAIL enrichment (2026-07-06), additive on top of the locked
-- society_meta above - never touches society_fit_score or its inputs.
-- Tries to resolve each qualifying society's official project page via the
-- same Places API key, then fetches that ONE page once for whatever's
-- published (unit count, possession status, RERA number, sales contact,
-- description). matched=0 or a null field means "not found/not confident",
-- never invented - see scoring/society_enrichment.py.
CREATE TABLE IF NOT EXISTS society_detail_enrichment (
    city_id TEXT NOT NULL,
    corridor TEXT NOT NULL,
    society_normalized TEXT NOT NULL,
    society_display TEXT NOT NULL,
    matched INTEGER NOT NULL,
    official_url TEXT,
    unit_count TEXT,
    possession_status TEXT,
    rera_number TEXT,
    sales_contact TEXT,
    project_description TEXT,
    source TEXT,
    confidence_note TEXT NOT NULL,
    looked_up_at TEXT NOT NULL,
    PRIMARY KEY (city_id, corridor, society_normalized)
);
