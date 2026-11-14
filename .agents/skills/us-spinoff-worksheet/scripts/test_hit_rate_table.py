import json
import tempfile
import unittest
from pathlib import Path

import hit_rate_table as table


class HitRateTableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bars = self.root / 'bars.json'
        self.bars.write_text(json.dumps({'ticker': 'XYZ', 'bars': [
            {'ticker': 'XYZ', 'date': '2025-01-02', 'close': '100', 'basis': 'official_unadjusted', 'session': 'regular'},
            {'ticker': 'XYZ', 'date': '2025-01-03', 'close': '110', 'basis': 'official_unadjusted', 'session': 'regular'},
        ]}), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_timely_late_and_not_computed_views(self):
        view = {'ticker': 'XYZ', 'filing_time': '2025-01-02T16:30:00-05:00',
                'view_time': '2025-01-03T12:00:00-05:00', 'direction': 'more than price',
                'reader_file': str(self.bars)}
        result = table.calculate_reaction(view, self.root / 'worksheet.json')
        self.assertEqual(result['reaction_percent'], '10.0')
        self.assertEqual(result['agreement'], 'agree')
        self.assertEqual(table.calculate_reaction(view | {'direction': 'not computed'}, self.root / 'worksheet.json')['agreement'], 'not computed')
        late = table.calculate_reaction(view | {'view_time': '2025-01-03T16:00:01-05:00'}, self.root / 'worksheet.json')
        self.assertEqual(late['agreement'], 'after')

    def test_new_reader_bar_updates_reaction_without_changing_view_file(self):
        run = self.root / 'run'
        run.mkdir()
        record = run / 'worksheet.json'
        data = {'live_view': {'ticker': 'XYZ', 'filing_time': '2025-01-02T16:30:00-05:00',
                'view_time': '2025-01-03T12:00:00-05:00', 'direction': 'less than price',
                'reader_file': str(self.bars)}}
        record.write_text(json.dumps(data), encoding='utf-8')
        original = record.read_bytes()
        source = json.loads(self.bars.read_text(encoding='utf-8'))
        self.bars.write_text(json.dumps(source | {'bars': source['bars'][:1]}), encoding='utf-8')
        self.assertIsNone(list(table.worksheet_views(self.root))[0][1]['reaction_percent'])
        self.bars.write_text(json.dumps(source), encoding='utf-8')
        result = list(table.worksheet_views(self.root))[0][1]
        self.assertEqual(result['agreement'], 'disagree')
        self.assertEqual(record.read_bytes(), original)

    def test_missing_and_ambiguous_run_and_missing_reader_remain_visible(self):
        (self.root / 'empty').mkdir()
        ambiguous = self.root / 'ambiguous'
        (ambiguous / 'a').mkdir(parents=True)
        (ambiguous / 'b').mkdir()
        for path in (ambiguous / 'a' / 'worksheet.json', ambiguous / 'b' / 'worksheet.json'):
            path.write_text('{}', encoding='utf-8')
        run = self.root / 'missing_reader'
        run.mkdir()
        view = {'ticker': 'XYZ', 'filing_time': '2025-01-02T16:30:00-05:00',
                'view_time': '2025-01-03T12:00:00-05:00', 'direction': 'more than price',
                'reader_file': str(self.root / 'missing.json')}
        (run / 'worksheet.json').write_text(json.dumps({'live_view': view}), encoding='utf-8')
        rows = list(table.worksheet_views(self.root))
        self.assertEqual(len(rows), 3)
        self.assertTrue(any('Multiple worksheet' in row['reason'] for _, row in rows))
        self.assertTrue(any('No worksheet' in row['reason'] for _, row in rows))
        failed = next(row for _, row in rows if row['ticker'] == 'XYZ')
        self.assertEqual(failed['direction'], 'more than price')
        self.assertEqual(failed['view_time'], view['view_time'])

    def test_reject_reader_for_different_ticker(self):
        with self.assertRaisesRegex(ValueError, 'ticker'):
            table.load_bars(self.bars, 'OTHER')

    def test_member_and_spinoff_are_shown_even_when_worksheet_is_missing(self):
        run = self.root / 'member_run'
        run.mkdir()
        (run / 'run_info.json').write_text(json.dumps({'member': 'Sam', 'spinoff_ticker': 'ABC',
                                                       'live_cik': '123'}), encoding='utf-8')
        rows = list(table.worksheet_views(self.root))
        self.assertEqual(rows[0][1]['member'], 'Sam')
        self.assertEqual(rows[0][1]['spinoff'], 'ABC')
        self.assertEqual(rows[0][1]['ticker'], 'not listed')


if __name__ == '__main__':
    unittest.main()
