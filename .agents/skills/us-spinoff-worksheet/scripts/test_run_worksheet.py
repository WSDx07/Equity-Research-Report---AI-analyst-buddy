import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch

import prepare_worksheet
import run_worksheet
import worksheet_evidence
import worksheet_math
import worksheet_guard


class WorksheetWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run_dir = self.root / 'run'
        self.run_dir.mkdir()
        self.accession = '0000000000-25-000001'
        current = {'val': 100, 'start': '2024-01-01', 'end': '2024-12-31',
                   'filed': '2025-01-15', 'accn': self.accession, 'form': '10-K'}
        def concept(value, unit='USD'):
            return {'unit': unit, 'tag': 'test:Concept', 'current': dict(current, val=value)}
        self.facts = {'company': {'ticker': 'XYZ', 'cik': 123}, 'as_of': '2025-02-01',
                      'concepts': {'net_income': concept(100),
                                   'depreciation_and_amortization': concept(20),
                                   'additions_to_property_and_equipment': concept(30),
                                   'diluted_shares_outstanding': concept(10, 'shares')}}
        (self.run_dir / 'facts.json').write_text(json.dumps(self.facts), encoding='utf-8')
        (self.run_dir / 'filings.json').write_text('{}', encoding='utf-8')
        (self.run_dir / f'XYZ_10-K_{self.accession}.txt').write_text(
            'INCOME STATEMENTS\n(In dollars)\n2024\n2023\nNet income\n100\n90\n'
            'CASH FLOWS STATEMENTS\n(In dollars)\n2024\n2023\n'
            'Depreciation and amortization\n20\n19\nAdditions to property and equipment\n30\n25\n'
            'DILUTED SHARES OUTSTANDING\n(In shares)\n2024\n2023\nDiluted shares outstanding\n10\n9\n', encoding='utf-8')
        self.registry = self.root / 'registry.json'
        self.registry.write_text('{}', encoding='utf-8')
        self.env = self.root / '.env'
        self.env.write_text('PURDUE_API_KEY=test\n', encoding='utf-8')
        self.persona = self.root / 'persona.md'
        self.persona.write_text('Use only the supplied evidence.', encoding='utf-8')
        self.bars = self.root / 'bars.json'
        rows = []
        day = date(2025, 1, 1)
        while len(rows) < 22:
            if day.weekday() < 5:
                rows.append({'ticker': 'XYZ', 'date': day.isoformat(), 'close': '10', 'volume': '2000000',
                             'basis': 'official_unadjusted', 'session': 'regular', 'when_issued': False})
            day += timedelta(days=1)
        self.bars.write_text(json.dumps({'ticker': 'XYZ', 'cik': '123', 'basis': 'official_unadjusted',
                                         'session': 'regular', 'when_issued': False, 'bars': rows}), encoding='utf-8')
        self.purchases = self.root / 'purchases.json'
        self.purchases.write_text('[]', encoding='utf-8')
        self.manifest = {'registry_present': False, 'registration_accession': None,
                         'form4_purchase_file': str(self.purchases), 'form4_coverage': {}, 'errors': [],
                         'live_release': {'ticker': 'XYZ', 'accession': '123',
                                          'filing_time': {'value': '2025-01-31T22:00:00+00:00'}}}
        self.args = SimpleNamespace(run=self.run_dir, registry=self.registry, env=self.env,
                                    rules=run_worksheet.ROOT / 'lab07_worksheet_rules.md', persona=self.persona,
                                    bars=self.bars, live_run=None, live_bars=None, release_accession=None)

    def tearDown(self):
        self.temp.cleanup()

    def test_end_to_end_one_judgment_and_calculations(self):
        prepare = Mock(return_value=(self.root, self.manifest))
        judge = Mock(return_value={'story': 'The evidence is limited.', 'change': 'Review the next cash flow statement.'})
        output = run_worksheet.run(self.args, prepare=prepare, judge=judge)
        result = output.read_text(encoding='utf-8')
        self.assertEqual(judge.call_count, 1)
        self.assertIn('Owner cash flow: 90 USD = 100 + 20 - 30', result)
        self.assertIn('Parent: not applicable', result)
        self.assertIn('Median daily dollar volume: 20000000 USD', result)
        payload = judge.call_args.args[3]
        self.assertNotIn('bars', json.dumps(payload))
        self.assertNotIn('volume', json.dumps(payload))

    def test_missing_price_never_creates_a_view(self):
        self.args.bars = None
        output = run_worksheet.run(self.args, prepare=Mock(return_value=(self.root, self.manifest)),
                                   judge=Mock(return_value={'story': 'Limited evidence.', 'change': 'Review the next filing.'}))
        text = output.read_text(encoding='utf-8')
        self.assertIn('Dated market price: not computed', text)
        self.assertIn('View: not computed', text)
        self.assertIn('Conviction: not computed', text)

    def test_separate_live_company_never_reuses_target_reader(self):
        live_run = self.root / 'live'
        live_run.mkdir()
        live_facts = dict(self.facts, company={'ticker': 'QRS', 'cik': 456})
        (live_run / 'facts.json').write_text(json.dumps(live_facts), encoding='utf-8')
        (live_run / 'filings.json').write_text('{}', encoding='utf-8')
        self.args.live_run = live_run
        output = run_worksheet.run(self.args, prepare=Mock(return_value=(self.root, self.manifest)),
                                   judge=Mock(return_value={'story': 'Limited evidence.', 'change': 'Review the next filing.'}))
        text = output.read_text(encoding='utf-8')
        self.assertIn('Company: QRS', text)
        self.assertIn('View: not computed', text)
        index = next(self.run_dir.glob('worksheet-*/worksheet.json'))
        self.assertIsNone(json.loads(index.read_text(encoding='utf-8'))['live_view']['reader_file'])

    def test_undated_or_future_registry_fact_is_not_used(self):
        result = prepare_worksheet.registry_as_of({'parent': [
            {'value': 'future', 'filing_date': '2025-03-01'}, {'value': 'undated'},
            {'value': 'known', 'filing_date': '2025-01-01'}]}, '2025-02-01')
        self.assertEqual([x['value'] for x in result['parent']], ['known'])

    def test_future_release_close_is_not_used(self):
        cutoff = datetime(2025, 1, 10, 15, tzinfo=timezone.utc)
        bundle = run_worksheet.snapshot(self.run_dir, {}, self.bars, cutoff=cutoff)
        self.assertEqual(bundle['inputs']['inputs']['market_price']['date'], '2025-01-09')
        self.assertNotIn('after_tax_earnings', bundle['inputs']['inputs'])
        self.assertEqual(bundle['financial_as_of'], '2025-01-09')

    def test_mismatched_bars_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'ticker'):
            worksheet_evidence.load_bars(self.bars, 'OTHER', '123', '2025-02-01')

    def test_financing_facts_require_a_dated_registry_accession_and_section(self):
        accession = self.accession.replace('-', '')
        source = self.run_dir / f'form10_{accession}.txt'
        source.write_text('Financing\nWe borrowed $20 million of debt.\n'
                          'We used $10 million of the proceeds to repay parent loans.\n'
                          'The parent transferred $2 million of pension liabilities.\n', encoding='utf-8')
        url = f'https://www.sec.gov/Archives/edgar/data/123/{accession}/filing.htm'
        entity = {'parent': [{'filing': url, 'filing_date': '2025-01-15', 'value': 'Parent'}],
                  'distribution_date': [{'value': '2025-02-01', 'filing_date': '2025-01-15'}]}
        manifest = {'registration_accession': accession,
                    'saved_source_documents': [{'accession': accession, 'url': url, 'path': source.name}]}
        facts = worksheet_evidence.extract_financing_facts(self.run_dir, manifest, entity, '2025-02-01')
        self.assertEqual(facts['debt_raised']['value'], '20000000')
        self.assertEqual(facts['cash_use']['description'], 'repay parent loans')
        self.assertEqual(facts['parent_liabilities']['value'], '2000000')
        self.assertEqual(facts['debt_raised']['tag'], 'historical')
        self.assertEqual(worksheet_evidence.extract_financing_facts(self.run_dir, manifest, entity, '2025-01-01'), {})

    def test_depreciation_statement_requires_unambiguous_label_and_year(self):
        self.facts['fiscal_year_end'] = '2024-12-31'
        del self.facts['concepts']['depreciation_and_amortization']
        path = self.run_dir / f'XYZ_10-K_{self.accession}.txt'
        path.write_text('INCOME STATEMENTS\n(In dollars)\n2024\n2023\nNet income\n100\n90\n'
                        'CASH FLOWS STATEMENTS\n(In millions)\n2024\n2023\n'
                        'Depreciation and amortization\n15\n12\n', encoding='utf-8')
        result = worksheet_evidence.read_financial_inputs(self.run_dir, self.facts)
        self.assertEqual(result['depreciation']['value'], '15000000')
        self.assertEqual(result['depreciation']['line'], 13)
        path.write_text('INCOME STATEMENTS\n(In dollars)\n2024\n2023\nNet income\n100\n90\n'
                        'CASH FLOWS STATEMENTS\n(In millions)\n2024\n2023\n'
                        'Depreciation and amortization and other\n15\n12\n', encoding='utf-8')
        self.assertNotIn('depreciation', worksheet_evidence.read_financial_inputs(self.run_dir, self.facts))

    def test_rule_can_be_low_when_a_material_fact_is_unknown(self):
        rules = worksheet_math.read_rules(self.args.rules)
        inputs = {'as_of': '2025-02-01', 'inputs': {'market_price': {
            'value': '10', 'date': '2025-01-31', 'reader_source': 'reader', 'basis': 'official_unadjusted'}},
            'material_unknowns': ['debt covenant'], 'bars': []}
        self.assertEqual(worksheet_math.calculate(inputs, rules)['conviction']['level'], 'low')

    def test_explicit_coverage_allows_high_conviction_when_rules_pass(self):
        path = self.run_dir / f'XYZ_10-K_{self.accession}.txt'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('Debt\nWe have no material debt covenants.\n')
        bundle = run_worksheet.snapshot(self.run_dir, {}, self.bars)
        result = worksheet_math.calculate(bundle['inputs'], worksheet_math.read_rules(self.args.rules))
        self.assertEqual(result['conviction']['level'], 'high')
        self.assertIn('debt covenants', bundle['explicit_absences'])

    def test_qualified_absence_does_not_clear_the_unknown(self):
        path = self.run_dir / f'XYZ_10-K_{self.accession}.txt'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('Debt\nWe have no material debt covenants except under the credit agreement.\n')
        bundle = run_worksheet.snapshot(self.run_dir, {}, self.bars)
        self.assertIn('debt covenants', bundle['inputs']['material_unknowns'])

    def test_earnings_period_before_distribution_remains_historical(self):
        result = worksheet_evidence.read_financial_inputs(self.run_dir, self.facts, '2025-01-01')
        self.assertEqual(result['after_tax_earnings']['tag'], 'historical')

    def test_saved_statement_must_match_the_xbrl_amount(self):
        self.facts['concepts']['net_income']['current']['val'] = 999
        result = worksheet_evidence.read_financial_inputs(self.run_dir, self.facts)
        self.assertNotIn('after_tax_earnings', result)

    def test_release_revenue_uses_only_explicit_total_revenue_line(self):
        source = self.run_dir / 'release.txt'
        source.write_text('Services revenue was $9 million.\nRevenue was $42 million.\n', encoding='utf-8')
        release = {'accession': '123', 'filing_date': '2025-01-31',
                   'documents': [{'accession': '123', 'url': 'https://www.sec.gov/release', 'path': source.name}]}
        result = worksheet_evidence.extract_release_facts(self.run_dir, release)
        self.assertEqual(result['revenue']['value'], '42000000')
        self.assertEqual(result['revenue']['line'], 2)

    def test_one_provider_request_and_no_added_numbers_in_judgment(self):
        response = Mock()
        response.json.return_value = {'choices': [{'message': {'content':
            '{"story":"Evidence is limited.","change":"Review the next filing."}'}}]}
        post = Mock(return_value=response)
        result = run_worksheet.model_judgment('key', 'model', 'persona', {'price': '10'}, post=post)
        self.assertEqual(result['story'], 'Evidence is limited.')
        self.assertEqual(post.call_count, 1)

    def test_information_statement_expected_and_completed_dates_are_distinct(self):
        accession = self.accession.replace('-', '')
        url = f'https://www.sec.gov/Archives/edgar/data/123/{accession}/ex991.htm'
        event_accession = '000000000025000002'
        event_url = f'https://www.sec.gov/Archives/edgar/data/123/{event_accession}/event.htm'
        source = self.run_dir / 'information.txt'
        source.write_text('INFORMATION STATEMENT\nShareholder letter\n', encoding='utf-8')
        event_source = self.run_dir / 'event.txt'
        event_source.write_text('Item 2.01\nThe distribution was completed.\n', encoding='utf-8')
        entity = {'parent': [{'value': 'Parent', 'filing': url, 'section': 'Shareholder letter',
                              'quote': 'The spin-off is expected to be completed on January 20, 2025.',
                              'filing_date': '2025-01-15'}],
                  'distribution_date': [{'value': '2025-01-21', 'filing': event_url,
                                         'section': 'Item 2.01', 'filing_date': '2025-01-22'}]}
        bundle = {'present': True, 'registry': entity, 'run': self.run_dir.resolve()}
        manifest = {'saved_source_documents': [
            {'accession': accession, 'url': url, 'path': source.name}],
            'distribution_filing_documents': [
                {'accession': event_accession, 'url': event_url, 'path': event_source.name}]}
        lines = run_worksheet.registry_lines(bundle, manifest)
        self.assertTrue(any('Parent: Parent | ' + url in line for line in lines))
        self.assertTrue(any('Distribution date: 2025-01-21 | ' + event_url + ' | Item 2.01' in line for line in lines))
        self.assertFalse(any('2025-01-20' in line for line in lines))

    def test_annual_statement_text_fills_missing_companyfacts(self):
        statement_dir = self.run_dir / 'worksheet_sources_test'
        statement_dir.mkdir()
        source = statement_dir / '10-12B_000000000025000003_ex99_1.txt'
        source.write_text(
            'The Sample Business\nCombined Statements of Operations\n'
            'For the Year Ended December 31,\n(In millions)\n2024\n2023\n'
            'Net income (loss)\n$\n100\n$\n90\n'
            'The Sample Business\nCombined Statements of Cash Flows\n'
            'For the Year Ended December 31,\n(In millions)\n2024\n2023\n'
            'Depreciation and amortization\n20\n19\nCapital expenditures\n(\n30\n)\n(\n25\n)\n',
            encoding='utf-8')
        facts = {'as_of': '2025-02-01', 'concepts': {
            'net_income': {'unit': 'USD', 'current': None},
            'depreciation_and_amortization': {'unit': 'USD', 'current': None},
            'additions_to_property_and_equipment': {'unit': 'USD', 'current': None},
            'diluted_shares_outstanding': {'unit': 'shares', 'current': None},
        }}
        result = worksheet_evidence.read_financial_inputs(self.run_dir, facts, '2025-01-01')
        self.assertEqual(result['after_tax_earnings']['value'], '100000000')
        self.assertEqual(result['depreciation']['value'], '20000000')
        self.assertEqual(result['capital_spending']['value'], '30000000')
        self.assertEqual(result['after_tax_earnings']['period'], 'FY2024 ended 2024-12-31')
        self.assertEqual(result['after_tax_earnings']['tag'], 'historical')

    def test_cover_page_common_share_count_is_sourced_and_dated(self):
        accession = '000000000025000004'
        source_dir = self.run_dir / 'worksheet_sources_cover'
        source_dir.mkdir()
        source = source_dir / f'first_post_spin_10-Q_{accession}_R1.htm.txt'
        source.write_text('Common Stock, Shares Outstanding\n667,303,030\n', encoding='utf-8')
        (source_dir / 'sources.json').write_text(json.dumps({'saved_source_documents': [
            {'path': str(source.relative_to(self.run_dir)), 'filing_date': '2025-01-31'}]}), encoding='utf-8')
        item = worksheet_evidence._cover_share_count(self.run_dir, '2025-01-20', '2025-02-01')
        self.assertEqual(item['value'], '667303030')
        self.assertEqual(item['tag'], 'reported after the spin')
        self.assertEqual(item['filing'], accession)

    def test_pipe_delimited_annual_statement_is_read(self):
        source = self.run_dir / 'company_10-K_000000000025000005.txt'
        source.write_text(
            'CONSOLIDATED STATEMENTS OF OPERATIONS\n'
            '(in millions)\nFiscal Year Ended March 31,\n'
            '2024 | | 2023\nNet loss | | $ | (298.2) | | | $ | (4.4)\n'
            'CONSOLIDATED STATEMENTS OF CASH FLOWS\n'
            '(in millions)\nFiscal Year Ended March 31,\n'
            '2024 | | 2023\nDepreciation | | 166.4 | | | 153.9\nPurchases of fixed assets | | $ | (162.8) | | | $ | (169.4)\n',
            encoding='utf-8')
        facts = {'as_of': '2025-02-01', 'concepts': {
            'net_income': {'unit': 'USD', 'current': None},
            'depreciation_and_amortization': {'unit': 'USD', 'current': None},
            'additions_to_property_and_equipment': {'unit': 'USD', 'current': None},
            'diluted_shares_outstanding': {'unit': 'shares', 'current': None},
        }}
        result = worksheet_evidence.read_financial_inputs(self.run_dir, facts)
        self.assertEqual(result['after_tax_earnings']['value'], '-298200000')
        self.assertEqual(result['capital_spending']['value'], '162800000')
        self.assertEqual(result['depreciation']['value'], '166400000')
        self.assertEqual(result['after_tax_earnings']['period'], 'FY2024 ended 2024-03-31')

    def test_common_cover_shares_are_not_diluted_shares(self):
        source = self.run_dir / 'first_post_spin_10-Q_000000000025000004_R1.txt'
        source.write_text('Common Stock, Shares Outstanding\n100\n', encoding='utf-8')
        result = worksheet_evidence.read_financial_inputs(self.run_dir, {'as_of': '2025-02-01', 'concepts': {}})
        self.assertNotIn('diluted_shares', result)
        self.assertEqual(result['common_shares']['value'], '100')

    def test_hook_finds_automatic_output_and_rejects_external_output(self):
        report = self.run_dir / 'worksheet.md'
        report.write_text('sample', encoding='utf-8')
        event = {'tool_response': {'output': f'Worksheet: {report}\n'}}
        self.assertEqual(worksheet_guard._automatic_worksheet(event, self.run_dir), report.resolve())
        outside = self.root / 'other.md'
        outside.write_text('sample', encoding='utf-8')
        with self.assertRaises(ValueError):
            worksheet_guard._automatic_worksheet({'tool_response': f'Worksheet: {outside}\n'}, self.run_dir)

    def test_pro_forma_financing_preserves_assumptions_and_amounts(self):
        accession = '000000000025000004'
        source = self.run_dir / 'registration.txt'
        source.write_text('UNAUDITED PRO FORMA CONSOLIDATED FINANCIAL STATEMENTS\n'
                          'principal indebtedness of an assumed amount equal to $2 billion, net of applicable debt issuance costs, and the expected distribution of an aggregate amount equal to $1 billion of cash to Former Parent, subject to adjustment.\n', encoding='utf-8')
        entity = {'parent': [{'filing': f'https://www.sec.gov/Archives/edgar/data/123/{accession}/f.htm', 'filing_date': '2025-01-01'}]}
        manifest = {'registration_accession': accession, 'saved_source_documents': [{'accession': accession, 'path': source.name, 'url': 'https://www.sec.gov/f.htm'}]}
        facts = worksheet_evidence.extract_financing_facts(self.run_dir, manifest, entity, '2025-02-01')
        self.assertEqual(facts['debt_raised']['value'], '2000000000')
        self.assertEqual(facts['cash_use']['value'], '1000000000')
        self.assertEqual(facts['debt_raised']['tag'], 'pro forma')
        self.assertIn('expected', facts['cash_use']['description'])

    def test_registry_form_ten_must_come_from_registry(self):
        row = {'form': '10-12B', 'accessionNumber': self.accession, 'filingDate': '2025-01-15'}
        self.assertIsNone(prepare_worksheet.choose_registration({}, [row], '123'))

    def test_pipeline_collects_registry_filing_then_writes_worksheet(self):
        accession = self.accession.replace('-', '')
        release = '000000000025000002'
        source_url = f'https://www.sec.gov/Archives/edgar/data/123/{accession}/ex991.htm'
        registry = {'0000000123': {'parent': [{'value': 'Parent', 'filing': source_url,
                     'section': 'Shareholder letter', 'quote': 'A spin was announced.',
                     'filing_date': '2025-01-15'}]}}
        self.registry.write_text(json.dumps(registry), encoding='utf-8')
        filings = {'filings': {'filing_list': [
            {'form': '10-12B', 'accessionNumber': self.accession, 'filingDate': '2025-01-15'},
            {'form': '8-K', 'accessionNumber': release, 'filingDate': '2025-01-31', 'items': '2.02'}]}}
        (self.run_dir / 'filings.json').write_text(json.dumps(filings), encoding='utf-8')
        self.env.write_text('PURDUE_API_KEY=test\nSEC_USER_AGENT=Example test@example.org\n', encoding='utf-8')
        submissions = {'filings': {'recent': {'accessionNumber': [release],
                       'acceptanceDateTime': ['2025-01-31T22:00:00+00:00']}, 'files': []}}
        client = Mock()
        client.get.return_value = json.dumps(submissions)
        def folder(_client, row):
            url = source_url if '10-12' in row['form'] else 'https://www.sec.gov/release.htm'
            return [{'url': url, 'text': '<html><body>INFORMATION STATEMENT</body></html>'}]
        judge = Mock(return_value={'story': 'Evidence is limited.', 'change': 'Review the next filing.'})
        with patch.object(prepare_worksheet.seeker, 'SecClient', return_value=client), \
             patch.object(prepare_worksheet.seeker, 'read_filing_folder', side_effect=folder):
            output = run_worksheet.run(self.args, judge=judge)
        text = output.read_text(encoding='utf-8')
        self.assertIn('Parent: Parent | ' + source_url, text)
        self.assertEqual(judge.call_count, 1)
        self.assertTrue(list(self.run_dir.glob('worksheet_sources_*/sources.json')))


if __name__ == '__main__':
    unittest.main()
