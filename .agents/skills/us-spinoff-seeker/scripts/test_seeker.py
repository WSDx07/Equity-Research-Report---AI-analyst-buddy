import sys, unittest, tempfile, json
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import seeker

class Rules(unittest.TestCase):
    def test_regular_listing_verification_reads_issuer_filing_and_rejects_ambiguity(self):
        class Client:
            def __init__(self,text): self.text=text; self.calls=[]
            def get(self,url): self.calls.append(url); return self.text
        proof={'cik':'1','ticker':'TEST','ric':'TEST.N','exchange':'New York Stock Exchange',
               'listing_url':'https://www.sec.gov/Archives/edgar/data/1/000000000124000001/listing.htm','regular_way':True}
        client=Client('Our common stock will begin regular-way trading under the ticker TEST on the New York Stock Exchange.')
        self.assertTrue(seeker.verify_regular_listing(proof,client))
        self.assertEqual(len(client.calls),1)
        client.text='Our common stock will begin when-issued trading under the ticker TEST on the New York Stock Exchange.'
        self.assertFalse(seeker.verify_regular_listing(proof,client))
        client.text='Our common stock will not begin regular-way trading under the ticker TEST on the New York Stock Exchange.'
        self.assertFalse(seeker.verify_regular_listing(proof,client))
        proof['listing_url']='https://www.sec.gov/Archives/edgar/data/2/000000000124000001/listing.htm'
        self.assertFalse(seeker.verify_regular_listing(proof,client))

    def test_export_snapshot_uses_verified_export_and_dated_companyfacts(self):
        from closes_reader import WorkspaceExportReader
        with tempfile.TemporaryDirectory() as d:
            export=Path(d)/'prices.csv'
            export.write_text('day,close\n2024-01-03,10\n2024-01-04,8\n',encoding='utf-8')
            mapping={'ticker':'TEST','cik':'1','date':'day','close':'close','price_basis':'official_unadjusted','session':'regular','coverage_start':'2024-01-02','coverage_end':'2024-01-04'}
            reference={'ticker':'TEST','date':'2024-01-03','close':'10','url':'https://exchange.example/close'}
            reader=WorkspaceExportReader(export,mapping,reference)
            facts={'cik':1,'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'end':'2024-01-04','filed':'2024-01-04','form':'10-Q','accn':'0000000001-24-000001','val':100}]}}}}}
            class Client:
                def get(self,url): return json.dumps(facts)
            record={'cik':'1','distribution_date':seeker.fact('2024-01-02','filing','section')}
            snapshot=seeker.verified_export_snapshot(record,date(2024,1,4),reader,Client())
            self.assertEqual(snapshot['first']['date'],'2024-01-03')
            self.assertEqual(snapshot['last']['date'],'2024-01-04')
            self.assertEqual(snapshot['shares']['value'],100)
            result=seeker.enrich_factor_inputs(record,snapshot,date(2024,1,4))
            self.assertNotIn('weakness',result['factors'])  # Declared coverage is not proof of the first close.
            self.assertEqual(result['factors']['size'],800)
            with self.assertRaises(ValueError): seeker.verified_export_snapshot(record,date(2024,1,5),reader,Client())
            with self.assertRaises(TypeError): seeker.verified_export_snapshot(record,date(2024,1,4),object(),Client())

    def test_index_filters_form_types_and_dates(self):
        data = '10        Fictional One  0000000001 2024-02-01 edgar/data/1/0000000001-24-000001.txt\n10/A      Fictional One  0000000001 2024-02-02 edgar/data/1/0000000001-24-000002.txt\nCERT      Fictional One  0000000001 2024-02-03 edgar/data/1/0000000001-24-000003.txt\n8-K       Fictional One  0000000001 2024-02-04 edgar/data/1/0000000001-24-000004.txt\n4         Fictional One  0000000001 2024-02-05 edgar/data/1/0000000001-24-000005.txt'
        rows = seeker.parse_index(data)
        self.assertEqual([x['form'] for x in rows], ['10','10/A','CERT','8-K','4'])
        self.assertEqual(rows[0]['cik'], '0000000001')

    def test_registry_requires_filing_and_section_and_no_estimates(self):
        with self.assertRaises(ValueError): seeker.fact('2024-01-01', '', 'Distribution')
        with self.assertRaises(ValueError): seeker.fact('2024-01-01', 'filing', '')
        self.assertEqual(seeker.fact(None, '', ''), None)
        self.assertEqual(seeker.fact('2024-01-01', 'filing', 'Distribution')['value'], '2024-01-01')

    def test_drop_requires_evidence_and_later_reinstates(self):
        r = {'rejection': {'reason':'fund', 'filing':'f', 'date':'2024-01-01'}, 'spinoff_evidence': {'filing':'g', 'date':'2024-01-02'}}
        self.assertFalse(seeker.is_dropped(r))
        r['spinoff_evidence']['date']='2023-12-31'
        self.assertTrue(seeker.is_dropped(r))

    def test_stage_and_window_boundaries(self):
        self.assertEqual(seeker.stage({}, date(2024,2,1), 30), 'registered')
        self.assertEqual(seeker.stage({'listing': True}, date(2024,2,1), 30), 'listing approved')
        self.assertEqual(seeker.stage({'trading': True}, date(2024,2,1), 30), 'trading')
        self.assertEqual(seeker.stage({'trading':True,'distribution_date':seeker.fact('2024-01-02','f','s')},date(2024,2,1),30),'in its window')
        self.assertEqual(seeker.stage({'trading':True,'distribution_date':seeker.fact('2024-01-01','f','s')},date(2024,2,1),30),'past it')
        self.assertEqual(seeker.stage({'trading':True,'distribution_date':seeker.fact('2024-02-02','f','s')},date(2024,2,1),30),'trading')

    def test_first_close_excludes_date_and_when_issued(self):
        quotes=[{'date':'2024-01-02','close':8,'when_issued':True}, {'date':'2024-01-03','close':10,'when_issued':False,'basis':'official_unadjusted','source':'reader'},{'date':'2024-01-04','close':11,'when_issued':False,'basis':'official_unadjusted','source':'reader'}]
        self.assertEqual(seeker.first_close(quotes,'2024-01-02',coverage_start='2024-01-02',coverage_end='2024-01-04')['date'],'2024-01-03')
        self.assertIsNone(seeker.first_close([{'date':'2024-01-04','close':11}], '2024-01-02'))

    def test_first_close_needs_coverage_and_no_earlier_unclassified_row(self):
        good={'date':'2024-01-04','close':11,'when_issued':False,'basis':'official_unadjusted','source':'reader'}
        self.assertIsNone(seeker.first_close([good],'2024-01-02'))
        self.assertIsNone(seeker.first_close([good],'2024-01-02',coverage_start='2024-01-03',coverage_end='2024-01-04'))
        unknown={'date':'2024-01-03','close':10}
        self.assertIsNone(seeker.first_close([unknown,good],'2024-01-02',coverage_start='2024-01-02',coverage_end='2024-01-04'))
        self.assertIsNone(seeker.first_close([dict(good,close=float('inf'))],'2024-01-02',coverage_start='2024-01-02',coverage_end='2024-01-04'))
        self.assertIsNone(seeker.first_close([dict(good,basis='adjusted')],'2024-01-02',coverage_start='2024-01-02',coverage_end='2024-01-04'))
        self.assertIsNone(seeker.first_close([dict(good,source='')],'2024-01-02',coverage_start='2024-01-02',coverage_end='2024-01-04'))

    def test_rank_direction_weights_missing_and_ties(self):
        names=[{'name':'A','factors':{'x':1,'y':1}},{'name':'B','factors':{'x':2,'y':2}},{'name':'C','factors':{'x':3}}]
        cfg=[{'name':'x','weight':3,'direction':'higher','threshold':2}, {'name':'y','weight':1,'direction':'lower','threshold':1}]
        ranked, missing=seeker.rank(names,cfg)
        self.assertEqual(ranked[0]['name'],'B')
        self.assertEqual(ranked[0]['points'],{'x':3.0,'y':0.0})
        self.assertIn('y',missing[0]['reason'])

    def test_report_dates_blanks_dispositions_and_final_line(self):
        s=seeker.report(date(2024,2,1),'2024-01-31','2024-01-30',[],[],[{'name':'A','reason':'fund','filing':'url'}],['missing ratio'])
        self.assertIn('2024-02-01',s.splitlines()[0]); self.assertIn('2024-01-31',s.splitlines()[0]); self.assertIn('2024-01-30',s.splitlines()[0]); self.assertIn('fund',s); self.assertIn('url',s); self.assertIn('missing ratio',s)
        self.assertEqual(s.strip().splitlines()[-1],'screens, not recommendations')

    def test_forms_for_trading_only_include_requested_evidence(self):
        for form in ('10-Q','10-K','4'): self.assertTrue(seeker.proves_trading(form))
        for form in ('10','10/A','CERT','8-K'): self.assertFalse(seeker.proves_trading(form))

    def test_edgar_rate_and_agent_on_each_request(self):
        client=seeker.SecClient('Research test@example.test')
        self.assertLess(client.requests_per_second,10)
        self.assertEqual(client.headers['User-Agent'],'Research test@example.test')
        with self.assertRaises(ValueError): seeker.SecClient('')

    def test_index_cache_reuses_recent_index_and_refreshes_without_caching_filings(self):
        class SEC:
            def __init__(self): self.calls=[]
            def get(self,url): self.calls.append(url); return 'version-'+str(len(self.calls))
        clock=[1000.0]; index='https://www.sec.gov/Archives/edgar/full-index/2024/QTR1/form.idx'
        filing='https://www.sec.gov/Archives/edgar/data/123/filing.htm'
        with tempfile.TemporaryDirectory() as d:
            client=SEC(); cache=seeker.CachedIndexClient(client,Path(d),ttl=100,clock=lambda:clock[0])
            self.assertEqual(cache.get(index),'version-1')
            self.assertEqual(cache.get(index),'version-1')
            self.assertEqual(cache.get(filing),'version-2')
            self.assertEqual(cache.get(filing),'version-3')
            clock[0]=1101.0
            self.assertEqual(cache.get(index),'version-4')
            self.assertEqual(len(client.calls),4)

    def test_index_cache_does_not_cache_errors_or_follow_non_sec_urls(self):
        class SEC:
            def get(self,url): raise OSError('unavailable')
        with tempfile.TemporaryDirectory() as d:
            cache=seeker.CachedIndexClient(SEC(),Path(d),ttl=100,clock=lambda:1000.0)
            with self.assertRaises(OSError): cache.get('https://www.sec.gov/Archives/edgar/full-index/2024/QTR1/form.idx')
            self.assertEqual(list(Path(d).iterdir()),[])
            with self.assertRaises(ValueError): cache.get('https://outside.test/form.idx')

    def test_sec_document_decoding_preserves_common_encodings(self):
        self.assertEqual(seeker.decode_sec_text(b'plain \xe2\x80\x99',None),'plain \u2019')
        self.assertEqual(seeker.decode_sec_text(b'plain \x92',None),'plain \u2019')
        self.assertEqual(seeker.decode_sec_text(b'plain \x92','windows-1252'),'plain \u2019')
        with self.assertRaises(UnicodeError): seeker.decode_sec_text(b'plain \x81',None)

    def test_sec_redirects_are_not_followed_automatically(self):
        handler=seeker.NoAutomaticRedirects()
        self.assertIsNone(handler.redirect_request(None,None,302,'redirect',{},'https://elsewhere.test/'))
        client=seeker.SecClient('Research test@example.test')
        self.assertTrue(any(isinstance(h,seeker.NoAutomaticRedirects) for h in client.opener.handlers))
        with self.assertRaises(ValueError): client.get('https://elsewhere.test/filing')

    def test_config_requires_window_and_factors(self):
        with self.assertRaises(ValueError): seeker.validate_config({'window_days':30,'factors':[]})
        with self.assertRaises(ValueError): seeker.validate_config({'window_days':30,'factors':[{'name':'x','weight':1,'direction':'unknown'}]})
        seeker.validate_config({'window_days':30,'factors':[{'name':'x','weight':1,'direction':'higher','threshold':2}]})



class CoverageTests(unittest.TestCase):
    def test_rejection_without_reason_or_source_does_not_drop(self):
        self.assertFalse(seeker.is_dropped({'rejection':{'reason':'fund'}}))
    def test_first_close_does_not_accept_when_issued_or_unclassified(self):
        self.assertIsNone(seeker.first_close([{'date':'2024-01-02','close':5,'when_issued':False}], '2024-01-02'))
        self.assertIsNone(seeker.first_close([{'date':'2024-01-03','close':5,'when_issued':True}], '2024-01-02'))
    def test_rank_rejects_invalid_weights(self):
        for weight in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError): seeker.validate_config({'window_days':1,'factors':[{'name':'x','weight':weight,'direction':'higher'}]})
    def test_no_filing_date_is_used_as_distribution(self):
        self.assertEqual(seeker.stage({'trading':True,'filing_date':'2024-01-31'},date(2024,2,1),30),'trading')

