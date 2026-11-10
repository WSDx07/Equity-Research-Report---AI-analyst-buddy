import unittest

from equity_desk.filing_excerpts import cited_excerpts, numbered_excerpt


class FilingExcerptsTest(unittest.TestCase):
    def test_bounded_excerpt_preserves_line_numbers_and_discloses_omissions(self):
        text = "\n".join(["ordinary sentence"] * 100 + ["Revenue grew"] + ["other sentence"] * 100)
        excerpt = numbered_excerpt(text, 500)
        self.assertLessEqual(len(excerpt), 500)
        self.assertIn("omitted lines", excerpt)
        self.assertIn("101: Revenue grew", excerpt)

    def test_verifier_receives_cited_line_and_neighbors(self):
        text = "\n".join(f"line content {i}" for i in range(1, 100))
        result = cited_excerpts("- Claim — 10-K line 57: line content 57", {"10-K": text}, 1000)
        self.assertIn("57: line content 57", result["10-K"])
        self.assertIn("56: line content 56", result["10-K"])
        self.assertIn("omitted", result["10-K"])


if __name__ == "__main__":
    unittest.main()
