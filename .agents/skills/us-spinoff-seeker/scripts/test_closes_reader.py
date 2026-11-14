import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import closes_reader

class OfficialCloseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.file=Path(self.tmp.name)/'export.csv'
        with self.file.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['ticker','date','close','basis','session'])
            w.writeheader()
            w.writerows([
                {'ticker':'TEST','date':'2024-03-08','close':'10.00','basis':'official_unadjusted','session':'regular'},
                {'ticker':'TEST','date':'2024-03-11','close':'11.00','basis':'official_unadjusted','session':'regular'},
                {'ticker':'TEST','date':'2024-03-12','close':'12.00','basis':'official_unadjusted','session':'when-issued'},
                {'ticker':'TEST','date':'2024-03-13','close':'13.00','basis':'adjusted','session':'regular'},
            ])
    def tearDown(self): self.tmp.cleanup()
    def test_official_workspace_reader_requires_exchange_match_and_first_weekday(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Discovery:
            class Views: EQUITY_QUOTES='equities'
            def search(self,**kwargs): return Frame([{'TickerSymbol':'TEST','RIC':'TEST.N','AssetState':'AC','ExchangeName':'New York Stock Exchange'}])
        class Client:
            def __init__(self):
                self.discovery=Discovery()
                self.rows=[{'Date':'2024-01-03','Official Close Price':'10'},{'Date':'2024-01-04','Official Close Price':'8'}]
            def get_data(self,**kwargs): return Frame([r for r in self.rows if kwargs['parameters']['SDate']<=r['Date']<=kwargs['parameters']['EDate']])
        evidence={'cik':'1','ticker':'TEST','ric':'TEST.N','exchange':'New York Stock Exchange','listing_url':'https://www.sec.gov/Archives/example.htm',
                  'regular_way':True,'exchange_url':'https://exchange.example/close','reference_date':'2024-01-03','reference_close':'10'}
        client=Client()
        r=closes_reader.WorkspaceOfficialReader(client,evidence,lambda evidence: True)
        snapshot=r.factor_snapshot('1','2024-01-02','2024-01-04')
        self.assertEqual(snapshot['first']['date'],'2024-01-03')
        self.assertTrue(snapshot['first']['verified_first'])
        self.assertEqual(snapshot['last']['date'],'2024-01-04')
        self.assertEqual(snapshot['last']['basis'],'official_unadjusted')
        self.assertEqual(r.last_close_before(datetime(2024,1,4,16,0,tzinfo=closes_reader.EASTERN),'2024-01-02')['date'],'2024-01-03')
        self.assertEqual(r.last_close_before(datetime(2024,1,4,16,0,1,tzinfo=closes_reader.EASTERN),'2024-01-02')['date'],'2024-01-04')
        with self.assertRaises(ValueError): r.last_close_before(datetime(2024,1,4,16,0),'2024-01-02')
        with self.assertRaises(ValueError): r.factor_snapshot('2','2024-01-02','2024-01-04')
        evidence['reference_close']='11'
        with self.assertRaises(ValueError): closes_reader.WorkspaceOfficialReader(client,evidence,lambda evidence: True)
        evidence['reference_close']='10'; evidence['regular_way']=False
        with self.assertRaises(ValueError): closes_reader.WorkspaceOfficialReader(client,evidence,lambda evidence: True)
        evidence['regular_way']=True
        r=closes_reader.WorkspaceOfficialReader(client,evidence,lambda evidence: True)
        client.rows=[{'Date':'2024-01-03','Official Close Price':'10'},{'Date':'2024-01-05','Official Close Price':'7'}]
        # A missing first possible weekday must not be called the first close.
        self.assertIsNone(r.factor_snapshot('1','2024-01-03','2024-01-05')['first'])

    def test_workspace_probe_ends_before_unfinished_market_close(self):
        eastern=closes_reader.EASTERN
        self.assertEqual(closes_reader.completed_close_end('2024-01-05',datetime(2024,1,5,15,59,tzinfo=eastern)),'2024-01-04')
        self.assertEqual(closes_reader.completed_close_end('2024-01-05',datetime(2024,1,5,16,0,tzinfo=eastern)),'2024-01-04')
        self.assertEqual(closes_reader.completed_close_end('2024-01-05',datetime(2024,1,5,16,1,tzinfo=eastern)),'2024-01-05')
        self.assertEqual(closes_reader.completed_close_end('2024-01-04',datetime(2024,1,5,12,tzinfo=eastern)),'2024-01-04')
        with self.assertRaises(ValueError): closes_reader.completed_close_end('2024-01-05',datetime(2024,1,5,15,59))

    def test_workspace_probe_requires_unique_primary_and_never_returns_candidate_prices(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Views: EQUITY_QUOTES='equities'
        class Discovery:
            pass
        Discovery.Views=Views
        class Discovery(Discovery):
            def __init__(self): self.matches=[{'TickerSymbol':'TEST','RIC':'TEST.N','IsPrimaryRIC':True,'AssetState':'AC','ExchangeName':'Example'}]
            def search(self,**kwargs): return Frame(self.matches)
        class Client:
            def __init__(self): self.discovery=Discovery(); self.calls=[]
            def get_data(self,**kwargs):
                self.calls.append(kwargs)
                return Frame([{'Date':'2024-01-03','Close Price':'10.0'}])
        client=Client()
        probe=closes_reader.WorkspaceCandidateProbe(client,{'x':{'cik_str':1,'ticker':'TEST'}})
        result=probe({'cik':'1','distribution_date':'2024-01-02'},'2024-01-04')
        self.assertEqual(result['candidate_count'],1)
        self.assertNotIn('10.0',str(result))
        self.assertNotIn('first',result); self.assertNotIn('last',result)
        client.discovery.matches.append(dict(client.discovery.matches[0],RIC='TEST.X'))
        with self.assertRaises(ValueError): probe({'cik':'1','distribution_date':'2024-01-02'},'2024-01-04')
        self.assertEqual(len(client.calls),1)

    def test_range_only_regular_official_unadjusted(self):
        r=closes_reader.daily_closes(self.file,'TEST','2024-03-08','2024-03-13')
        self.assertEqual([x['date'] for x in r],['2024-03-08','2024-03-11'])
    def test_last_close_before_dst_clock(self):
        self.assertEqual(closes_reader.last_close_before(self.file,'TEST',datetime(2024,3,11,19,59,tzinfo=timezone.utc))['date'],'2024-03-08')
        self.assertEqual(closes_reader.last_close_before(self.file,'TEST',datetime(2024,3,11,20,0,tzinfo=timezone.utc))['date'],'2024-03-08')
        self.assertEqual(closes_reader.last_close_before(self.file,'TEST',datetime(2024,3,11,20,0,1,tzinfo=timezone.utc))['date'],'2024-03-11')
    def test_reject_naive_time(self):
        with self.assertRaises(ValueError): closes_reader.last_close_before(self.file,'TEST',datetime(2024,3,11,16,0))
    def test_reject_duplicate_and_invalid_values(self):
        with self.file.open('a',encoding='utf-8') as f: f.write('TEST,2024-03-11,14,official_unadjusted,regular\n')
        with self.assertRaises(ValueError): closes_reader.daily_closes(self.file,'TEST','2024-03-01','2024-03-20')
    def test_reference_check_requires_matching_price_date_and_exchange_source(self):
        close={'date':'2024-03-11','close':'11.00'}
        self.assertTrue(closes_reader.matches_exchange(close,{'date':'2024-03-11','close':'11.00','url':'https://exchange.test/official'}))
        self.assertFalse(closes_reader.matches_exchange(close,{'date':'2024-03-11','close':'11.01','url':'https://exchange.test/official'}))
        self.assertFalse(closes_reader.matches_exchange(close,{'date':'2024-03-11','close':'11.00','url':''}))

    def test_financial_datasets_pages_are_read_without_claiming_official_close(self):
        calls=[]
        def fetch(url,headers):
            calls.append((url,headers))
            if len(calls)==1:
                return {'prices':[{'time':'2024-03-08T00:00:00Z','close':10}], 'next_page_url':'https://api.financialdatasets.ai/prices/?cursor=abc'}
            return {'prices':[{'time':'2024-03-11T00:00:00Z','close':11}]}
        data=closes_reader.financial_datasets_prices('key','TEST','2024-03-01','2024-03-31',fetch)
        self.assertEqual(len(data),2)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0][1]['X-API-KEY'],'key')
        self.assertEqual(calls[1][1]['X-API-KEY'],'key')
        self.assertNotIn('official_unadjusted',str(data))

    def test_pagination_does_not_send_key_to_untrusted_host(self):
        def fetch(url,headers): return {'prices':[], 'next_page_url':'https://evil.test/'}
        with self.assertRaises(ValueError): closes_reader.financial_datasets_prices('key','TEST','2024-03-01','2024-03-31',fetch)

    def test_spot_check_compares_one_same_day_exchange_reference(self):
        reference={'date':'2024-03-11','close':'11.00','url':'https://exchange.test/official'}
        def vendor(url,headers): return {'prices':[{'time':'2024-03-11T00:00:00Z','close':11.00}]}
        result=closes_reader.check_exchange_close('key','TEST','2024-03-11',reference,vendor)
        self.assertTrue(result['matches'])
        self.assertEqual(result['date'],'2024-03-11')
        self.assertEqual(result['exchange_url'],reference['url'])

    def test_spot_check_wont_accept_missing_wrong_day_or_wrong_close(self):
        reference={'date':'2024-03-11','close':'11.00','url':'https://exchange.test/official'}
        def different(url,headers): return {'prices':[{'time':'2024-03-11T00:00:00Z','close':12.00}]}
        self.assertFalse(closes_reader.check_exchange_close('key','TEST','2024-03-11',reference,different)['matches'])
        def absent(url,headers): return {'prices':[]}
        self.assertIsNone(closes_reader.check_exchange_close('key','TEST','2024-03-11',reference,absent)['matches'])

    def test_spot_check_requires_reference_and_never_fetches_exchange(self):
        def vendor(url,headers): return {'prices':[{'time':'2024-03-11T00:00:00Z','close':11.00}]}
        with self.assertRaises(ValueError): closes_reader.check_exchange_close('key','TEST','2024-03-11',{},vendor)

    def test_workspace_export_requires_external_file_and_verified_exchange_observation(self):
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as workspace:
            path=Path(outside)/'workspace.csv'
            path.write_text('Date,Official close\n2024-03-08,10.00\n2024-03-11,11.00\n',encoding='utf-8')
            mapping={'date':'Date','close':'Official close','ticker':'TEST','price_basis':'official_unadjusted','session':'regular','coverage_start':'2024-03-08','coverage_end':'2024-03-11'}
            reference={'ticker':'TEST','date':'2024-03-11','close':'11.00','url':'https://exchange.test/official'}
            reader=closes_reader.WorkspaceExportReader(path,mapping,reference,workspace_root=workspace)
            rows=reader.daily_closes('TEST','2024-03-08','2024-03-11')
            self.assertEqual([r['date'] for r in rows],['2024-03-08','2024-03-11'])
            self.assertEqual(reader.last_close_before('TEST',datetime(2024,3,11,19,59,tzinfo=timezone.utc))['date'],'2024-03-08')
            self.assertEqual(reader.last_close_before('TEST',datetime(2024,3,11,20,0,tzinfo=timezone.utc))['date'],'2024-03-08')
            self.assertEqual(reader.last_close_before('TEST',datetime(2024,3,11,20,0,1,tzinfo=timezone.utc))['date'],'2024-03-11')
            with self.assertRaises(ValueError): reader.last_close_before('TEST',datetime(2024,3,12,21,0,tzinfo=timezone.utc))
            with self.assertRaises(ValueError):
                closes_reader.WorkspaceExportReader(path,mapping,dict(reference,close='12.00'),workspace_root=workspace)
            inside=Path(workspace)/'workspace.csv'; inside.write_text(path.read_text(encoding='utf-8'),encoding='utf-8')
            with self.assertRaises(ValueError):
                closes_reader.WorkspaceExportReader(inside,mapping,reference,workspace_root=workspace)
            path.write_text('Date,Official close\n2024-03-08,99.00\n2024-03-11,11.00\n',encoding='utf-8')
            with self.assertRaises(ValueError): reader.daily_closes('TEST','2024-03-08','2024-03-11')

    def test_workspace_export_rejects_ambiguous_price_basis_and_other_tickers(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'workspace.csv'; path.write_text('Date,Close\n2024-03-11,11\n',encoding='utf-8')
            mapping={'date':'Date','close':'Close','ticker':'TEST','price_basis':'adjusted','session':'regular'}
            reference={'ticker':'TEST','date':'2024-03-11','close':'11','url':'https://exchange.test/official'}
            with self.assertRaises(ValueError): closes_reader.WorkspaceExportReader(path,mapping,reference)

    def test_workspace_xlsx_export_uses_selected_header_and_sheet(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'export.xlsx'; book=Workbook(); sheet=book.active; sheet.title='Prices'
            sheet.append(['Title']); sheet.append(['Date','Close']); sheet.append([datetime(2024,3,11),11]); book.save(path)
            mapping={'date':'Date','close':'Close','ticker':'TEST','price_basis':'official_unadjusted','session':'regular','coverage_start':'2024-03-11','coverage_end':'2024-03-11','sheet':'Prices','header_row':2}
            reference={'ticker':'TEST','date':'2024-03-11','close':'11','url':'https://exchange.test/official'}
            reader=closes_reader.WorkspaceExportReader(path,mapping,reference)
            self.assertEqual(reader.daily_closes('TEST','2024-03-11','2024-03-11')[0]['close'],'11')

class WorkspaceCandidateTests(unittest.TestCase):
    def test_candidate_reader_requests_unadjusted_daily_field_and_dated_values(self):
        class Frame:
            def to_dict(self,orient):
                return [{'Date':'2024-03-08','Close Price':10}, {'Date':'2024-03-11','Close Price':11}]
        class Fake:
            def __init__(self): self.calls=[]
            def get_data(self,**kwargs): self.calls.append(kwargs); return Frame()
        client=Fake()
        r=closes_reader.WorkspaceCandidateReader(client)
        rows=r.daily_closes('TEST.N','2024-03-08','2024-03-11')
        self.assertEqual([x['date'] for x in rows],['2024-03-08','2024-03-11'])
        self.assertEqual(client.calls[0]['fields'],['TR.CLOSEPRICE.date','TR.CLOSEPRICE(Adjusted=0)'])
        self.assertEqual(client.calls[0]['parameters']['Frq'],'D')
        self.assertTrue(all(x['verification']=='unverified candidate' for x in rows))
        self.assertEqual(r.last_close_before('TEST.N',datetime(2024,3,11,19,59,tzinfo=timezone.utc),start='2024-03-08')['date'],'2024-03-08')
        self.assertEqual(r.last_close_before('TEST.N',datetime(2024,3,11,20,0,tzinfo=timezone.utc),start='2024-03-08')['date'],'2024-03-08')

    def test_candidate_reader_rejects_ambiguous_columns_and_invalid_rows(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Fake:
            def __init__(self,rows): self.rows=rows
            def get_data(self,**kwargs): return Frame(self.rows)
        r=closes_reader.WorkspaceCandidateReader(Fake([{'Date':'2024-03-08','Close Price':float('inf')}]))
        with self.assertRaises(ValueError): r.daily_closes('TEST.N','2024-03-08','2024-03-11')
        r=closes_reader.WorkspaceCandidateReader(Fake([{'Other':'2024-03-08','Price':10}]))
        with self.assertRaises(ValueError): r.daily_closes('TEST.N','2024-03-08','2024-03-11')
        self.assertEqual(closes_reader.WorkspaceCandidateReader(Fake([])).daily_closes('TEST.N','2024-03-08','2024-03-11'),[])

    def test_missing_candidate_values_are_unavailable_and_mixed_gaps_fail_closed(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Fake:
            def __init__(self,rows): self.rows=rows
            def get_data(self,**kwargs): return Frame(self.rows)
        missing={'Date':'2024-03-08','Close Price':None}
        self.assertEqual(closes_reader.WorkspaceCandidateReader(Fake([missing])).daily_closes('TEST.N','2024-03-08','2024-03-11'),[])
        good={'Date':'2024-03-11','Close Price':11}
        with self.assertRaises(ValueError):
            closes_reader.WorkspaceCandidateReader(Fake([missing,good])).daily_closes('TEST.N','2024-03-08','2024-03-11')

    def test_candidate_check_returns_one_dated_close_or_not_available(self):
        class Frame:
            def __init__(self,rows): self.rows=rows
            def to_dict(self,orient): return self.rows
        class Fake:
            def __init__(self,rows): self.rows=rows
            def get_data(self,**kwargs): return Frame(self.rows)
        self.assertEqual(closes_reader.candidate_check(Fake([{'Date':'2024-03-08','Close Price':10}]),'TEST.N','2024-03-08'),{'date':'2024-03-08','close':'10','verification':'unverified candidate'})
        self.assertIsNone(closes_reader.candidate_check(Fake([]),'TEST.N','2024-03-08'))

    def test_workspace_open_requires_an_open_session(self):
        class State:
            def __init__(self,name): self.name=name
        class Session:
            def __init__(self,name): self.open_state=State(name)
        class Fake:
            def __init__(self,name): self.name=name; self.calls=[]
            def open_session(self,**kw): self.calls.append(kw); return Session(self.name)
        ok=Fake('Opened')
        self.assertEqual(closes_reader.open_workspace_session(ok,'secret').open_state.name,'Opened')
        self.assertEqual(ok.calls,[{'name':'desktop.workspace','app_key':'secret'}])
        with self.assertRaisesRegex(RuntimeError,'Workspace'):
            closes_reader.open_workspace_session(Fake('Closed'),'secret')
