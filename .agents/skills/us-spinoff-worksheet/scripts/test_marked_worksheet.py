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


class UnprintableInputTests(unittest.TestCase):
    """An input with no printed scale is dropped before calculation, and the worksheet says not known."""
    def bundle(self, folder, header):
        run = Path(folder)
        (run / "10-K.txt").write_text(STATEMENT.replace("(thousands) | 2025 | | 2024", header), encoding="utf-8")
        item = {"source_file": "10-K.txt", "line": 3, "value": 406801000, "section": "CASH FLOWS", "unit": "USD",
                "tag": "historical", "period": "FY2025", "filing": "10-K"}
        return {"run": run, "inputs": {"inputs": {"depreciation": item, "market_price": {"value_usd": None}},
                                       "material_unknowns": []}}

    def test_unprintable_input_is_dropped_and_listed(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle = self.bundle(folder, "2025 | | 2024")
            self.assertEqual(marked_worksheet.drop_unprintable_inputs(bundle), ["depreciation"])
            self.assertNotIn("depreciation", bundle["inputs"]["inputs"])
            self.assertIn("market_price", bundle["inputs"]["inputs"])
            self.assertEqual(len(bundle["inputs"]["material_unknowns"]), 1)

    def test_printable_input_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle = self.bundle(folder, "(thousands) | 2025 | | 2024")
            self.assertEqual(marked_worksheet.drop_unprintable_inputs(bundle), [])
            self.assertIn("depreciation", bundle["inputs"]["inputs"])

    def test_filing_line_says_not_known_instead_of_stopping(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle = self.bundle(folder, "2025 | | 2024")
            item = bundle["inputs"]["inputs"]["depreciation"]
            line = marked_worksheet._filing("Release revenue", item, bundle["run"])
            self.assertEqual(line, "- Release revenue: " + marked_worksheet.UNPRINTABLE)


if __name__ == "__main__":
    unittest.main()
