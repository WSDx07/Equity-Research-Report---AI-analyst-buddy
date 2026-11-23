import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import marked_worksheet

# Made-up statement lines; "(thousands)" with no "in" is how some 10-Ks print the scale.
STATEMENT = """CONSOLIDATED STATEMENTS OF CASH FLOWS
(thousands) | 2025 | | 2024
Depreciation | 406,801 | | | 362,771
"""


class SourceAmountScaleTests(unittest.TestCase):
    def amount(self, text, value):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "10-K.txt").write_text(text, encoding="utf-8")
            item = {"source_file": "10-K.txt", "line": 3, "value": value, "section": "CASH FLOWS"}
            return marked_worksheet._source_amount(item, run)

    def test_bare_thousands_header_sets_the_scale(self):
        self.assertEqual(self.amount(STATEMENT, 406801000), (Decimal("406801"), Decimal(1000), "thousands"))

    def test_in_millions_header_still_works(self):
        text = STATEMENT.replace("(thousands)", "(in millions)")
        self.assertEqual(self.amount(text, 406801000000)[2], "millions")

    def test_no_printed_scale_is_still_refused(self):
        text = STATEMENT.replace("(thousands) | 2025 | | 2024", "2025 | | 2024")
        with self.assertRaises(ValueError):
            self.amount(text, 406801000)


if __name__ == "__main__":
    unittest.main()
