import json
import unittest
from types import SimpleNamespace

from equity_desk.financialdatasets_check import compare, fetch_statements


class FinancialDatasetsTest(unittest.TestCase):
    def setUp(self):
        self.facts = {"as_of": "2025-04-01", "company": {"ticker": "TEST"}, "concepts": {"total_revenue": {"tag": "us-gaap:Revenues", "unit": "USD", "current": {"val": 100, "end": "2024-12-31", "filed": "2025-02-01", "accn": "abc"}, "prior": None}}}
        self.statement = {"ticker": "TEST", "period": "annual", "report_period": "2024-12-31", "currency": "USD", "filing_date": "2025-02-01", "accession_number": "abc", "revenue": 100}

    def run_comparison(self, **changes):
        stmt = self.statement | changes
        return compare(self.facts, {"financials": {"income_statements": [stmt]}})["rows"][0]

    def test_exact_match_and_difference(self):
        self.assertEqual(self.run_comparison()["status"], "numeric_match")
        row = self.run_comparison(revenue=120)
        self.assertEqual((row["status"], row["difference_provider_minus_sec"]), ("difference", "20"))

    def test_mismatched_period_filing_currency_and_future_date_are_not_compared(self):
        for change in ({"report_period": "2024-09-30"}, {"accession_number": "other"}, {"currency": "EUR"}, {"filing_date": "2025-05-01"}, {"period": "quarterly"}):
            with self.subTest(change=change):
                self.assertEqual(self.run_comparison(**change)["status"], "not_comparable")

    def test_request_uses_key_only_in_header(self):
        class Session:
            def get(self, url, **kwargs):
                self.args = (url, kwargs)
                return SimpleNamespace(status_code=200, text=json.dumps({"financials": {}}))
        session = Session()
        fetch_statements("TEST", "secret", "2025-04-01", session)
        self.assertEqual(session.args[1]["headers"], {"X-API-KEY": "secret"})
        self.assertNotIn("secret", str(session.args[1]["params"]))
        self.assertFalse(session.args[1]["allow_redirects"])

    def test_missing_key_and_http_errors_are_explicit(self):
        with self.assertRaisesRegex(ValueError, "FINDATA_API_KEY"):
            fetch_statements("TEST", "", "2025-04-01")
        session = SimpleNamespace(get=lambda *a, **kw: SimpleNamespace(status_code=403))
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            fetch_statements("TEST", "secret", "2025-04-01", session)


if __name__ == "__main__":
    unittest.main()
