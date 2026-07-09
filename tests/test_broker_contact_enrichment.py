"""
Confidence-gate checks for scoring/broker_contact_enrichment.py (2026-07-06).
No network/API key needed - requests.get is mocked so these run anywhere,
including this environment which has no GOOGLE_MAPS_API_KEY configured.
Covers the exact 4 cases manually verified before shipping: a genuine match,
a right-name-wrong-city match, a right-city-wrong-business match, and a
zero-result search - the confidence gate must reject all but the first.
"""

from unittest.mock import MagicMock, patch

from scoring.broker_contact_enrichment import BrokerLookupSubject, _resolve_one


def _fake_get(url, params=None, timeout=None):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    if "textsearch" in url:
        q = params["query"]
        if "GoodMatch" in q:
            resp.json.return_value = {
                "status": "OK",
                "results": [{"name": "GoodMatch Realtors", "formatted_address": "123 Main St, Pune, Maharashtra", "place_id": "abc"}],
            }
        elif "WrongCity" in q:
            resp.json.return_value = {
                "status": "OK",
                "results": [{"name": "WrongCity Realtors", "formatted_address": "123 Main St, Mumbai, Maharashtra", "place_id": "xyz"}],
            }
        elif "NameMismatch" in q:
            resp.json.return_value = {
                "status": "OK",
                "results": [{"name": "Totally Unrelated Business", "formatted_address": "123 Main St, Pune, Maharashtra", "place_id": "zzz"}],
            }
        else:
            resp.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    else:
        resp.json.return_value = {
            "status": "OK",
            "result": {"formatted_phone_number": "+91 98765 43210", "website": "https://goodmatch.example.com", "formatted_address": "123 Main St, Pune"},
        }
    return resp


def test_genuine_name_and_locality_match_is_accepted():
    subject = BrokerLookupSubject("pune", "Pune", "goodmatch realtors", "GoodMatch Realtors")
    with patch("scoring.broker_contact_enrichment.requests.get", side_effect=_fake_get):
        result = _resolve_one(subject, "fake-key")
    assert result.matched is True
    assert result.phone == "+91 98765 43210"
    assert result.website == "https://goodmatch.example.com"


def test_right_name_wrong_city_is_rejected():
    subject = BrokerLookupSubject("pune", "Pune", "wrongcity realtors", "WrongCity Realtors")
    with patch("scoring.broker_contact_enrichment.requests.get", side_effect=_fake_get):
        result = _resolve_one(subject, "fake-key")
    assert result.matched is False
    assert result.phone is None


def test_right_city_wrong_business_is_rejected():
    subject = BrokerLookupSubject("pune", "Pune", "namemismatch agency", "NameMismatch Agency")
    with patch("scoring.broker_contact_enrichment.requests.get", side_effect=_fake_get):
        result = _resolve_one(subject, "fake-key")
    assert result.matched is False


def test_zero_results_is_unavailable_not_a_crash():
    subject = BrokerLookupSubject("pune", "Pune", "nomatch agency", "NoMatch Agency")
    with patch("scoring.broker_contact_enrichment.requests.get", side_effect=_fake_get):
        result = _resolve_one(subject, "fake-key")
    assert result.matched is False
    assert "No Places result" in result.confidence_note


if __name__ == "__main__":
    test_genuine_name_and_locality_match_is_accepted()
    test_right_name_wrong_city_is_rejected()
    test_right_city_wrong_business_is_rejected()
    test_zero_results_is_unavailable_not_a_crash()
    print("All broker_contact_enrichment tests passed.")
