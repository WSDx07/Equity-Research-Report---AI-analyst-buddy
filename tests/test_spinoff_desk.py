import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from equity_research_data_desk import Desk, CONCEPTS
from equity_desk.desk_verifier import load_filings
from equity_desk.equity_research_roles import Claim, Research, research_errors


class SpinoffDeskTests(unittest.TestCase):
    def setUp(self):
        self.desk = Desk.__new__(Desk)
        self.desk.ticker = 'XYZ'
        self.desk.filings = None
        self.desk.filing_text = {}
        self.desk.company_info = Mock(return_value={'ticker': 'XYZ', 'name': 'Example', 'cik': 123})
        self.rows = [
            {'form': '10-Q', 'filingDate': '2026-10-20', 'accessionNumber': 'q', 'items': ''},
            {'form': '8-K', 'filingDate': '2026-10-19', 'accessionNumber': 'e', 'items': '2.02'},
            {'form': '10-12B/A', 'filingDate': '2026-09-01', 'accessionNumber': 'r', 'items': ''},
        ]
        self.desk.submissions = Mock(return_value={'url': 'https://sec.example/submissions', 'rows': self.rows})
        self.desk.index_details = Mock(side_effect=lambda cik, row: {'index_url': row['accessionNumber'], 'accepted': None,
            'documents': [{'type': row['form'], 'url': 'https://sec.example/document'},
                          {'type': 'EX-99.1', 'url': 'https://sec.example/exhibit'}]})
        self.desk.client = Mock()
        self.desk.client.get.return_value = b'<html>Item 2.02 Results</html>'

    def test_registration_is_not_mislabeled_as_annual_report(self):
        result = self.desk.choose_filings()
        self.assertIn('Form 10', result)
        self.assertEqual(result['Form 10']['form'], '10-12B/A')
        self.assertNotIn('10-K', result)
        self.assertEqual(result['10-Q']['accessionNumber'], 'q')

    def test_missing_annual_xbrl_does_not_annualize_quarters(self):
        self.desk.client.json.return_value = {'facts': {'us-gaap': {}}}
        facts = self.desk.collect_facts(self.desk.company_info())
        self.assertIsNone(facts['fiscal_year_end'])
        self.assertEqual(set(facts['concepts']), set(CONCEPTS))
        self.assertTrue(all(item['current'] is None for item in facts['concepts'].values()))
        self.assertIn('not annualized', facts['limitation'])

    def test_verifier_reads_form_ten_without_calling_it_ten_k(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for form in ('Form 10', '10-Q', '8-K', 'EX-99.1'):
                (path / f'XYZ_{form}_id.txt').write_text(form, encoding='utf-8')
            filings = load_filings(path)
            self.assertEqual(filings['Form 10'], 'Form 10')
            self.assertNotIn('10-K', filings)

    def test_quarterly_claim_is_validated_against_quarterly_source(self):
        claim = Claim(section='Overview', claim='Evidence.', document='10-Q', line=1, quote='Evidence.')
        result = research_errors(Research(claims=[claim], gaps=[]), {'10-Q': 'Evidence.', 'EX-99.1': ''})
        self.assertFalse(any('invalid or non-verbatim' in issue for issue in result))


if __name__ == '__main__':
    unittest.main()
