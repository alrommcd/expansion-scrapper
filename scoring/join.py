"""
Join layer: combines the society fit score and absentee density score into
the single ranked table the product is built around (PRD: "one joined
view", society is the spine). Broker matching (Layer 2) is not built yet,
so matched_brokers is always empty for now - see PROGRESS.md.
"""

import sqlite3

from scoring.absentee import score_absentee_density
from scoring.society import rank_societies


def build_ranked_society_table(
    conn: sqlite3.Connection, city_id: str, corridor: str, nri_heavy_societies: list[str] | None = None
) -> list[dict]:
    fit_results = rank_societies(conn, city_id, corridor)
    absentee_by_id = {
        r.society_id: r for r in score_absentee_density(conn, city_id, corridor, nri_heavy_societies)
    }

    joined = []
    for fit in fit_results:
        absentee = absentee_by_id.get(fit.society_id)
        joined.append(
            {
                "society_id": fit.society_id,
                "society_name": fit.canonical_name,
                "listing_count": fit.listing_count,
                "fit_score": fit.fit_score,
                "fit_sub_scores": fit.sub_scores,
                "absentee_avg_score": absentee.avg_score if absentee else None,
                "absentee_density": absentee.absentee_density if absentee else None,
                "absentee_hot_count": absentee.hot_count if absentee else 0,
                "absentee_warm_count": absentee.warm_count if absentee else 0,
                "absentee_cold_count": absentee.cold_count if absentee else 0,
                "matched_brokers": [],  # Layer 2 not built yet
            }
        )

    return sorted(joined, key=lambda row: row["fit_score"], reverse=True)