class RealEdgarForms(unittest.TestCase):
    def test_form_10_registration_variants_and_amendments(self):
        data = '\n'.join(f'{form:<17} Fictional Co 123 2024-10-01 edgar/data/123/0000000123-24-000001.txt' for form in ['10-12B','10-12B/A','10-12G','10-12G/A','10-12B/A','10-K'])
        self.assertEqual([r['form'] for r in seeker.parse_index(data)], ['10-12B','10-12B/A','10-12G','10-12G/A','10-12B/A','10-K'])

    def test_zero_weight_removes_only_that_factors_points(self):
        items = [{'name':'A','factors':{'size':1,'weakness':30,'insiders':10}}, {'name':'B','factors':{'size':2,'weakness':5,'insiders':2}}, {'name':'C','factors':{'size':1,'weakness':30}}]
        factors=[{'name':'size','weight':3,'direction':'lower','threshold':1},{'name':'weakness','weight':5,'direction':'higher','threshold':20},{'name':'insiders','weight':4,'direction':'higher','threshold':5}]
        original,unranked=seeker.rank(items,factors)
        changed=[dict(f,weight=0) if f['name']=='insiders' else dict(f) for f in factors]
        new,new_unranked=seeker.rank(items,changed)
        self.assertEqual(len(unranked),1)
        self.assertEqual(len(new_unranked),0)
        before={x['name']:x['points'] for x in original}
        for row in new:
            self.assertNotIn('insiders',row['points'])
            if row['name'] in before:
                self.assertEqual(row['points']['size'],before[row['name']]['size'])
                self.assertEqual(row['points']['weakness'],before[row['name']]['weakness'])

