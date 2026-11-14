import unittest

from scripts.factor_check_demo import compare


class FactorCheckDemoTest(unittest.TestCase):
    def test_thresholds_and_primary_contrast(self):
        records = [
            {'id': 'A', 'market_cap_usd': 2000000000, 'decline_pct': 15, 'insider_pct': 5, 'stock_return': '.10', 'benchmark_return': '.03'},
            {'id': 'B', 'market_cap_usd': 2000000001, 'decline_pct': 14, 'insider_pct': 4, 'stock_return': '.02', 'benchmark_return': '.05'},
        ]
        result = compare(records)
        self.assertEqual(result['counts'][75], 1)
        self.assertEqual(result['counts'][0], 1)
        self.assertEqual(str(result['difference']), '0.10')
        self.assertEqual(result['comparisons'], 1)

    def test_missing_not_scored_and_no_comparison_with_empty_group(self):
        result = compare([{'id': 'A', 'market_cap_usd': None, 'decline_pct': 20, 'insider_pct': 10, 'stock_return': '.2', 'benchmark_return': '.1'}])
        self.assertEqual(result['excluded'], 1)
        self.assertIsNone(result['difference'])
        self.assertEqual(result['comparisons'], 0)

    def test_duplicate_rejected(self):
        row = {'id': 'A', 'market_cap_usd': 1, 'decline_pct': 20, 'insider_pct': 10, 'stock_return': '.2', 'benchmark_return': '.1'}
        with self.assertRaises(ValueError):
            compare([row, row])


if __name__ == '__main__':
    unittest.main()
