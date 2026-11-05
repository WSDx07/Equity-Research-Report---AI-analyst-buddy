import unittest
from insight_checks import insight_errors, release_first_paragraph

class InsightChecksTest(unittest.TestCase):
    def test_missing_insight_and_missing_release_are_rejected(self):
        self.assertTrue(insight_errors("", {}, {"status": "unavailable"}))
        source = {"10-K": "Revenue was 8 million."}
        self.assertTrue(insight_errors("Insight: Revenue was 8 million. — 10-K line 1: Revenue was 8 million.", source, {"status": "unavailable"}))

    def test_exact_restatement_is_rejected_and_distinct_insight_accepted(self):
        release = release_first_paragraph("Press release\nCity, January 2, 2026 - Issuer announced revenue of 8 million.")
        source = {"10-K": "Revenue of 8 million.\nMembership grew 5%."}
        repeated = "Insight: revenue of 8 million. — 10-K line 1: Revenue of 8 million."
        distinct = "Insight: Membership grew 5%. — 10-K line 2: Membership grew 5%."
        self.assertTrue(any("repeats" in error for error in insight_errors(repeated, source, release)))
        self.assertEqual(insight_errors(distinct, source, release), [])

if __name__ == "__main__":
    unittest.main()
