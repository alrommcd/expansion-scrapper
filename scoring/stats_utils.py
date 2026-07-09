"""
Small generic statistics helpers shared across scoring modules - extracted
2026-07-06 (broker-list layer) from scoring/society_fit.py so both it and
scoring/broker_list.py reuse one definition instead of two copies.
"""


def percentile_ranks(values: list[float]) -> list[float]:
    """0-1 percentile rank per value, 0=worst/lowest, 1=best/highest,
    average rank for ties. A single-value list gets [1.0] - no spread to
    rank against, but it's the best (and only) sample available, so it
    isn't penalized for that."""
    n = len(values)
    if n == 1:
        return [1.0]
    sorted_vals = sorted(values)
    ranks = []
    for v in values:
        matching_positions = [i for i, sv in enumerate(sorted_vals) if sv == v]
        ranks.append((sum(matching_positions) / len(matching_positions)) / (n - 1))
    return ranks
