import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import worksheet_guard


ROOT = Path(__file__).resolve().parents[4]
RULES = ROOT / 'docs' / 'lab07_worksheet_rules.md'


class WorksheetGuardTests(unittest.TestCase):
    def test_visible_link_label_is_checked(self):
        self.assertEqual(worksheet_guard.visible_numbers('[Revenue 123](https://example.test/456)'), ['123'])
        self.assertEqual(worksheet_guard.visible_numbers('123 USD is the amount'), ['123'])
        self.assertEqual(worksheet_guard.visible_numbers('Amount 123million'), ['123'])
        self.assertEqual(worksheet_guard.visible_numbers('Value -4292742857.142857142857142857 USD'), ['-4292742857.142857142857142857'])
        self.assertEqual(worksheet_guard.visible_numbers('Source: https://example.test/123/10-Q/456'), [])

    def test_clean_and_changed_rule_and_filing_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / 'filing.txt').write_text('Debt 45\n', encoding='utf-8')
            worksheet = run / 'worksheet.md'
            clean = ('Low case discount rate: 0.10 [rule id=low_discount_rate]\n'
                     'Debt: 45 [filing file=filing.txt line=1 section=Debt tag=historical period=FY2025]\n')
            worksheet.write_text(clean, encoding='utf-8')
            self.assertEqual(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES), [])
            worksheet.write_text(clean.replace('Debt: 45', 'Debt: 46'), encoding='utf-8')
            issues = worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES)
            self.assertEqual(len(issues), 1)
            self.assertIn('line 2', issues[0])
            self.assertIn('Debt: 46', issues[0])

    def test_uncited_number_in_link_label_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            worksheet = Path(folder) / 'worksheet.md'
            worksheet.write_text('[Value 42](https://example.test/123)\n', encoding='utf-8')
            issues = worksheet_guard.validate_worksheet(worksheet, run=folder, rules_path=RULES)
            self.assertTrue(any('42' in issue for issue in issues))
            worksheet.write_text('Value 1e6 [rule id=low_growth_rate]\n', encoding='utf-8')
            self.assertTrue(any('scientific notation' in issue for issue in worksheet_guard.validate_worksheet(worksheet, run=folder, rules_path=RULES)))

    def test_saved_fact_requires_exact_xbrl_tag_period_and_accession(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            facts = {'concepts': {'net_income': {'tag': 'us-gaap:NetIncomeLoss',
                       'current': {'val': 100, 'end': '2025-12-31', 'fy': 2025, 'fp': 'FY', 'accn': '0001-25-000001', 'reporting_tag': 'historical'},
                       'prior': {'val': 90, 'end': '2024-12-31', 'fy': 2025, 'fp': 'FY', 'accn': '0001-25-000001', 'reporting_tag': 'historical'}}}}
            (run / 'facts.json').write_text(json.dumps(facts), encoding='utf-8')
            worksheet = run / 'worksheet.md'
            line = 'Income: 90 [fact concept=net_income period=FY2024 tag=historical xbrl_tag=us-gaap:NetIncomeLoss filing=0001-25-000001 section=Income]\n'
            worksheet.write_text(line, encoding='utf-8')
            self.assertEqual(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES), [])
            for changed in (line.replace('90', '91'), line.replace('tag=historical', 'tag=pro-forma'), line.replace('NetIncomeLoss', 'Assets'),
                            line.replace('FY2024', 'FY2025'), line.replace('0001-25-000001', '0001-25-000002')):
                worksheet.write_text(changed, encoding='utf-8')
                self.assertTrue(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES))

    def test_stop_without_state_emits_valid_json(self):
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps({'hook_event_name': 'Stop', 'session_id': 'no-test-session'}))), contextlib.redirect_stdout(output):
            worksheet_guard.hook_main()
        self.assertEqual(json.loads(output.getvalue()), {})

    def test_hook_recognizes_only_python_execution_of_writer_scripts(self):
        self.assertTrue(worksheet_guard._python_script_invocation(
            r"& '.\.venv\Scripts\python.exe' '.agents\skills\us-spinoff-worksheet\scripts\run_worksheet.py' --run sample",
            'run_worksheet.py'))
        self.assertTrue(worksheet_guard._python_script_invocation(
            r"python .agents/skills/us-spinoff-worksheet/scripts/save_worksheet.py --output sample.md",
            'save_worksheet.py'))
        self.assertFalse(worksheet_guard._python_script_invocation(
            r"Get-Content -LiteralPath '.agents\skills\us-spinoff-worksheet\scripts\run_worksheet.py'",
            'run_worksheet.py'))
        self.assertFalse(worksheet_guard._python_script_invocation(
            r"Select-String -Path run_worksheet.py -Pattern main",
            'run_worksheet.py'))

    def test_cash_flow_uses_printed_millions_and_capex_magnitude(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / 'filing.txt').write_text('575\n806\n(346\n', encoding='utf-8')
            suffix = 'file=filing.txt section=Statements tag=historical period=FY2025'
            worksheet = run / 'worksheet.md'
            text = (f'After-tax earnings: 575 USD millions [filing {suffix} line=1]\n'
                    f'Depreciation: 806 USD millions [filing {suffix} line=2]\n'
                    f'Capital spending: 346 USD millions [filing {suffix} line=3 sign=magnitude]\n'
                    'Owner cash flow: 1035000000 USD [calc id=owner_cash_flow]\n')
            worksheet.write_text(text, encoding='utf-8')
            self.assertEqual(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES), [])
            worksheet.write_text(text.replace('575 USD', '576 USD'), encoding='utf-8')
            self.assertEqual(len(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES)), 2)

    def test_filing_number_written_as_word(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / 'filing.txt').write_text('one share for each holder\n', encoding='utf-8')
            worksheet = run / 'worksheet.md'
            line = 'Shares distributed: 1 [filing file=filing.txt line=1 section=Distribution tag=historical period=FY2025 number_word=one]\n'
            worksheet.write_text(line, encoding='utf-8')
            self.assertEqual(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES), [])
            worksheet.write_text(line.replace('distributed: 1', 'distributed: 2'), encoding='utf-8')
            self.assertTrue(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES))

    def test_form4_checks_purchases_in_saved_xml(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            xml = ('<ownershipDocument><nonDerivativeTransaction>'
                   '<transactionDate><value>2025-01-02</value></transactionDate>'
                   '<transactionCoding><transactionCode>P</transactionCode></transactionCoding>'
                   '<transactionAmounts><transactionShares><value>12</value></transactionShares>'
                   '<transactionPricePerShare><value>3.5</value></transactionPricePerShare>'
                   '</transactionAmounts></nonDerivativeTransaction></ownershipDocument>')
            (run / 'filing.txt').write_text(xml, encoding='utf-8')
            worksheet = run / 'worksheet.md'
            line = 'Insider shares purchased: 12 shares [form4 file=filing.txt accession=123 date=2025-01-02 field=shares]\n'
            worksheet.write_text(line, encoding='utf-8')
            self.assertEqual(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES), [])
            worksheet.write_text(line.replace(': 12', ': 13'), encoding='utf-8')
            self.assertTrue(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES))
            (run / 'filing.txt').write_text(xml.replace('<transactionCode>P', '<transactionCode>G'), encoding='utf-8')
            worksheet.write_text(line, encoding='utf-8')
            self.assertTrue(worksheet_guard.validate_worksheet(worksheet, run=run, rules_path=RULES))

    def test_missing_writer_output_also_blocks_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            session = 'test-missing-writer-output'
            event = {'hook_event_name': 'PostToolUse', 'session_id': session, 'turn_id': 'turn',
                     'tool_input': {'command': 'python run_worksheet.py --run sample'}, 'tool_response': ''}
            output = io.StringIO()
            with patch.object(worksheet_guard.tempfile, 'gettempdir', return_value=folder):
                with patch('sys.stdin', io.StringIO(json.dumps(event))), contextlib.redirect_stdout(output):
                    worksheet_guard.hook_main()
                self.assertEqual(json.loads(output.getvalue())['decision'], 'block')
                output = io.StringIO()
                stop = {'hook_event_name': 'Stop', 'session_id': session, 'turn_id': 'turn'}
                with patch('sys.stdin', io.StringIO(json.dumps(stop))), contextlib.redirect_stdout(output):
                    worksheet_guard.hook_main()
                self.assertEqual(json.loads(output.getvalue())['decision'], 'block')


if __name__ == '__main__':
    unittest.main()
