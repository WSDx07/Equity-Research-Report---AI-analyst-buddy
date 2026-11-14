import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

import prepare_worksheet


class Form4Tests(unittest.TestCase):
    def test_only_purchases_and_nested_values_are_read(self):
        xml = '''<ownershipDocument><nonDerivativeTable>
          <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-01-08</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts><transactionShares><value>125</value></transactionShares>
              <transactionPricePerShare><value>12.50</value></transactionPricePerShare>
            </transactionAmounts>
          </nonDerivativeTransaction>
          <nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode>
          </transactionCoding></nonDerivativeTransaction>
        </nonDerivativeTable></ownershipDocument>'''
        with patch.object(prepare_worksheet.seeker, 'submission_text_documents',
                          return_value={'ownership.xml': xml}):
            purchases = prepare_worksheet.parse_form4_purchases('filing', '123', '2026-01-09')
        self.assertEqual(len(purchases), 1)
        self.assertEqual(purchases[0]['transaction_code'], 'P')
        self.assertEqual(purchases[0]['transaction_date'], '2026-01-08')
        self.assertEqual(purchases[0]['shares'], '125')
        self.assertEqual(purchases[0]['price_per_share'], '12.50')
        self.assertEqual(purchases[0]['security_title'], 'Common Stock')

    def test_standalone_ownership_xml_is_parsed(self):
        xml = '''<ownershipDocument><nonDerivativeTransaction>
          <transactionDate><value>2026-10-02</value></transactionDate>
          <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
          <transactionAmounts><transactionShares><value>50</value></transactionShares></transactionAmounts>
        </nonDerivativeTransaction></ownershipDocument>'''
        purchases = prepare_worksheet.parse_form4_purchases(xml, '000122520826008498', '2026-10-05')
        self.assertEqual(len(purchases), 1)
        self.assertEqual(purchases[0]['transaction_code'], 'P')
        self.assertEqual(purchases[0]['shares'], '50')


class SecRowTests(unittest.TestCase):
    def test_sec_row_uses_dashed_accession_expected_by_edgar_folder_reader(self):
        row = prepare_worksheet.sec_row(
            '0002128626', '000119312526396054', '10-12B/A', '2026-09-21')
        self.assertEqual(row['path'], 'edgar/data/2128626/0001193125-26-396054.txt')
        self.assertEqual(
            prepare_worksheet.seeker.folder_url(row),
            'https://www.sec.gov/Archives/edgar/data/2128626/000119312526396054/')

    def test_document_form_label_is_safe_for_path_separators(self):
        with tempfile.TemporaryDirectory() as directory:
            record = prepare_worksheet.save_document(
                Path(directory), '000119312526396054', 'exhibit99.htm',
                '<p>statement</p>', 'https://www.sec.gov/example', '10-12B/A')
            path = Path(directory) / Path(record['path']).name
            self.assertTrue(path.is_file())
            self.assertNotIn('/', path.name)


if __name__ == '__main__':
    unittest.main()
