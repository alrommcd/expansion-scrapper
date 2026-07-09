"""
Regression test for the real bug found 2026-07-06 during broker-count
reconciliation: `_unique_subjects` (build_broker_contact_enrichment.py) used
to do `SELECT DISTINCT city_id, agent_normalized, agent_display`, which
double-counted an agent whose corridors disagree on capitalization only
(found live in Bangalore's real data: "GLOBAL EDIFICE INFRA" in one
corridor's broker_meta row vs "Global Edifice Infra" in another, same
agent_normalized) - inflating 1,118 real unique (city, agent) businesses to
1,119 lookup subjects. Fixed by grouping in Python and picking the most
common display spelling per (city, agent_normalized), same tie-break
broker_list.py already uses within one corridor.
"""

import sqlite3

from build_broker_contact_enrichment import _unique_subjects
from config.cities import CITIES


def _fake_conn_with_capitalization_variants():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE broker_meta (city_id TEXT, corridor TEXT, agent_normalized TEXT, agent_display TEXT)"
    )
    city_id = next(iter(CITIES))
    # Same normalized name, two corridors, two different capitalizations -
    # the exact shape of the real Bangalore case.
    conn.executemany(
        "INSERT INTO broker_meta (city_id, corridor, agent_normalized, agent_display) VALUES (?, ?, ?, ?)",
        [
            (city_id, "Corridor A", "global edifice infra", "GLOBAL EDIFICE INFRA"),
            (city_id, "Corridor A", "global edifice infra", "GLOBAL EDIFICE INFRA"),
            (city_id, "Corridor B", "global edifice infra", "Global Edifice Infra"),
        ],
    )
    conn.commit()
    return conn, city_id


def test_capitalization_variants_collapse_to_one_subject():
    conn, city_id = _fake_conn_with_capitalization_variants()
    subjects = _unique_subjects(conn)
    matching = [s for s in subjects if s.city_id == city_id and s.agent_normalized == "global edifice infra"]
    assert len(matching) == 1, f"expected exactly 1 subject, got {len(matching)}"
    # Most common spelling (2 occurrences) wins over the 1-occurrence variant.
    assert matching[0].agent_display == "GLOBAL EDIFICE INFRA"


if __name__ == "__main__":
    test_capitalization_variants_collapse_to_one_subject()
    print("All build_broker_contact_enrichment tests passed.")