class FilingFolderTests(unittest.TestCase):
    def test_filing_folder_url_removes_accession_dashes(self):
        row={'cik':'0000000123','path':'edgar/data/123/0000000123-24-000001.txt'}
        self.assertEqual(seeker.folder_url(row),'https://www.sec.gov/Archives/edgar/data/123/000000012324000001/')
    def test_folder_lists_relevant_documents(self):
        data='{"directory":{"item":[{"name":"info.htm"},{"name":"form10.htm"},{"name":"image.jpg"},{"name":"exhibit.xml"}]}}'
        self.assertEqual(seeker.filing_documents(data),['info.htm','form10.htm','exhibit.xml'])
    def test_bad_filing_path_is_rejected(self):
        with self.assertRaises(ValueError): seeker.folder_url({'cik':'0000000123','path':'edgar/data/123/../../bad.txt'})

    def test_discovery_reads_index_and_filing_folders(self):
        class FakeSEC:
            def __init__(self): self.urls=[]
            def get(self,url):
                self.urls.append(url)
                if url.endswith('form.idx'):
                    return 'Last Data Received:    December 31, 2024\n10-12B  Fictional Co 123 2024-10-01 edgar/data/123/0000000123-24-000001.txt\n'
                if url.endswith('index.json'): return '{"directory":{"item":[{"name":"statement.htm"}]}}'
                return '<html>Distribution statement</html>'
        client=FakeSEC()
        rows,index_date=seeker.discover_index(client,2024,4)
        self.assertEqual(index_date,'2024-12-31')
        docs=seeker.read_filing_folder(client,rows[0])
        self.assertEqual(len(docs),1)
        self.assertIn('Distribution statement',docs[0]['text'])
        self.assertTrue(any(x.endswith('index.json') for x in client.urls))

    def test_folder_download_error_is_not_an_empty_filing(self):
        class Broken:
            def get(self,url): raise OSError('unavailable')
        with self.assertRaises(OSError): seeker.read_filing_folder(Broken(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})

    def test_one_unreadable_document_does_not_discard_other_documents(self):
        class Partial:
            def get(self,url):
                if url.endswith('index.json'): return '{"directory":{"item":[{"name":"good.htm"},{"name":"bad.htm"}]}}'
                if url.endswith('bad.htm'): raise OSError('unavailable')
                return 'readable'
        docs=seeker.read_filing_folder(Partial(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertEqual(docs[0]['text'],'readable')
        self.assertIsNone(docs[1]['text'])
        self.assertTrue(docs[1]['error'])

    def test_filing_folder_uses_readable_documents_in_complete_submission(self):
        class SEC:
            def __init__(self): self.urls=[]
            def get(self,url):
                self.urls.append(url)
                if url.endswith('index.json'):
                    return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'},{'name':'form.htm'},{'name':'info.htm'},{'name':'image.jpg'}]}})
                if url.endswith('0000000123-24-000001.txt'):
                    return '<DOCUMENT>\n<TYPE>10-12B\n<FILENAME>form.htm\n<TEXT>\n<html>Registration</html>\n</TEXT>\n</DOCUMENT>\n<DOCUMENT>\n<TYPE>EX-99\n<FILENAME>info.htm\n<TEXT>\n<html>Information statement</html>\n</TEXT>\n</DOCUMENT>\n<DOCUMENT>\n<TYPE>GRAPHIC\n<FILENAME>image.jpg\n<TEXT>\nencoded binary\n</TEXT>\n</DOCUMENT>\n'
                raise AssertionError('Document should come from complete submission')
        client=SEC()
        docs=seeker.read_filing_folder(client,{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertEqual(len(client.urls),2)
        self.assertTrue(any(d['url'].endswith('info.htm') and 'Information statement' in d['text'] for d in docs if d.get('text')))
        self.assertTrue(any(d['url'].endswith('image.jpg') and d['text'] is None for d in docs))

    def test_complete_submission_retains_unlisted_embedded_document(self):
        class SEC:
            def get(self,url):
                if url.endswith('index.json'):
                    return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'},{'name':'form.htm'}]}})
                return ('<DOCUMENT>\n<TYPE>10-12B\n<FILENAME>form.htm\n<TEXT>\nRegistration\n</TEXT>\n</DOCUMENT>\n'
                        '<DOCUMENT>\n<TYPE>EX-99\n<FILENAME>unlisted.htm\n<TEXT>\nInformation statement\n</TEXT>\n</DOCUMENT>\n')
        docs=seeker.read_filing_folder(SEC(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        matches=[d for d in docs if d.get('text') and 'Information statement' in d['text']]
        self.assertEqual(len(matches),1)
        self.assertTrue(matches[0]['url'].endswith('0000000123-24-000001.txt'))
        self.assertEqual(matches[0]['embedded_filename'],'unlisted.htm')

    def test_single_complete_submission_is_not_silently_discarded(self):
        class SEC:
            def get(self,url):
                if url.endswith('index.json'): return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'}]}})
                return 'Information statement\nParent: Fictional Parent'
        docs=seeker.read_filing_folder(SEC(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertEqual(len(docs),1)
        self.assertIn('Information statement',docs[0]['text'])

    def test_only_submission_is_split_into_readable_documents_when_possible(self):
        class SEC:
            def get(self,url):
                if url.endswith('index.json'): return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'}]}})
                return '<DOCUMENT>\n<TYPE>EX-99\n<FILENAME>info.htm\n<TEXT>\n<html>Information statement</html>\n</TEXT>\n</DOCUMENT>\n'
        docs=seeker.read_filing_folder(SEC(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertEqual(len(docs),1)
        self.assertEqual(docs[0]['embedded_filename'],'info.htm')
        self.assertNotIn('<DOCUMENT>',docs[0]['text'])

    def test_unlisted_binary_in_complete_submission_is_an_explicit_gap(self):
        class SEC:
            def get(self,url):
                if url.endswith('index.json'): return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'}]}})
                return ('<DOCUMENT>\n<TYPE>10-12B\n<FILENAME>form.htm\n<TEXT>\nRegistration\n</TEXT>\n</DOCUMENT>\n'
                        '<DOCUMENT>\n<TYPE>EX-99\n<FILENAME>scan.pdf\n<TEXT>\nencoded data\n</TEXT>\n</DOCUMENT>\n')
        docs=seeker.read_filing_folder(SEC(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertTrue(any(d.get('text') is None and d.get('embedded_filename')=='scan.pdf' for d in docs))

    def test_filing_folder_downloads_missing_submission_document_individually(self):
        class SEC:
            def __init__(self): self.urls=[]
            def get(self,url):
                self.urls.append(url)
                if url.endswith('index.json'):
                    return json.dumps({'directory':{'item':[{'name':'0000000123-24-000001.txt'},{'name':'form.htm'},{'name':'info.htm'}]}})
                if url.endswith('0000000123-24-000001.txt'):
                    return '<DOCUMENT>\n<TYPE>10-12B\n<FILENAME>form.htm\n<TEXT>\nRegistration\n</TEXT>\n</DOCUMENT>\n'
                if url.endswith('info.htm'): return 'Information statement'
                raise AssertionError('unexpected download')
        client=SEC()
        docs=seeker.read_filing_folder(client,{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertTrue(any(d['url'].endswith('info.htm') and d.get('text')=='Information statement' for d in docs))
        self.assertTrue(any(url.endswith('info.htm') for url in client.urls))

    def test_undecodable_document_does_not_discard_other_readable_documents(self):
        class Partial:
            def get(self,url):
                if url.endswith('index.json'): return '{"directory":{"item":[{"name":"bad.htm"},{"name":"good.htm"}]}}'
                if url.endswith('bad.htm'): raise UnicodeDecodeError('utf-8',b'\xff',0,1,'invalid')
                return 'readable'
        docs=seeker.read_filing_folder(Partial(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertIsNone(docs[0]['text'])
        self.assertEqual(docs[1]['text'],'readable')

    def test_unsupported_attachment_is_reported_as_unreadable(self):
        class SEC:
            def get(self,url):
                if url.endswith('index.json'): return '{"directory":{"item":[{"name":"form.htm"},{"name":"exhibit.jpg"}]}}'
                return 'Registration'
        docs=seeker.read_filing_folder(SEC(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertTrue(any(d['url'].endswith('exhibit.jpg') and d['text'] is None for d in docs))

    def test_unreadable_pdf_is_a_gap_not_proof_an_information_statement_is_absent(self):
        class PDF:
            def get(self,url):
                if url.endswith('index.json'): return '{"directory":{"item":[{"name":"form.htm"},{"name":"exhibit.pdf"}]}}'
                return 'readable'
        docs=seeker.read_filing_folder(PDF(),{'cik':'123','path':'edgar/data/123/0000000123-24-000001.txt'})
        self.assertTrue(any(d['url'].endswith('exhibit.pdf') and d['text'] is None for d in docs))

class RegistryTests(unittest.TestCase):
    def test_each_screen_gets_a_unique_registry_path(self):
        with tempfile.TemporaryDirectory() as d:
            first=seeker.new_registry_path(Path(d))
            second=seeker.new_registry_path(Path(d))
            self.assertNotEqual(first,second)
            self.assertTrue(first.name.startswith('registry-'))
            self.assertEqual(first.suffix,'.json')

    def test_registry_flush_retries_a_transient_windows_replace_lock(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'registry.json'
            registry=seeker.Registry(path,autosave=False)
            registry.ensure_entity('123')
            replace=seeker.os.replace
            calls=[]
            def transient(source,destination):
                calls.append((source,destination))
                if len(calls)==1: raise PermissionError('simulated file lock')
                return replace(source,destination)
            with patch.object(seeker.os,'replace',side_effect=transient), patch.object(seeker.time,'sleep'):
                registry.flush()
            self.assertEqual(len(calls),2)
            self.assertTrue(path.exists())
            self.assertFalse(registry.dirty)

    def test_registry_initializes_missing_fields_and_can_flush_a_batch(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'registry.json'; registry=seeker.Registry(path,autosave=False)
            registry.ensure_entity('123')
            self.assertFalse(path.exists())
            registry.record('123','parent',seeker.fact('Fictional Parent','f','Parent'))
            registry.flush()
            loaded=seeker.Registry(path)
            entity=loaded.data['0000000123']
            for key in ('parent','parent_cik','distribution_ratio','record_date','distribution_date'):
                self.assertIn(key,entity)
            self.assertEqual(entity['record_date'],[])
            self.assertEqual(loaded.resolved('123','parent'),'Fictional Parent')
            loaded.ensure_entity('123')
            self.assertEqual(loaded.resolved('123','parent'),'Fictional Parent')

    def test_store_only_sourced_fact_and_preserve_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'registry.json'
            registry=seeker.Registry(path)
            registry.record('123','distribution_date',seeker.fact('2024-03-01','https://www.sec.gov/Archives/f1','Distribution'))
            registry.record('123','distribution_date',seeker.fact('2024-03-02','https://www.sec.gov/Archives/f2','Distribution'))
            registry.record('123','record_date',None)
            loaded=seeker.Registry(path)
            self.assertEqual(len(loaded.data['0000000123']['distribution_date']),2)
            self.assertIsNone(loaded.resolved('123','distribution_date'))
            self.assertIsNone(loaded.resolved('123','record_date'))
            self.assertEqual(loaded.conflicts('123'),['distribution_date'])

    def test_registry_as_of_ignores_future_and_undated_filing_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            registry=seeker.Registry(Path(d)/'registry.json')
            registry.record('123','parent',dict(seeker.fact('Fictional Old','f1','Parent'),filing_date='2024-01-01'))
            registry.record('123','parent',dict(seeker.fact('Fictional New','f2','Parent'),filing_date='2024-02-01'))
            registry.record('123','parent',seeker.fact('Undated','f3','Parent'))
            self.assertIsNone(registry.resolved('123','parent'))
            self.assertEqual(registry.resolved('123','parent',as_of=date(2024,1,15)),'Fictional Old')
            self.assertEqual(registry.evidence('123','parent',as_of=date(2024,1,15))['filing'],'f1')
            self.assertEqual(registry.conflicts('123',as_of=date(2024,1,15)),[])
            self.assertEqual(registry.conflicts('123',as_of=date(2024,3,1)),['parent'])

    def test_fact_missing_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            registry=seeker.Registry(Path(d)/'registry.json')
            with self.assertRaises(ValueError): registry.record('123','parent',{'value':'X','filing':'','section':'Distribution'})

    def test_report_prints_parent_window_prices_and_factor_points(self):
        ranked=[{'name':'Example','parent':'Parent','distribution_date':'2024-01-01','window_ends':'2024-03-31',
                 'first_close':{'close':'50.00','date':'2024-01-02'},'latest_close':{'close':'9.25','date':'2024-03-20'},'total':12.0,'points':{'size':5.0,'weakness':7.0}}]
        s=seeker.report(date(2024,3,21),'2024-03-20','2024-03-20',ranked,[],[],[])
        for part in ('Example','Parent','2024-01-01','2024-03-31','9.25','2024-03-20','size: 5.00','weakness: 7.00'):
            self.assertIn(part,s)
        self.assertEqual(s.strip().splitlines()[-1],'screens, not recommendations')
        self.assertNotIn('50.00',s)

    def test_ranked_report_preserves_filing_sources_for_material_facts(self):
        records=[{'name':'Fictional','trading':True,'parent':dict(seeker.fact('Parent','https://www.sec.gov/Archives/parent.htm','Letter'),filing_date='2023-12-01'),'distribution_date':dict(seeker.fact('2024-01-01','https://www.sec.gov/Archives/event.htm','Item 2.01'),filing_date='2024-01-02'),'factors':{'x':1}}]
        ranked,watch,missing=seeker.prepare_screen(records,'2024-01-01',date(2024,1,10),90,[{'name':'x','weight':1,'direction':'higher','threshold':1}])
        report=seeker.report(date(2024,1,10),None,'2024-01-09',ranked,watch,[],[])
        self.assertIn('https://www.sec.gov/Archives/parent.htm (Letter)',report)
        self.assertIn('https://www.sec.gov/Archives/event.htm (Item 2.01)',report)
        self.assertIn('filed 2023-12-01',report)
        self.assertIn('filed 2024-01-02',report)

    def test_report_includes_available_calculation_explanations(self):
        ranked=[{'name':'Example','total':25,'points':{'size':25},'factor_explanations':{'size':'100 shares times USD 8 per share on 2024-01-10 = USD 800; filing (Shares).'}}]
        text=seeker.report(date(2024,3,21),None,None,ranked,[],[],[])
        self.assertIn('100 shares times USD 8 per share on 2024-01-10 = USD 800; filing (Shares).',text)

    def test_missing_parent_or_dates_are_not_invented(self):
        ranked=[{'name':'Example','total':0,'points':{}}]
        s=seeker.report(date(2024,3,21),None,None,ranked,[],[],[])
        self.assertIn('parent: unavailable',s)
        self.assertIn('distribution: unavailable',s)
        self.assertIn('window ends: unavailable',s)

class FilingEvidenceTests(unittest.TestCase):
    def test_only_explicit_labels_are_parsed_with_source_and_section(self):
        text='Distribution details\nParent: Fictional Holdings\nParent CIK: 123\nDistribution ratio: one share for every two shares\nRecord date: January 12, 2024\nDistribution date: January 20, 2024'
        result=seeker.extract_labeled_facts(text,'https://www.sec.gov/Archives/filing.htm')
        self.assertEqual(result['record_date']['value'],'2024-01-12')
        self.assertEqual(result['distribution_date']['value'],'2024-01-20')
        self.assertEqual(result['parent']['value'],'Fictional Holdings')
        self.assertEqual(result['parent_cik']['value'],'0000000123')
        for entry in result.values():
            self.assertTrue(entry['filing']); self.assertTrue(entry['section']); self.assertTrue(entry['quote'])

    def test_information_statement_letter_extracts_sourced_facts_without_claiming_completion(self):
        text=('Information statement\nDear Fictional Parent Company Shareholder:\n'
              'On July 26, 2022, Fictional Parent Company ("FP") announced its plan to separate its business. '
              'The separation will occur through a pro rata distribution by FP of shares of a newly formed company, Fictional Newco Corporation ("FN"). '
              'Each FP shareholder as of the close of business on March 18, 2024, the record date for the distribution, '
              'will receive one share of FN common stock for every four shares of FP common stock held by such shareholder.')
        result=seeker.extract_letter_facts(text,'https://www.sec.gov/Archives/info.htm','Fictional Newco Corp')
        self.assertEqual(result['parent'][0]['value'],'Fictional Parent Company')
        self.assertEqual(result['record_date'][0]['value'],'2024-03-18')
        self.assertIn('one share',result['distribution_ratio'][0]['value'])
        self.assertNotIn('distribution_date',result)
        self.assertTrue(all(e['section']=='Shareholder letter' for v in result.values() for e in v))
        self.assertEqual(seeker.extract_letter_facts(text,'f','Another Company'),{})
        self.assertEqual(seeker.extract_letter_facts(text.replace('distribution by FP','sale by FP'),'f','Fictional Newco Corp'),{})

    def test_completed_parent_8k_extracts_distribution_date_from_sourced_context(self):
        text=('Item 2.01. Completion of Acquisition or Disposition of Assets\n'
              'On April 1, 2024, Fictional Parent Company completed the separation through the distribution of common stock of Fictional Newco Corporation to its stockholders.')
        result=seeker.completed_distribution_date(text,'https://www.sec.gov/Archives/event.htm','Fictional Parent Co','Fictional Newco Corp')
        self.assertEqual(result['value'],'2024-04-01')
        self.assertEqual(result['section'],'Item 2.01')
        self.assertEqual(result['filing'],'https://www.sec.gov/Archives/event.htm')
        self.assertIsNone(seeker.completed_distribution_date(text.replace('completed','did not complete'),'f','Fictional Parent Co','Fictional Newco Corp'))
        self.assertIsNone(seeker.completed_distribution_date(text.replace('Fictional Newco Corporation','Other Corporation'),'f','Fictional Parent Co','Fictional Newco Corp'))
        self.assertIsNone(seeker.completed_distribution_date(text.replace('Item 2.01.','Item 9.01.'),'f','Fictional Parent Co','Fictional Newco Corp'))

    def test_information_statement_stockholder_letter_extracts_facts(self):
        text=('Information statement. Dear FP Stockholder: On October 1, 2023, we announced that our board approved a plan to separate Fictional Parent, Inc. ("FP") into two independent companies through the separation of our business into an independent, publicly traded company, Fictional Newco Inc. ("FN"), and the distribution to FP stockholders of all of the then issued and outstanding shares of common stock of FN. '
              'Each FP stockholder will receive one share of FN common stock on the date of the distribution for every share of FP common stock held as of the close of business on September 24, 2024, the record date for the distribution.')
        facts=seeker.extract_separation_letter_facts(text,'https://www.sec.gov/Archives/info.htm','Fictional Newco Inc')
        self.assertEqual(facts['parent'][0]['value'],'Fictional Parent, Inc.')
        self.assertEqual(facts['record_date'][0]['value'],'2024-09-24')
        self.assertIn('one share',facts['distribution_ratio'][0]['value'])
        self.assertNotIn('distribution_date',facts)
        self.assertEqual(seeker.extract_separation_letter_facts(text,'f','Unrelated Newco Inc'),{})
        self.assertEqual(seeker.extract_separation_letter_facts(text.replace('distribution to FP stockholders','sale to FP stockholders'),'f','Fictional Newco Inc'),{})

    def test_completed_distribution_in_incorporated_introductory_note(self):
        text=('Introductory Note. At 12:03 a.m., New York City time, on October 1, 2024 (the "Effective Time"), Fictional Parent Inc. ("FP") completed its previously announced separation into two publicly traded companies through the separation of its business into an independent company, Fictional Newco Inc. (the "Company"). '
              'The Separation was effected through a pro rata distribution of all outstanding shares of common stock of the Company to holders of common stock of FP as of September 24, 2024. '
              'Item 2.01. Completion of Acquisition or Disposition of Assets. The information set forth in the Introductory Note of this Current Report on Form 8-K is incorporated by reference into this Item 2.01.')
        result=seeker.completed_distribution_date(text,'f','Fictional Parent Inc','Fictional Newco Inc')
        self.assertEqual(result['value'],'2024-10-01')
        self.assertIn('Introductory Note',result['section'])
        self.assertIsNone(seeker.completed_distribution_date(text.replace('completed its','did not complete its'),'f','Fictional Parent Inc','Fictional Newco Inc'))
        self.assertIsNone(seeker.completed_distribution_date(text.replace('Fictional Newco Inc.','Other Newco Inc.'),'f','Fictional Parent Inc','Fictional Newco Inc'))
        self.assertIsNone(seeker.completed_distribution_date(text.replace('incorporated by reference','not incorporated by reference'),'f','Fictional Parent Inc','Fictional Newco Inc'))

    def test_ambiguous_or_absent_information_stays_blank(self):
        result=seeker.extract_labeled_facts('The transaction is anticipated in early 2025.','https://www.sec.gov/Archives/f.htm')
        self.assertEqual(result,{})
        result=seeker.extract_labeled_facts('Distribution date: To be announced','https://www.sec.gov/Archives/f.htm')
        self.assertNotIn('distribution_date',result)

    def test_overlapping_evidence_is_not_silently_selected(self):
        result=seeker.extract_labeled_facts('Distribution date: January 1, 2024\nDistribution date: January 2, 2024','https://www.sec.gov/Archives/f.htm')
        self.assertNotIn('distribution_date',result)

    def test_html_text_keeps_explicit_labels_and_ignores_script_content(self):
        text=seeker.html_text('<html><p>Parent: Fictional Holdings</p><script>Distribution date: 2024-01-01</script><p>Distribution date: 2024-01-02</p></html>')
        facts=seeker.extract_labeled_facts(text,'f')
        self.assertEqual(facts['parent']['value'],'Fictional Holdings')
        self.assertEqual(facts['distribution_date']['value'],'2024-01-02')

class ClassificationTests(unittest.TestCase):
    def test_rejections_need_filing_evidence_and_complete_review(self):
        self.assertIsNone(seeker.rejection_from_evidence({'kind':'fund'}))
        self.assertIsNone(seeker.rejection_from_evidence({'kind':'no information statement','filing':'f','complete':False}))
        self.assertEqual(seeker.rejection_from_evidence({'kind':'no information statement','filing':'f','complete':True})['reason'],'no information statement')
        self.assertEqual(seeker.rejection_from_evidence({'kind':'fund','filing':'f','section':'Registrant','complete':True})['reason'],'fund')
        self.assertEqual(seeker.rejection_from_evidence({'kind':'already owned shares','filing':'f','section':'Registration','complete':True})['reason'],'already owned shares')
        self.assertIsNone(seeker.rejection_from_evidence({'kind':'fund','filing':'f','complete':True}))

    def test_no_spinoff_claim_from_word_alone(self):
        self.assertFalse(seeker.distribution_statement('The term spinoff appears here.', 'Fictional Parent','Fictional Newco'))
        self.assertTrue(seeker.distribution_statement('Fictional Parent will distribute shares of Fictional Newco to its shareholders.', 'Fictional Parent','Fictional Newco'))
        self.assertFalse(seeker.distribution_statement('Fictional Parent may not distribute shares of Fictional Newco to shareholders.', 'Fictional Parent','Fictional Newco'))
        self.assertFalse(seeker.distribution_statement('Fictional Parent will distribute shares of another entity to shareholders.', 'Fictional Parent','Fictional Newco'))

    def test_distribution_name_matching_accepts_legal_suffix_but_not_other_names(self):
        text='Fictional Parent Company completed the separation through the distribution of common stock of Fictional Newco Corporation to its stockholders.'
        self.assertTrue(seeker.distribution_statement(text,'Fictional Parent Co','Fictional Newco Corp'))
        self.assertFalse(seeker.distribution_statement(text,'Different Parent Co','Fictional Newco Corp'))
        self.assertFalse(seeker.distribution_statement(text,'Fictional Parent Co','Different Newco Corp'))

    def test_completed_parent_distribution_statement_requires_both_companies_and_holders(self):
        line='On April 1, 2024, Fictional Parent completed the separation through the pro rata distribution of 80.1% of the issued shares of common stock of Fictional Newco to Fictional Parent stockholders.'
        self.assertTrue(seeker.distribution_statement(line,'Fictional Parent','Fictional Newco'))
        self.assertFalse(seeker.distribution_statement(line.replace('Fictional Newco','Other Business'),'Fictional Parent','Fictional Newco'))
        self.assertFalse(seeker.distribution_statement(line.replace('completed','did not complete'),'Fictional Parent','Fictional Newco'))

    def test_complete_registration_with_no_information_statement_is_dropped(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Registration document with no exhibit.'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertEqual(rec['rejection']['reason'],'no information statement')
            self.assertIn('/edgar/data/123/',rec['rejection']['filing'])
            self.assertTrue(seeker.is_dropped(rec))

    def test_incomplete_registration_is_not_dropped_for_missing_information_statement(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Registration'}, {'url':'https://www.sec.gov/Archives/exhibit.pdf','text':None,'error':'unreadable'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertFalse(seeker.is_dropped(rec))
            self.assertTrue(any('exhibit.pdf' in gap for gap in gaps))

    def test_fund_registration_expressly_electing_bdc_is_sourced(self):
        rows=[{'form':'10-12G','cik':'0000000123','date':'2024-01-01','name':'Fictional Fund','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Fictional Fund is filing this registration statement with the authorities\nunder the applicable statute to permit it to file an election to be regulated as a business\ndevelopment company under the Investment Company Act.'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertEqual(rec['rejection']['reason'],'fund')
            self.assertEqual(rec['rejection']['filing'],docs[0]['url'])

    def test_fund_and_existing_share_registration_require_a_sourced_statement(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        cases=[('The registrant is a registered investment company.','fund'),('This filing is registering shares already owned by selling stockholders.','already owned shares')]
        for statement,expected in cases:
            docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':statement}]
            with self.subTest(kind=expected), tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
                rec,_=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
                self.assertEqual(rec['rejection']['reason'],expected)
                self.assertEqual(rec['rejection']['filing'],docs[0]['url'])

    def test_registration_of_shares_already_owned_by_registrant_is_sourced(self):
        rows=[{'form':'10-12G','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'The registrant is registering shares that it already owns.'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,_=seeker.inspect_candidate(None,'123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertEqual(rec['rejection']['reason'],'already owned shares')
            self.assertEqual(rec['rejection']['filing'],docs[0]['url'])

    def test_negated_bdc_election_is_not_classified_as_a_fund(self):
        row={'form':'10-12G','cik':'0000000123','date':'2024-01-01','name':'Fictional Fund','path':'edgar/data/123/0000000123-24-000001.txt'}
        text='Information statement\nFictional Fund is filing this registration statement not to permit it to file an election to be regulated as a business development company.'
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[{'url':'https://www.sec.gov/Archives/form.htm','text':text}]), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',[row],seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertFalse(seeker.is_dropped(rec))

    def test_negated_or_conditional_classification_is_not_a_fact(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement\nThis filing is not registering shares already owned by selling stockholders.'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,_=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertFalse(seeker.is_dropped(rec))

class ScreenPreparationTests(unittest.TestCase):
    def test_companyfacts_request_uses_ten_digit_cik_on_sec_host(self):
        class Fake:
            def __init__(self): self.urls=[]
            def get(self,url): self.urls.append(url); return '{"cik":123,"facts":{}}'
        client=Fake()
        self.assertEqual(seeker.fetch_companyfacts(client,'123')['cik'],123)
        self.assertEqual(client.urls,['https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json'])
        with self.assertRaises(ValueError): seeker.fetch_companyfacts(client,'123/other')

    def test_shares_require_exact_price_day_sourced_filing_and_no_conflict(self):
        good={'end':'2024-01-10','filed':'2024-01-10','form':'10-Q','accn':'0000000123-24-000001','val':100}
        def document(values): return {'cik':123,'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':values}}}}}
        fact=seeker.shares_from_companyfacts(document([good]),'123','2024-01-10')
        self.assertEqual(fact['value'],100)
        self.assertEqual(fact['as_of'],'2024-01-10')
        self.assertEqual(fact['filing_date'],'2024-01-10')
        self.assertIn('dei:EntityCommonStockSharesOutstanding',fact['section'])
        self.assertIn('0000000123-24-000001.txt',fact['filing'])
        self.assertIsNone(seeker.shares_from_companyfacts(document([dict(good,end='2024-01-09')]),'123','2024-01-10'))
        self.assertIsNone(seeker.shares_from_companyfacts(document([dict(good,filed='2024-01-11')]),'123','2024-01-10'))
        self.assertIsNone(seeker.shares_from_companyfacts(document([good,dict(good,val=101)]),'123','2024-01-10'))
        self.assertIsNone(seeker.shares_from_companyfacts(document([dict(good,val=True)]),'123','2024-01-10'))
        self.assertIsNone(seeker.shares_from_companyfacts(document([good]),'999','2024-01-10'))

    def test_sourced_insider_statement_requires_exact_group_percentage_and_date(self):
        text=('Security ownership of certain beneficial owners and management. '
              'As of January 5, 2024, our directors and executive officers as a group beneficially owned 6.5% of our outstanding common stock.')
        facts=seeker.extract_insider_statements(text,'https://www.sec.gov/Archives/filing.htm','2024-01-08')
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]['value'],'6.5')
        self.assertEqual(facts[0]['as_of'],'2024-01-05')
        self.assertEqual(facts[0]['filing_date'],'2024-01-08')
        self.assertIn('beneficial owners',facts[0]['section'].lower())
        self.assertEqual(seeker.extract_insider_statements(text.replace('beneficially owned','are expected to beneficially own'),'f','2024-01-08'),[])
        self.assertEqual(seeker.extract_insider_statements(text.replace('6.5%','less than 1%'),'f','2024-01-08'),[])
        self.assertEqual(seeker.extract_insider_statements(text,'f','2024-01-04'),[])

    def test_latest_insider_statement_is_dated_and_conflicts_stay_unavailable(self):
        a={'value':'6.5','as_of':'2024-01-05','filing_date':'2024-01-08','filing':'f','section':'Ownership'}
        b=dict(a,value='7',filing='g')
        self.assertEqual(seeker.select_insider_statement([a],'2024-01-10')['value'],'6.5')
        self.assertIsNone(seeker.select_insider_statement([a,b],'2024-01-10'))
        self.assertIsNone(seeker.select_insider_statement([dict(a,filing_date='2024-01-11')],'2024-01-10'))

    def test_factor_inputs_use_sourced_shares_and_dated_regular_closes(self):
        first={'date':'2024-01-02','close':'10','when_issued':False,'source':'price export','basis':'official_unadjusted','verified_first':True}
        last={'date':'2024-01-10','close':'8','when_issued':False,'source':'price export','basis':'official_unadjusted'}
        shares={'value':'100','filing':'filing','section':'Shares','as_of':'2024-01-10','filing_date':'2024-01-10'}
        insiders={'value':'5','filing':'filing','section':'Ownership','as_of':'2024-01-05','filing_date':'2024-01-05'}
        factors,formulas=seeker.factor_inputs('2024-01-01',first,last,shares,insiders)
        self.assertEqual(factors,{'size':800.0,'weakness':20.0,'insiders':5.0})
        self.assertIn('100',formulas['size'])
        self.assertIn('8',formulas['size'])
        self.assertIn('filing',formulas['insiders'])
        self.assertIn('2024-01-10',formulas['size'])
        factors,_=seeker.factor_inputs('2024-01-01',first,dict(last,basis='adjusted'),shares,insiders)
        self.assertEqual(factors,{})
        factors,_=seeker.factor_inputs('2024-01-01',first,last,dict(shares,filing_date='2024-01-11'),dict(insiders,filing_date='2024-01-11'))
        self.assertEqual(factors,{'weakness':20.0})

    def test_factor_inputs_never_replace_missing_or_invalid_data_with_zero(self):
        first={'date':'2024-01-01','close':'10','when_issued':False,'source':'p','basis':'official_unadjusted'}
        last={'date':'2024-01-10','close':'8','when_issued':False,'source':'p','basis':'official_unadjusted'}
        factors,_=seeker.factor_inputs('2024-01-01',first,last,None,None)
        self.assertEqual(factors,{})

    def test_stale_share_count_does_not_become_current_market_cap(self):
        first={'date':'2024-01-02','close':'10','when_issued':False,'source':'p','basis':'official_unadjusted','verified_first':True}
        last={'date':'2024-01-10','close':'8','when_issued':False,'source':'p','basis':'official_unadjusted'}
        shares={'value':'100','filing':'f','section':'s','as_of':'2024-01-05','filing_date':'2024-01-05'}
        factors,_=seeker.factor_inputs('2024-01-01',first,last,shares,None)
        self.assertNotIn('size',factors)
        first['date']='2024-01-02'; first['when_issued']=True
        factors,_=seeker.factor_inputs('2024-01-01',first,last,None,None)
        self.assertEqual(factors,{})

    def test_normal_cli_runs_and_saves_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'x','weight':1,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\n',encoding='utf-8')
            result={'ranked':[],'watch':[],'dropped':[],'limitations':[],'index_date':'2024-03-01'}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d]
            with patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result): seeker.main()
            self.assertEqual(len(list(root.glob('spinoff-screen-*.md'))),1)

    def test_lseg_live_provider_uses_first_close_strictly_after_distribution(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Discovery:
            class Views: EQUITY_QUOTES='equities'
            def search(self,**kwargs): return Frame([{'TickerSymbol':'TEST','RIC':'TEST.N','IsPrimaryRIC':True,'AssetState':'AC','ExchangeName':'Example'}])
        class Workspace:
            def __init__(self): self.discovery=Discovery()
            def get_data(self,**kwargs): return Frame([{'Date':'2024-01-02','Close Price':'9'},{'Date':'2024-01-03','Close Price':'10'},{'Date':'2024-01-04','Close Price':'8'}])
        record={'cik':'1','distribution_date':seeker.fact('2024-01-02','filing','section')}
        data={'x':{'cik_str':1,'ticker':'TEST'}}
        with patch('closes_reader.completed_close_end',return_value='2024-01-04'), patch.object(seeker,'fetch_companyfacts',return_value={}):
            snapshot=seeker.WorkspaceLiveProvider(Workspace(),None,data)(record,date(2024,1,4))
        self.assertEqual(snapshot['first']['date'],'2024-01-03')
        self.assertEqual(snapshot['last']['date'],'2024-01-04')
        self.assertTrue(snapshot['first']['verified_first'])
        scored=seeker.enrich_factor_inputs(record,snapshot,date(2024,1,4))
        self.assertEqual(scored['factors']['weakness'],20)

    def test_explicit_partial_cli_saves_dated_report_with_limitations(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'size','weight':10,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\n',encoding='utf-8')
            result={'ranked':[],'watch':[],'dropped':[],'limitations':['fictional source unavailable'],'index_date':'2024-03-01'}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d,'--partial']
            with patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result): seeker.main()
            reports=list(root.glob('spinoff-screen-*.md'))
            self.assertEqual(len(reports),1)
            content=reports[0].read_text(encoding='utf-8')
            self.assertIn('PARTIAL',content)
            self.assertIn('fictional source unavailable',content)
            self.assertIn('not connected to a verified live reader',content)
            self.assertNotIn('No official price source has been verified against an exchange',content)
            self.assertEqual(content.strip().splitlines()[-1],'screens, not recommendations')
    def test_partial_cli_propagates_actual_screen_price_date(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'x','weight':1,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\n',encoding='utf-8')
            row={'name':'Fictional','points':{'x':1},'total':1,'latest_close':{'date':'2024-03-01','close':'8'}}
            result={'ranked':[row],'watch':[],'dropped':[],'limitations':[],'index_date':'2024-03-01','price_date':'2024-03-01'}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d,'--partial']
            with patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result): seeker.main()
            content=next(root.glob('spinoff-screen-*.md')).read_text(encoding='utf-8')
            self.assertIn('Price date: 2024-03-01',content.splitlines()[0])

    def test_partial_cli_saves_detailed_source_gaps_and_reports_location(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'x','weight':1,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\n',encoding='utf-8')
            folder='https://www.sec.gov/Archives/edgar/data/123/456/'
            gaps=[f'Could not read document {folder}image{i}.jpg: Unsupported' for i in range(6)]
            result={'ranked':[],'watch':[],'dropped':[],'limitations':gaps,'index_date':'2024-03-01'}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d,'--partial']
            with patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result): seeker.main()
            detail=next(root.glob('source-gaps-*.json'))
            self.assertEqual(json.loads(detail.read_text(encoding='utf-8'))['gaps'],gaps)
            report=next(root.glob('spinoff-screen-*.md')).read_text(encoding='utf-8')
            self.assertIn('6 documents',report)
            self.assertIn(detail.name,report)
            self.assertEqual(report.strip().splitlines()[-1],'screens, not recommendations')

    def test_partial_cli_wires_workspace_provider_from_evidence_file(self):
        import types
        ld=types.ModuleType('lseg.data'); ld.close_session=lambda:None
        package=types.ModuleType('lseg'); package.data=ld
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'; evidence=root/'evidence.json'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'x','weight':1,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\nLSEG_APP_KEY=not-a-real-key\n',encoding='utf-8')
            evidence.write_text(json.dumps({'1':{'cik':'1'}}),encoding='utf-8')
            result={'ranked':[],'watch':[],'dropped':[],'limitations':[],'index_date':'2024-03-01'}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d,'--partial','--lseg-evidence',str(evidence)]
            with patch.dict(sys.modules,{'lseg':package,'lseg.data':ld}), patch('closes_reader.open_workspace_session'), patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result) as screen:
                seeker.main()
            self.assertIsInstance(screen.call_args.kwargs['factor_provider'],seeker.WorkspaceOfficialProvider)

    def test_partial_cli_requests_same_input_weight_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=root/'factors.json'; env=root/'.env'
            config.write_text(json.dumps({'window_days':90,'factors':[{'name':'x','weight':1,'direction':'lower','threshold':2}]}),encoding='utf-8')
            env.write_text('SEC_USER_AGENT=Example analyst test@example.test\n',encoding='utf-8')
            scenario={'ranked':[],'watch':[],'unranked':[]}
            comparison={'as_of':'2024-03-01','disabled_factor':'x','baseline':scenario,'disabled':scenario}
            result={'ranked':[],'watch':[],'dropped':[],'limitations':[],'index_date':'2024-03-01','comparison':comparison}
            argv=['seeker.py','--start','2024-01-01','--config',str(config),'--env',str(env),'--output',d,'--partial','--compare-zero','x']
            with patch.object(sys,'argv',argv), patch.object(seeker,'run_screen',return_value=result) as screen: seeker.main()
            self.assertEqual(screen.call_args.kwargs['compare_zero'],'x')
            content=next(root.glob('spinoff-screen-*.md')).read_text(encoding='utf-8')
            self.assertIn('Same-input weight comparison',content)
            self.assertEqual(content.strip().splitlines()[-1],'screens, not recommendations')

    def test_filing_insider_evidence_flows_to_frozen_factor_snapshot(self):
        row={'form':'10-12B','cik':'0000000123','date':'2024-01-08','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}
        text=('Information statement. Security ownership of certain beneficial owners and management. '
              'As of January 5, 2024, our directors and executive officers as a group beneficially owned 6.5% of our outstanding common stock.')
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[{'url':'https://www.sec.gov/Archives/filing.htm','text':text}]), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',[row],seeker.Registry(Path(d)/'registry.json'),'2024-01-01',as_of=date(2024,1,10))
        rec['distribution_date']=seeker.fact('2024-01-01','f','Distribution')
        snapshot={'last':{'date':'2024-01-10','close':'8','when_issued':False,'basis':'official_unadjusted','source':'reader'}}
        enriched=seeker.enrich_factor_inputs(rec,snapshot,date(2024,1,10))
        self.assertEqual(enriched['factors']['insiders'],6.5)
        self.assertIn('https://www.sec.gov/Archives/filing.htm',enriched['factor_explanations']['insiders'])
        snapshot['insiders']={'value':'7','as_of':'2024-01-05','filing_date':'2024-01-08','filing':'g','section':'Ownership'}
        self.assertNotIn('insiders',seeker.enrich_factor_inputs(rec,snapshot,date(2024,1,10))['factors'])

    def test_unranked_price_still_has_actual_date_in_report(self):
        config={'window_days':90,'factors':[{'name':'size','weight':25,'direction':'lower','threshold':1000}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{}}
        snapshot={'last':{'date':'2024-01-10','close':'8','when_issued':False,'basis':'official_unadjusted','source':'reader'}}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            result=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=lambda record,day:snapshot)
        self.assertEqual(result['price_date'],'2024-01-10')
        self.assertTrue(any('8 on 2024-01-10' in line for line in result['limitations']))

    def test_workspace_provider_runtime_failure_leaves_unranked_without_stale_price(self):
        config={'window_days':90,'factors':[{'name':'weakness','weight':25,'direction':'higher','threshold':15}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{'weakness':99},'latest_close':{'date':'2024-01-02','close':'9'}}
        def unavailable(record,day): raise RuntimeError('Vendor failure')
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=unavailable)
        self.assertEqual(output['ranked'],[])
        self.assertIsNone(output['price_date'])
        self.assertTrue(any('unranked' in x for x in output['limitations']))

    def test_verified_workspace_provider_feeds_dated_prices_into_scoring(self):
        config={'window_days':90,'factors':[{'name':'weakness','weight':25,'direction':'higher','threshold':15}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{}}
        class Reader:
            def __init__(self,*args): pass
            def factor_snapshot(self,cik,distribution,end):
                return {'first':{'date':'2024-01-02','close':'10','when_issued':False,'basis':'official_unadjusted','source':'reference','verified_first':True},
                        'last':{'date':'2024-01-10','close':'8','when_issued':False,'basis':'official_unadjusted','source':'reference'}}
        with tempfile.TemporaryDirectory() as d, patch('closes_reader.WorkspaceOfficialReader',Reader), patch('closes_reader.completed_close_end',return_value='2024-01-10'), patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'fetch_companyfacts',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            provider=seeker.WorkspaceOfficialProvider(None,None,{'1':{'cik':'1'}})
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=provider)
        self.assertEqual(output['ranked'][0]['points']['weakness'],25)
        self.assertEqual(output['ranked'][0]['latest_close']['date'],'2024-01-10')
        self.assertEqual(output['price_date'],'2024-01-10')

    def test_screen_reports_workspace_probe_without_scoring_candidate_values(self):
        config={'window_days':90,'factors':[{'name':'weakness','weight':25,'direction':'higher','threshold':15}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{}}
        def probe(record,day):
            self.assertEqual(record['distribution_date'],'2024-01-01')
            return {'candidate_count':2,'limitations':['Candidate prices are not verified.']}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,candidate_probe=probe)
        self.assertEqual(output['ranked'],[])
        self.assertTrue(any('Candidate prices are not verified.' in x for x in output['limitations']))
        self.assertIsNone(output['price_date'])

    def test_screen_can_score_a_sourced_frozen_factor_input_without_exporting_first_price(self):
        config={'window_days':90,'factors':[{'name':'size','weight':25,'direction':'lower','threshold':1000},{'name':'weakness','weight':25,'direction':'higher','threshold':15},{'name':'insiders','weight':25,'direction':'higher','threshold':5}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'parent':seeker.fact('Parent','f','Parent'),'factors':{}}
        snapshot={'first':{'date':'2024-01-02','close':'10','when_issued':False,'basis':'official_unadjusted','source':'reader','verified_first':True},
                  'last':{'date':'2024-01-10','close':'8','when_issued':False,'basis':'official_unadjusted','source':'reader'},
                  'shares':{'value':'100','filing':'f','section':'Shares','as_of':'2024-01-10','filing_date':'2024-01-10'},
                  'insiders':{'value':'5','filing':'f','section':'Ownership','as_of':'2024-01-05','filing_date':'2024-01-05'}}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=lambda record,day:snapshot)
        self.assertEqual(output['ranked'][0]['total'],75)
        self.assertEqual(output['ranked'][0]['latest_close']['date'],'2024-01-10')
        self.assertNotIn('first_close',output['ranked'][0])
        self.assertIn('size',output['ranked'][0]['factor_explanations'])
        self.assertEqual(output['price_date'],'2024-01-10')

    def test_same_input_comparison_is_in_report_without_refetching_factors(self):
        config={'window_days':90,'factors':[{'name':'size','weight':25,'direction':'lower','threshold':1000},{'name':'insiders','weight':25,'direction':'higher','threshold':5}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{}}
        snapshot={'first':{'date':'2024-01-02','close':'10','when_issued':False,'basis':'official_unadjusted','source':'reader','verified_first':True},
                  'last':{'date':'2024-01-10','close':'8','when_issued':False,'basis':'official_unadjusted','source':'reader'},
                  'shares':{'value':'100','filing':'f','section':'Shares','as_of':'2024-01-10','filing_date':'2024-01-10'},
                  'insiders':{'value':'5','filing':'f','section':'Ownership','as_of':'2024-01-05','filing_date':'2024-01-05'}}
        calls=[]
        def provider(record,day): calls.append(day); return snapshot
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            result=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=provider,compare_zero='insiders')
        self.assertEqual(len(calls),1)
        self.assertEqual(result['comparison']['baseline']['ranked'][0]['total'],50)
        self.assertEqual(result['comparison']['disabled']['ranked'][0]['total'],25)
        text=seeker.report(date(2024,1,10),result['price_date'],result['index_date'],result['ranked'],result['watch'],result['dropped'],result['limitations'],comparison=result['comparison'])
        self.assertIn('Same-input weight comparison',text)
        self.assertIn('insiders',text)
        self.assertEqual(text.strip().splitlines()[-1],'screens, not recommendations')

    def test_failed_factor_provider_does_not_reuse_stale_price(self):
        config={'window_days':90,'factors':[{'name':'x','weight':0,'direction':'higher','threshold':1}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        candidate={'name':'Fictional','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-01-01','f','Distribution'),'factors':{},'latest_close':{'date':'2023-12-01','close':'999'}}
        def unavailable(record,day): raise OSError('unavailable')
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',return_value=(candidate,[])):
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,1,10),config,2024,factor_provider=unavailable)
        self.assertNotIn('latest_close',output['ranked'][0])
        self.assertIsNone(output['price_date'])
        self.assertTrue(any('factor data unavailable' in s for s in output['limitations']))

    def test_factor_snapshot_rejects_prices_after_screen_date(self):
        record={'name':'Fictional','distribution_date':seeker.fact('2024-01-01','f','Distribution')}
        future={'first':{'date':'2024-01-02','close':'10','when_issued':False,'basis':'official_unadjusted','source':'p','verified_first':True},'last':{'date':'2024-01-11','close':'8','when_issued':False,'basis':'official_unadjusted','source':'p'}}
        enriched=seeker.enrich_factor_inputs(record,future,date(2024,1,10))
        self.assertEqual(enriched['factors'],{})
        self.assertNotIn('latest_close',enriched)

    def test_missing_date_is_unranked_even_when_no_factors_are_active(self):
        records=[{'name':'Fictional','trading':True}]
        ranked,watch,unranked=seeker.prepare_screen(records,'2024-01-01',date(2024,3,1),90,[])
        self.assertEqual(ranked,[])
        self.assertIn('distribution date',unranked[0]['reason'])

    def test_unknown_trading_is_unranked_and_not_on_watch_list(self):
        records=[{'name':'Unknown date','trading':None},
                 {'name':'Known date','trading':None,'distribution_date':seeker.fact('2024-02-01','f','s')}]
        ranked,watch,unranked=seeker.prepare_screen(records,'2024-01-01',date(2024,3,1),90,[])
        self.assertEqual(ranked,[])
        self.assertEqual(watch,[])
        self.assertTrue(all(any(r['name']==name and 'trading' in r['reason'] for r in unranked) for name in ('Unknown date','Known date')))

    def test_listing_stage_retains_cert_source_without_claiming_trading(self):
        reg={'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}
        cert={'form':'CERT','cik':'0000000123','date':'2024-01-02','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000002.txt'}
        def folders(client,row):
            return [{'url':'https://www.sec.gov/Archives/cert.htm','text':'Fictional Newco has been approved for listing.'}] if row['form']=='CERT' else [{'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=folders), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',[reg,cert],seeker.Registry(Path(d)/'registry.json'),'2024-01-01',as_of=date(2024,1,10))
            self.assertTrue(rec['listing'])
            self.assertEqual(seeker.stage(rec,date(2024,1,10),90),'listing approved')
            self.assertEqual(rec['listing_evidence']['filing'],'https://www.sec.gov/Archives/cert.htm')
            self.assertEqual(rec['listing_evidence']['date'],'2024-01-02')
            self.assertIsNone(rec['trading'])
        def unrelated(client,row):
            return [{'url':'https://www.sec.gov/Archives/cert.htm','text':'Fictional Newco appears here. Other Entity is approved for listing.'}] if row['form']=='CERT' else [{'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=unrelated), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',[reg,cert],seeker.Registry(Path(d)/'registry.json'),'2024-01-01',as_of=date(2024,1,10))
            self.assertFalse(rec['listing'])

    def test_only_current_explicit_nontrading_statement_supports_watch_list(self):
        row={'form':'10-12B','cik':'0000000123','date':'2024-01-10','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}
        doc={'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement\nAs of January 10, 2024, our common stock is not trading on any exchange.'}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[doc]), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',[row],registry,'2024-01-01',as_of=date(2024,1,10))
            self.assertIs(rec['trading'],False)
            self.assertEqual(rec['trading_evidence']['filing'],doc['url'])
            ranked,watch,unranked=seeker.prepare_screen([rec],'2024-01-01',date(2024,1,10),90,[])
            self.assertEqual(watch[0]['name'],'Fictional Newco')
            self.assertEqual(watch[0]['evidence']['filing'],doc['url'])
            self.assertIn(doc['url'],seeker.report(date(2024,1,10),None,None,ranked,watch,[],[]))
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[doc]), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',[row],seeker.Registry(Path(d)/'registry.json'),'2024-01-01',as_of=date(2024,1,11))
            self.assertIsNone(rec['trading'])
        own=[{'form':'4','cik':'0000000123','date':'2024-01-10','path':'edgar/data/123/0000000123-24-000002.txt'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[doc]), patch.object(seeker,'submissions',return_value=own):
            rec,gaps=seeker.inspect_candidate(None,'123',[row],seeker.Registry(Path(d)/'registry.json'),'2024-01-01',as_of=date(2024,1,10))
            self.assertIs(rec['trading'],True)

    def test_missing_trading_form_is_not_proof_of_non_trading(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertIsNone(rec['trading'])

    def test_weight_comparison_scores_same_frozen_inputs_without_exporting_prices(self):
        factors=[{'name':'size','weight':25,'direction':'lower','threshold':1000},{'name':'insiders','weight':25,'direction':'higher','threshold':5}]
        records=[{'name':'One','trading':True,'distribution_date':seeker.fact('2024-01-01','f','s'),'factors':{'size':800,'insiders':6},'first_close':{'close':'sensitive'}},
                 {'name':'Two','trading':True,'distribution_date':seeker.fact('2024-01-01','f','s'),'factors':{'size':800}}]
        comparison=seeker.compare_weight_scenarios(records,'2024-01-01',date(2024,1,10),90,factors,'insiders')
        before=comparison['baseline']; after=comparison['disabled']
        self.assertEqual(before['ranked'][0]['points'],{'size':25.0,'insiders':25.0})
        self.assertTrue(any(x['name']=='Two' for x in before['unranked']))
        self.assertEqual([x['name'] for x in after['ranked']],['One','Two'])
        self.assertEqual(after['ranked'][0]['points'],{'size':25.0})
        self.assertNotIn('sensitive',json.dumps(comparison))
        self.assertEqual(factors[1]['weight'],25)
        with self.assertRaises(ValueError): seeker.compare_weight_scenarios(records,'2024-01-01',date(2024,1,10),90,factors,'unknown')

    def test_watch_and_window_and_before_start(self):
        records=[{'name':'In','trading':True,'distribution_date':seeker.fact('2024-02-01','f','s'),'factors':{}},
                 {'name':'Watch','trading':False},
                 {'name':'Earlier','trading':True,'distribution_date':seeker.fact('2023-10-01','f','s'),'factors':{}}]
        ranked,watch,unranked=seeker.prepare_screen(records,'2024-01-01',date(2024,3,1),90,[])
        self.assertEqual([r['name'] for r in ranked],['In'])
        self.assertEqual(ranked[0]['window_ends'],'2024-05-01')
        self.assertEqual([r['name'] for r in watch],['Watch'])
        self.assertTrue(any(r['name']=='Watch' and 'distribution date' in r['reason'] for r in unranked))

    def test_repeated_document_gaps_are_summarized_with_all_details_saved(self):
        folder='https://www.sec.gov/Archives/edgar/data/123/456/'
        gaps=[f'Could not read document {folder}image{i}.jpg: Unsupported' for i in range(6)]
        gaps.append('Could not read parent submissions: OSError')
        summary,details=seeker.summarize_document_gaps(gaps)
        self.assertTrue(any('6 documents' in item and folder in item for item in summary))
        self.assertIn('Could not read parent submissions: OSError',summary)
        self.assertEqual(len(details),6)
        with tempfile.TemporaryDirectory() as d:
            path=seeker.save_source_gaps(Path(d),details)
            saved=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(saved['gaps'],details)
            self.assertNotEqual(path,seeker.save_source_gaps(Path(d),details))

    def test_output_names_are_unique_when_clock_does_not_advance(self):
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'datetime') as clock:
            clock.now.return_value.astimezone.return_value.strftime.return_value='2024-01-01_12-00-00_000000_-0500'
            text='Run date: 2024-01-01 | Price date: unavailable | Index date: unavailable\n\nscreens, not recommendations\n'
            self.assertNotEqual(seeker.save_report(d,text),seeker.save_report(d,text))
            self.assertNotEqual(seeker.save_source_gaps(d,['gap']),seeker.save_source_gaps(d,['gap']))

    def test_report_save_is_unique_and_ends_correctly(self):
        with tempfile.TemporaryDirectory() as d:
            path=seeker.save_report(Path(d),'Run date: 2024-01-01 | Price date: unavailable | Index date: unavailable\n\nscreens, not recommendations\n')
            self.assertTrue(path.exists())
            self.assertIn('spinoff-screen-',path.name)
            self.assertEqual(path.read_text(encoding='utf-8').strip().splitlines()[-1],'screens, not recommendations')

    def test_screen_flushes_established_facts_even_if_candidate_read_fails(self):
        config={'window_days':90,'factors':[{'name':'x','weight':1,'direction':'higher','threshold':1}]}
        rows=[{'form':'10-12B','cik':'1','date':'2024-01-01','name':'Fictional','path':'1'}]
        def broken(client,cik,group,registry,since,ticker_data=None,as_of=None):
            registry.ensure_entity(cik)
            registry.record(cik,'parent',seeker.fact('Fictional Parent','f','Parent'))
            raise ValueError('bad document')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'registry.json'; registry=seeker.Registry(path,autosave=False)
            with patch.object(seeker,'collect_indices',return_value=(rows,'2024-01-10',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',side_effect=broken):
                output=seeker.run_screen(None,registry,'2024-01-01',date(2024,1,10),config,2024)
            self.assertEqual(seeker.Registry(path).resolved('1','parent'),'Fictional Parent')
            self.assertTrue(any('review failed' in item for item in output['limitations']))

    def test_screen_connects_index_candidates_ranking_watch_and_unranked(self):
        config={'window_days':90,'factors':[{'name':'size','weight':10,'direction':'lower','threshold':2}]}
        registration=lambda cik,name: {'form':'10-12B','cik':cik,'date':'2024-01-01','name':name,'path':cik}
        rows=[registration('1','Ready'),registration('2','Watch'),registration('3','Unknown')]
        candidates={
          '1':{'name':'Ready','cik':'1','trading':True,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'distribution_date':seeker.fact('2024-02-01','f','Distribution'),'parent':seeker.fact('Parent','f','Parent'),'factors':{'size':1}},
          '2':{'name':'Watch','cik':'2','trading':False,'spinoff_evidence':{'filing':'f','date':'2024-01-01'},'factors':{}},
          '3':{'name':'Unknown','cik':'3','trading':False,'spinoff_evidence':None,'factors':{}}
        }
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-03-01',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',side_effect=lambda client,cik,group,registry,since,ticker_data=None,as_of=None:(candidates[cik],[])):
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,3,1),config,2023)
        self.assertEqual(output['ranked'][0]['name'],'Ready')
        self.assertEqual(output['ranked'][0]['points']['size'],10)
        self.assertEqual(output['watch'][0]['name'],'Watch')
        self.assertTrue(any('Unknown' in item for item in output['limitations']))
        self.assertEqual(output['index_date'],'2024-03-01')

    def test_diagnostic_candidate_limit_is_visible(self):
        rows=[{'form':'10-12B','cik':str(n),'date':'2024-01-01','name':'Fictional','path':str(n)} for n in (1,2,3)]
        config={'window_days':90,'factors':[{'name':'size','weight':10,'direction':'lower','threshold':2}]}
        def fake(client,cik,group,registry,since,ticker_data=None,as_of=None):
            return {'name':cik,'cik':cik,'spinoff_evidence':None},[]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'collect_indices',return_value=(rows,'2024-03-01',[])), patch.object(seeker,'fetch_company_tickers',return_value={}), patch.object(seeker,'inspect_candidate',side_effect=fake) as inspect:
            output=seeker.run_screen(None,seeker.Registry(Path(d)/'registry.json'),'2024-01-01',date(2024,3,1),config,2023,max_candidates=1)
        self.assertEqual(inspect.call_count,1)
        self.assertTrue(any('1 of 3' in s for s in output['limitations']))

class SubmissionTests(unittest.TestCase):
    def test_parent_identity_requires_exact_unique_name_and_matching_filing_header(self):
        ticker_data={'0':{'title':'Fictional Parent','cik_str':123},'1':{'title':'Other','cik_str':456}}
        self.assertEqual(seeker.parent_cik_candidates('Fictional Parent',ticker_data),['0000000123'])
        self.assertEqual(seeker.parent_cik_candidates('Fictional',ticker_data),[])
        filing='COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000123\n'
        self.assertTrue(seeker.parent_header_matches(filing,'Fictional Parent','123'))
        self.assertFalse(seeker.parent_header_matches(filing,'Fictional Parent','456'))
        self.assertFalse(seeker.parent_header_matches(filing,'Other','123'))
        mixed='COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000456\nCOMPANY CONFORMED NAME: Other\nCENTRAL INDEX KEY: 0000000123\n'
        self.assertFalse(seeker.parent_header_matches(mixed,'Fictional Parent','123'))

    def test_parent_identity_accepts_legal_suffix_equivalence_without_prefix_matching(self):
        ticker_data={'0':{'title':'Fictional Parent CO','cik_str':123},'1':{'title':'Fictional Parent Holdings CO','cik_str':456}}
        self.assertEqual(seeker.parent_cik_candidates('Fictional Parent Company',ticker_data),['0000000123'])
        header='COMPANY CONFORMED NAME: Fictional Parent CO\nCENTRAL INDEX KEY: 0000000123\n'
        self.assertTrue(seeker.parent_header_matches(header,'Fictional Parent Company','123'))
        ticker_data['2']={'title':'Fictional Parent Company','cik_str':789}
        self.assertEqual(len(seeker.parent_cik_candidates('Fictional Parent Company',ticker_data)),2)

    def test_parent_cik_is_backed_by_matching_edgar_filing_not_just_ticker_data(self):
        tickers={'0':{'title':'Fictional Parent','cik_str':123}}
        class Client:
            def get(self,url):
                if '/submissions/' in url:
                    return json.dumps({'filings':{'recent':{'form':['10-K'],'filingDate':['2024-02-01'],'accessionNumber':['0000000123-24-000001']},'files':[]}})
                return 'COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000123\n'
        entry=seeker.find_parent_cik(Client(),'Fictional Parent',tickers)
        self.assertEqual(entry['value'],'0000000123')
        self.assertIn('/edgar/data/123/',entry['filing'])
        self.assertTrue(entry['section'])
        tickers['1']={'title':'Fictional Parent','cik_str':456}
        self.assertIsNone(seeker.find_parent_cik(Client(),'Fictional Parent',tickers))

    def test_parent_lookup_does_not_use_filings_after_analysis_date(self):
        tickers={'0':{'title':'Fictional Parent','cik_str':123}}
        rows=[{'form':'10-K','date':'2024-02-01','cik':'0000000123','path':'edgar/data/123/0000000123-24-000002.txt'},
              {'form':'10-K','date':'2024-01-01','cik':'0000000123','path':'edgar/data/123/0000000123-24-000001.txt'}]
        class Client:
            def get(self,url): return 'COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000123\n'
        with patch.object(seeker,'submissions',return_value=rows):
            entry=seeker.find_parent_cik(Client(),'Fictional Parent',tickers,as_of=date(2024,1,15))
        self.assertEqual(entry['filing_date'],'2024-01-01')

    def test_inspection_ignores_future_filings_and_future_registry_values(self):
        registration={'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}
        future={'form':'8-K','cik':'0000000123','date':'2024-02-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000002.txt'}
        docs=[{'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement\nParent: Fictional Parent'}]
        own=[{'form':'10-Q','cik':'0000000123','date':'2024-02-02','path':'edgar/data/123/0000000123-24-000003.txt'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs) as folders, patch.object(seeker,'submissions',return_value=own):
            registry=seeker.Registry(Path(d)/'registry.json')
            registry.record('123','parent',dict(seeker.fact('Future Parent','future','Parent'),filing_date='2024-02-01'))
            rec,gaps=seeker.inspect_candidate(None,'123',[registration,future],registry,'2024-01-01',as_of=date(2024,1,15))
            self.assertEqual(folders.call_count,1)
            self.assertEqual(seeker.value(rec,'parent'),'Fictional Parent')
            self.assertIsNone(rec['trading'])
            self.assertIsNone(rec['distribution_date'])

    def test_parent_cik_verification_checks_recent_filings_before_full_history(self):
        tickers={'0':{'title':'Fictional Parent','cik_str':123}}
        row={'form':'10-K','date':date.today().isoformat(),'cik':'0000000123','path':'edgar/data/123/0000000123-24-000001.txt'}
        class Client:
            def get(self,url): return 'COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000123\n'
        with patch.object(seeker,'submissions',return_value=[row]) as lookup:
            entry=seeker.find_parent_cik(Client(),'Fictional Parent',tickers)
            self.assertEqual(entry['value'],'0000000123')
            self.assertNotEqual(lookup.call_args.args[2],'1994-01-01')
            self.assertEqual(lookup.call_count,1)

    def test_parent_cik_verification_falls_back_to_historical_filings(self):
        tickers={'0':{'title':'Fictional Parent','cik_str':123}}
        row={'form':'10-K','date':'2001-01-01','cik':'0000000123','path':'edgar/data/123/0000000123-01-000001.txt'}
        class Client:
            def get(self,url): return 'COMPANY CONFORMED NAME: Fictional Parent\nCENTRAL INDEX KEY: 0000000123\n'
        with patch.object(seeker,'submissions',side_effect=[[],[row]]) as lookup:
            entry=seeker.find_parent_cik(Client(),'Fictional Parent',tickers)
            self.assertEqual(entry['value'],'0000000123')
            self.assertEqual(lookup.call_args.args[2],'1994-01-01')
            self.assertEqual(lookup.call_count,2)

    def test_parent_8k_lookup_uses_parent_cik_and_saved_history(self):
        class SEC:
            def __init__(self): self.urls=[]
            def get(self,url):
                self.urls.append(url)
                if url.endswith('CIK0000000123.json'):
                    return json.dumps({'filings':{'recent':{'form':['10-K'],'filingDate':['2024-04-01'],'accessionNumber':['0000000123-24-000001']},'files':[{'name':'CIK0000000123-submissions-001.json','filingTo':'2024-03-01'}]}})
                return json.dumps({'form':['8-K','10-Q'],'filingDate':['2024-03-01','2024-02-01'],'accessionNumber':['0000000123-24-000002','0000000123-24-000003']})
        c=SEC()
        events=seeker.parent_8ks(c,'123','2024-01-01')
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['form'],'8-K')
        self.assertTrue(c.urls[0].endswith('CIK0000000123.json'))
        self.assertTrue(any('submissions-001.json' in u for u in c.urls))

    def test_failed_company_submissions_does_not_assert_not_trading(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',side_effect=OSError('unavailable')):
            rec,gaps=seeker.inspect_candidate(None,'0000000123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertIsNone(rec['trading'])
            self.assertTrue(any('submissions' in gap for gap in gaps))

    def test_embedded_submission_fact_records_the_embedded_document_name(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/submission.txt','text':'Information statement\nParent: Fictional Parent','embedded_filename':'info.htm'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',rows,registry,'2024-01-01')
            self.assertEqual(seeker.value(rec,'parent'),'Fictional Parent')
            self.assertIn('info.htm',rec['parent']['section'])
            self.assertEqual(rec['parent']['filing'],docs[0]['url'])

    def test_conflicting_dates_in_one_filing_are_retained_in_registry(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement\nDistribution date: January 1, 2024\nDistribution date: January 2, 2024'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            registry.record('123','distribution_date',seeker.fact('2024-01-01','https://www.sec.gov/Archives/older.htm','Distribution'))
            rec,gaps=seeker.inspect_candidate(None,'123',rows,registry,'2024-01-01')
            self.assertIsNone(rec['distribution_date'])
            self.assertEqual({e['value'] for e in registry.data['0000000123']['distribution_date']},{'2024-01-01','2024-01-02'})
            self.assertIn('distribution_date',registry.conflicts('123'))

    def test_inspect_records_sourced_information_statement_letter(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco Corp','path':'edgar/data/123/0000000123-24-000001.txt'}]
        text=('Information statement\nDear Fictional Parent Company Shareholder:\nOn July 26, 2022, Fictional Parent Company ("FP") announced its plan to separate its business. '
              'The separation will occur through a pro rata distribution by FP of shares of a newly formed company, Fictional Newco Corporation ("FN"). '
              'Each FP shareholder as of the close of business on March 18, 2024, the record date for the distribution, will receive one share of FN common stock for every four shares of FP common stock held.')
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[{'url':'https://www.sec.gov/Archives/info.htm','text':text}]), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',rows,registry,'2024-01-01')
            self.assertEqual(seeker.value(rec,'parent'),'Fictional Parent Company')
            self.assertEqual(seeker.value(rec,'record_date'),'2024-03-18')
            self.assertIn('one share',seeker.value(rec,'distribution_ratio'))
            self.assertEqual(rec['record_date']['section'],'Shareholder letter')
            self.assertEqual(rec['spinoff_evidence']['section'],'Shareholder letter')
            self.assertEqual(rec['spinoff_evidence']['filing'],'https://www.sec.gov/Archives/info.htm')
            self.assertEqual(rec['spinoff_evidence']['status'],'planned')

    def test_new_company_distribution_8k_is_read_and_sourced(self):
        reg={'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}
        event={'form':'8-K','cik':'0000000123','date':'2024-04-04','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000002.txt'}
        registration={'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement\nParent: Fictional Parent'}
        report={'url':'https://www.sec.gov/Archives/event.htm','text':'Item 2.01. Completion of Acquisition or Disposition of Assets\nOn April 1, 2024, Fictional Parent completed the separation through the distribution of common stock of Fictional Newco to its stockholders.'}
        def folders(client,row): return [report] if row['form']=='8-K' else [registration]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=folders), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',[reg,event],registry,'2024-01-01')
            self.assertEqual(seeker.value(rec,'distribution_date'),'2024-04-01')
            self.assertEqual(rec['distribution_date']['filing'],report['url'])

    def test_parent_8k_unrelated_label_does_not_set_distribution_date(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        event={'form':'8-K','cik':'0000000999','date':'2024-04-04','path':'edgar/data/999/0000000999-24-000001.txt'}
        registration={'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement\nParent: Fictional Parent\nParent CIK: 999'}
        report={'url':'https://www.sec.gov/Archives/event.htm','text':'Fictional Newco is mentioned here.\nDistribution date: 2024-04-01\nThis label refers to a different transaction.'}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=lambda client,row:[report] if row['cik']=='0000000999' else [registration]), patch.object(seeker,'submissions',return_value=[]), patch.object(seeker,'parent_8ks',return_value=[event]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',rows,registry,'2024-01-01')
            self.assertIsNone(seeker.value(rec,'distribution_date'))

    def test_parent_completion_date_enters_registry_with_section(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco Corp','path':'edgar/data/123/0000000123-24-000001.txt'}]
        event={'form':'8-K','cik':'0000000999','date':'2024-04-04','path':'edgar/data/999/0000000999-24-000001.txt'}
        registration={'url':'https://www.sec.gov/Archives/reg.htm','text':'Information statement\nParent: Fictional Parent Co\nParent CIK: 999'}
        report={'url':'https://www.sec.gov/Archives/event.htm','text':'Item 2.01. Completion of Acquisition or Disposition of Assets\nOn April 1, 2024, Fictional Parent Company completed the separation through the distribution of common stock of Fictional Newco Corporation to its stockholders.'}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=lambda client,row:[report] if row['cik']=='0000000999' else [registration]), patch.object(seeker,'submissions',return_value=[]), patch.object(seeker,'parent_8ks',return_value=[event]):
            registry=seeker.Registry(Path(d)/'registry.json')
            rec,gaps=seeker.inspect_candidate(None,'123',rows,registry,'2024-01-01')
            self.assertEqual(seeker.value(rec,'distribution_date'),'2024-04-01')
            self.assertEqual(rec['distribution_date']['section'],'Item 2.01')
            self.assertEqual(rec['distribution_date']['filing'],report['url'])
            self.assertEqual(rec['parent']['filing_date'],'2024-01-01')
            self.assertEqual(rec['distribution_date']['filing_date'],'2024-04-04')

    def test_parent_filings_search_includes_registration_before_start(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2022-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-22-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement\nParent: Fictional Parent\nParent CIK: 999'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]), patch.object(seeker,'parent_8ks',return_value=[]) as lookup:
            seeker.inspect_candidate(None,'123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            lookup.assert_called_once_with(None,'0000000999','2022-01-01')

    def test_later_distribution_evidence_can_reverse_prior_rejection(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'},
              {'form':'10-12B/A','cik':'0000000123','date':'2024-03-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000002.txt'}]
        statement='Fictional Parent will distribute shares of Fictional Newco to its shareholders.'
        def folder(client,row):
            suffix='first' if row['date']=='2024-01-01' else 'second'
            return [{'url':'https://www.sec.gov/Archives/'+suffix+'.htm','text':'Information statement\nParent: Fictional Parent\n'+('The company is a mutual fund.\n' if suffix=='first' else '')+statement}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=folder), patch.object(seeker,'submissions',return_value=[]):
            rec,gaps=seeker.inspect_candidate(None,'123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            self.assertEqual(rec['spinoff_evidence']['date'],'2024-03-01')
            self.assertFalse(seeker.is_dropped(rec))

    def test_trading_search_starts_at_registration_and_preserves_filing(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2022-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-22-000001.txt'}]
        own={'form':'10-Q','cik':'0000000123','date':'2022-06-01','path':'edgar/data/123/0000000123-22-000002.txt'}
        docs=[{'url':'https://www.sec.gov/Archives/form.htm','text':'Information statement'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[own]) as lookup:
            rec,gaps=seeker.inspect_candidate(None,'123',rows,seeker.Registry(Path(d)/'registry.json'),'2024-01-01')
            lookup.assert_called_once_with(None,'123','2022-01-01')
            self.assertTrue(rec['trading'])
            self.assertEqual(rec['trading_evidence']['filing'],'https://www.sec.gov/Archives/'+own['path'])
            self.assertEqual(rec['trading_evidence']['date'],own['date'])
            self.assertEqual(rec['trading_evidence']['form'],'10-Q')

    def test_trading_evidence_uses_new_company_own_form(self):
        rows=[{'form':'10-12B','cik':'123'},{'form':'10-Q','cik':'123'},{'form':'8-K','cik':'999'}]
        self.assertTrue(seeker.has_trading_evidence(rows,'123'))
        self.assertFalse(seeker.has_trading_evidence(rows,'999'))

    def test_group_candidates_keeps_registrations_before_distribution_start(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2022-01-01','name':'Fictional','path':'a'},
              {'form':'10-12B/A','cik':'0000000123','date':'2023-01-01','name':'Fictional','path':'b'},
              {'form':'CERT','cik':'0000000123','date':'2024-02-01','name':'Fictional','path':'c'},
              {'form':'4','cik':'0000000123','date':'2024-02-02','name':'Fictional','path':'d'},
              {'form':'8-K','cik':'0000000999','date':'2024-02-02','name':'Parent','path':'e'}]
        groups=seeker.group_candidates(rows)
        self.assertEqual(len(groups),1)
        self.assertEqual([r['form'] for r in groups['0000000123']],['10-12B','10-12B/A','CERT','4'])

    def test_full_history_keeps_old_registrations_but_does_not_retain_obsolete_event_indexes(self):
        rows=[{'form':'10-12B','cik':'1','date':'2000-01-01','path':'a'},
              {'form':'CERT','cik':'1','date':'2000-01-02','path':'b'},
              {'form':'8-K','cik':'1','date':'2000-01-03','path':'c'},
              {'form':'8-K/A','cik':'1','date':'2024-02-01','path':'d'}]
        with patch.object(seeker,'discover_index',return_value=(rows,'2024-03-01')):
            found,_,_=seeker.collect_indices(None,2024,date(2024,3,1),event_start='2024-01-01')
        self.assertEqual([r['path'] for r in found],['a','b','d'])

    def test_full_history_starts_at_first_public_edgar_index(self):
        visited=[]
        def fake(client,year,quarter):
            visited.append((year,quarter))
            return [],f'{year}-12-31'
        with patch.object(seeker,'discover_index',side_effect=fake):
            seeker.collect_indices(None,1994,date(1994,12,31))
        self.assertEqual(visited,[(1994,3),(1994,4)])

    def test_full_index_failures_are_recorded_and_latest_coverage_is_not_faked(self):
        class Client:
            def get(self,url):
                if 'QTR1' in url: return 'Last Data Received: March 31, 2024\n'
                raise OSError('failure')
        rows,index_date,problems=seeker.collect_indices(Client(),2024,date(2024,4,20))
        self.assertEqual(index_date,'2024-03-31')
        self.assertEqual(len(problems),1)
        self.assertEqual(rows,[])

    def test_index_collection_retains_registrations_and_certifications(self):
        rows=[{'form':'10-12B','date':'2024-01-01'},{'form':'CERT','date':'2024-01-02'},{'form':'8-K','date':'2024-01-02'},{'form':'8-K/A','date':'2024-01-02'},{'form':'4','date':'2024-01-03'}]
        with patch.object(seeker,'discover_index',return_value=(rows,'2024-03-31')):
            actual,index_date,issues=seeker.collect_indices(None,2024,date(2024,3,31))
        self.assertEqual([r['form'] for r in actual],['10-12B','CERT','8-K','8-K/A'])

    def test_group_candidates_scans_index_at_most_twice(self):
        class CountedRows:
            def __init__(self,rows): self.rows=rows; self.visits=0
            def __iter__(self):
                for row in self.rows:
                    self.visits+=1
                    yield row
        rows=[{'form':'10-12B','cik':str(i),'date':'2024-01-01','path':str(i)} for i in range(100)]
        rows += [{'form':'8-K','cik':str(i),'date':'2024-02-01','path':str(i)+'a'} for i in range(100)]
        rows.append({'form':'8-K','cik':'999','date':'2024-02-01','path':'other'})
        data=CountedRows(rows)
        grouped=seeker.group_candidates(data)
        self.assertEqual(len(grouped),100)
        self.assertEqual(len(grouped['1']),2)
        self.assertLessEqual(data.visits,2*len(rows))

    def test_form_index_includes_8k_amendments(self):
        row='8-K/A  Fictional Co 123 2024-02-01 edgar/data/123/0000000123-24-000001.txt'
        self.assertEqual(seeker.parse_index(row)[0]['form'],'8-K/A')

    def test_inspect_populates_sourced_registry_and_checks_parent_filings(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        registration={'url':'https://www.sec.gov/Archives/new.htm','text':'Information statement\nParent: Fictional Parent\nParent CIK: 999\nRecord date: 2024-01-10\nFictional Parent will distribute shares of Fictional Newco to its shareholders.'}
        parent_doc={'url':'https://www.sec.gov/Archives/parent.htm','text':'Item 2.01. Completion of Acquisition or Disposition of Assets\nOn January 20, 2024, Fictional Parent completed the separation through the distribution of common stock of Fictional Newco to its stockholders.'}
        event={'form':'8-K','cik':'0000000999','date':'2024-01-20','path':'edgar/data/999/0000000999-24-000001.txt'}
        def folders(client,row): return [parent_doc] if row['cik']=='0000000999' else [registration]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=folders), patch.object(seeker,'submissions',return_value=[{'form':'4','cik':'0000000123','date':'2024-01-21','path':'edgar/data/123/0000000123-24-000002.txt'}]), patch.object(seeker,'parent_8ks',return_value=[event]) as parent:
            registry=seeker.Registry(Path(d)/'registry.json')
            candidate,gaps=seeker.inspect_candidate(None,'0000000123',rows,registry,'2024-01-01')
            self.assertEqual(seeker.value(candidate,'distribution_date'),'2024-01-20')
            self.assertTrue(candidate['trading'])
            self.assertTrue(candidate['spinoff_evidence'])
            self.assertEqual(registry.resolved('123','record_date'),'2024-01-10')
            self.assertEqual(registry.data['0000000123']['distribution_date'][0]['filing'],parent_doc['url'])
            parent.assert_called_once_with(None,'0000000999','2024-01-01')

    def test_unrelated_parent_filing_cannot_supply_distribution_date(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        registration={'url':'https://www.sec.gov/Archives/new.htm','text':'Parent: Fictional Parent\nParent CIK: 999'}
        other={'url':'https://www.sec.gov/Archives/other.htm','text':'Unrelated transaction\nDistribution date: 2024-01-20'}
        event={'form':'8-K','cik':'0000000999','date':'2024-01-20','path':'edgar/data/999/0000000999-24-000001.txt'}
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',side_effect=lambda client,row:[other] if row['cik']=='0000000999' else [registration]), patch.object(seeker,'submissions',return_value=[]), patch.object(seeker,'parent_8ks',return_value=[event]):
            registry=seeker.Registry(Path(d)/'registry.json')
            candidate,gaps=seeker.inspect_candidate(None,'0000000123',rows,registry,'2024-01-01')
            self.assertIsNone(seeker.value(candidate,'distribution_date'))

    def test_malformed_attachment_does_not_discard_other_readable_filings(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        docs=[{'url':'https://www.sec.gov/Archives/bad.htm','text':'<![)5(RQ#4E.E%MQ5G"$'}, {'url':'https://www.sec.gov/Archives/good.htm','text':'Parent: Fictional Parent'}]
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=docs), patch.object(seeker,'submissions',return_value=[]):
            registry=seeker.Registry(Path(d)/'registry.json')
            candidate,gaps=seeker.inspect_candidate(None,'0000000123',rows,registry,'2024-01-01')
            self.assertEqual(seeker.value(candidate,'parent'),'Fictional Parent')
            self.assertTrue(any('bad.htm' in gap for gap in gaps))

    def test_parent_cik_lookup_is_saved_and_used(self):
        rows=[{'form':'10-12B','cik':'0000000123','date':'2024-01-01','name':'Fictional Newco','path':'edgar/data/123/0000000123-24-000001.txt'}]
        doc={'url':'https://www.sec.gov/Archives/new.htm','text':'Parent: Fictional Parent'}
        source=seeker.fact('0000000999','https://www.sec.gov/Archives/parent.htm','SEC header')
        with tempfile.TemporaryDirectory() as d, patch.object(seeker,'read_filing_folder',return_value=[doc]), patch.object(seeker,'submissions',return_value=[]), patch.object(seeker,'find_parent_cik',return_value=source), patch.object(seeker,'parent_8ks',return_value=[]) as parent:
            registry=seeker.Registry(Path(d)/'registry.json')
            seeker.inspect_candidate(None,'0000000123',rows,registry,'2024-01-01',ticker_data={'x':{}})
            self.assertEqual(registry.resolved('123','parent_cik'),'0000000999')
            parent.assert_called_once_with(None,'0000000999','2024-01-01')


