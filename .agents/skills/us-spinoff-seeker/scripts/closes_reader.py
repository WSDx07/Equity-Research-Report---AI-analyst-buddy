"""Read a local export labeled as official unadjusted regular-session closes.

The labels and source must be independently checked against an exchange before use.
Raw data should remain outside the repository and language-model inputs.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

EASTERN = ZoneInfo('America/New_York')


def financial_datasets_prices(key, ticker, start, end, fetch=None):
    """Return vendor bars in memory; their official/unadjusted status is unverified."""
    if not key or not ticker: raise ValueError('API key and ticker are required')
    if date.fromisoformat(end) < date.fromisoformat(start): raise ValueError('Invalid date range')
    def default_fetch(url,headers):
        with urlopen(Request(url,headers=headers),timeout=30) as response:
            return json.load(response)
    fetch=fetch or default_fetch
    query=urlencode({'ticker':ticker,'interval':'day','start_date':start,'end_date':end})
    url='https://api.financialdatasets.ai/prices/?'+query
    headers={'X-API-KEY':key, 'Accept':'application/json'}
    rows=[]
    visited=set()
    while url:
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.netloc!='api.financialdatasets.ai' or parsed.path.rstrip('/')!='/prices':
            raise ValueError('Unsafe Financial Datasets pagination URL')
        if url in visited: raise ValueError('Repeated pagination URL')
        visited.add(url)
        data=fetch(url,headers)
        prices=data.get('prices')
        if not isinstance(prices,list): raise ValueError('Invalid price response')
        rows.extend(prices)
        url=data.get('next_page_url')
    return rows


def check_exchange_close(key,ticker,day,reference,vendor_fetch=None):
    """Compare one vendor bar with an independently supplied exchange observation."""
    date.fromisoformat(day)
    if not reference.get('url') or reference.get('date')!=day or reference.get('close') is None:
        raise ValueError('A dated exchange observation and source URL are required')
    vendor=financial_datasets_prices(key,ticker,day,day,vendor_fetch)
    bars=[row for row in vendor if str(row.get('time',''))[:10]==day]
    result={'ticker':ticker,'date':day,'exchange_url':reference['url'],'matches':None}
    if len(bars)==1:
        result['matches']=matches_exchange({'date':day,'close':bars[0].get('close')},reference)
    return result


def daily_closes(path: str | Path, ticker: str, start: str, end: str) -> list[dict]:
    start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    if end_date < start_date:
        raise ValueError('end date precedes start date')
    records = []
    seen = set()
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        required = {'ticker', 'date', 'close', 'basis', 'session'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('The export does not contain required close metadata')
        for row in reader:
            if row['ticker'].strip().upper() != ticker.strip().upper():
                continue
            if row['basis'] != 'official_unadjusted' or row['session'] != 'regular':
                continue
            day = date.fromisoformat(row['date'])
            if not start_date <= day <= end_date:
                continue
            try:
                close = Decimal(row['close'])
            except InvalidOperation as exc:
                raise ValueError('Invalid close') from exc
            if not close.is_finite() or close <= 0 or day in seen:
                raise ValueError('Invalid or duplicate official close')
            seen.add(day)
            records.append({'date': day.isoformat(), 'close': str(close)})
    return sorted(records, key=lambda row: row['date'])


def last_close_before(path: str | Path, ticker: str, moment: datetime) -> dict | None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('Date and time must include a time zone')
    eastern = moment.astimezone(EASTERN)
    rows = daily_closes(path, ticker, '1900-01-01', eastern.date().isoformat())
    eligible = [r for r in rows if datetime.combine(date.fromisoformat(r['date']), time(16), EASTERN) < eastern]
    return eligible[-1] if eligible else None


def matches_exchange(close: dict, reference: dict) -> bool:
    try:
        return (bool(reference.get('url')) and close['date'] == reference['date']
                and Decimal(str(close['close'])) == Decimal(str(reference['close'])))
    except (KeyError, InvalidOperation, TypeError):
        return False


def _normalized_lseg_key(value):
    return ''.join(character for character in str(value).casefold() if character.isalnum())


def _lseg_value(row, aliases, label):
    wanted = {_normalized_lseg_key(value) for value in aliases}
    matches = [value for key, value in row.items() if _normalized_lseg_key(key) in wanted]
    if len(matches) != 1:
        raise ValueError(f'Unrecognized LSEG {label} response column')
    return matches[0]


def _parse_share_volume(value):
    try:
        volume = Decimal(str(value).strip().replace(',', ''))
    except (InvalidOperation, TypeError, AttributeError) as exc:
        raise ValueError('Invalid share volume') from exc
    if not volume.is_finite() or volume < 0 or volume != volume.to_integral_value():
        raise ValueError('Invalid share volume')
    return str(volume)


class WorkspaceExportReader:
    """Read a mapped LSEG web export after a user-supplied exchange spot check.

    Mapping and exchange reference must be independently verified; matching one
    observation does not prove that the complete series is official/unadjusted.
    """
    def __init__(self,path,mapping,reference,workspace_root=None):
        self.path=Path(path).resolve()
        if workspace_root and self.path.is_relative_to(Path(workspace_root).resolve()):
            raise ValueError('Keep the raw export outside the workspace')
        if mapping.get('price_basis')!='official_unadjusted' or mapping.get('session')!='regular':
            raise ValueError('Export must identify unadjusted official regular-way closes')
        self.mapping=dict(mapping)
        self.ticker=str(mapping.get('ticker','')).strip().upper()
        if not self.ticker or not mapping.get('date') or not mapping.get('close'):
            raise ValueError('Ticker, date column, and close column are required')
        try:
            self.coverage_start=date.fromisoformat(mapping['coverage_start'])
            self.coverage_end=date.fromisoformat(mapping['coverage_end'])
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError('Export coverage dates are required') from exc
        if self.coverage_end<self.coverage_start: raise ValueError('Invalid export coverage')
        if reference.get('ticker','').upper()!=self.ticker:
            raise ValueError('Exchange reference ticker does not match export')
        self.digest=hashlib.sha256(self.path.read_bytes()).digest()
        rows=self._read_rows()
        candidates=[r for r in rows if r['date']==reference.get('date')]
        if len(candidates)!=1 or not matches_exchange(candidates[0],reference):
            raise ValueError('Exchange spot check missing or does not match')

    def _read_rows(self):
        if hashlib.sha256(self.path.read_bytes()).digest()!=self.digest:
            raise ValueError('Export changed after exchange spot check; verify it again')
        suffix=self.path.suffix.lower()
        if suffix=='.csv':
            with self.path.open(encoding='utf-8-sig',newline='') as file:
                source=list(csv.DictReader(file))
        elif suffix=='.xlsx':
            from openpyxl import load_workbook
            book=load_workbook(self.path,read_only=True,data_only=True)
            try:
                sheet=book[self.mapping['sheet']] if self.mapping.get('sheet') else book.active
                rows=sheet.iter_rows(values_only=True)
                for _ in range(int(self.mapping.get('header_row',1))-1): next(rows)
                header=next(rows)
                source=[dict(zip(header,row)) for row in rows]
            finally: book.close()
        else: raise ValueError('Expected a CSV or XLSX export')
        result=[]; seen=set()
        for row in source:
            raw_date=row.get(self.mapping['date']); raw_close=row.get(self.mapping['close'])
            if raw_date in (None,'') and raw_close in (None,''): continue
            if raw_date in (None,'') or raw_close in (None,''): raise ValueError('Incomplete date or close')
            if isinstance(raw_date,datetime): day=raw_date.date()
            elif isinstance(raw_date,date): day=raw_date
            else:
                try: day=datetime.strptime(str(raw_date).strip(),self.mapping.get('date_format','%Y-%m-%d')).date()
                except ValueError as exc: raise ValueError('Invalid date in export') from exc
            try: close=Decimal(str(raw_close).strip().replace(',',''))
            except InvalidOperation as exc: raise ValueError('Invalid close in export') from exc
            if not close.is_finite() or close<=0 or day in seen: raise ValueError('Invalid or duplicate close')
            item={'ticker':self.ticker,'date':day.isoformat(),'close':str(close),
                  'basis':'official_unadjusted','session':'regular','when_issued':False}
            if self.mapping.get('volume'):
                raw_volume=row.get(self.mapping['volume'])
                if raw_volume in (None, ''): raise ValueError('Share volume is missing in export')
                item['volume']=_parse_share_volume(raw_volume)
            seen.add(day); result.append(item)
        if hashlib.sha256(self.path.read_bytes()).digest()!=self.digest:
            raise ValueError('Export changed while reading')
        return sorted(result,key=lambda r:r['date'])

    def daily_closes(self,ticker,start,end):
        if ticker.strip().upper()!=self.ticker: raise ValueError('Ticker does not match export')
        first=date.fromisoformat(start); last=date.fromisoformat(end)
        if last<first: raise ValueError('end date precedes start date')
        if first<self.coverage_start or last>self.coverage_end: raise ValueError('Requested dates exceed declared export coverage')
        return [r for r in self._read_rows() if first<=date.fromisoformat(r['date'])<=last]

    def daily_bars(self,ticker,start,end):
        if not self.mapping.get('volume'):
            raise ValueError('Export mapping must identify a share-volume column')
        return self.daily_closes(ticker,start,end)

    def last_close_before(self,ticker,moment):
        if moment.tzinfo is None or moment.utcoffset() is None: raise ValueError('Date and time must include a time zone')
        eastern=moment.astimezone(EASTERN)
        rows=self.daily_closes(ticker,self.coverage_start.isoformat(),eastern.date().isoformat())
        eligible=[r for r in rows if datetime.combine(date.fromisoformat(r['date']),time(16),EASTERN)<eastern]
        return eligible[-1] if eligible else None


class WorkspaceCandidateReader:
    """Read a candidate unadjusted LSEG field; its official/regular-way status is unverified."""
    def __init__(self, client):
        self.client=client

    def daily_closes(self, ticker, start, end):
        first=date.fromisoformat(start); last=date.fromisoformat(end)
        if not ticker or last<first: raise ValueError('Ticker and valid date range are required')
        frame=self.client.get_data(universe=[ticker],fields=['TR.CLOSEPRICE.date','TR.CLOSEPRICE(Adjusted=0)'],parameters={'SDate':start,'EDate':end,'Frq':'D'})
        rows=frame.to_dict('records')
        output=[]; seen=set(); missing=0
        for row in rows:
            date_keys=[k for k in row if str(k).lower() in {'date','tr.closeprice.date'}]
            price_keys=[k for k in row if str(k).lower() in {'close price','tr.closeprice','tr.closeprice(adjusted=0)'}]
            if len(date_keys)!=1 or len(price_keys)!=1: raise ValueError('Unrecognized LSEG response columns')
            raw_day=row[date_keys[0]]; raw_price=row[price_keys[0]]
            absent=lambda value: value is None or str(value).strip().casefold() in {'','<na>','nan','nat','none'}
            if absent(raw_price):
                missing+=1
                continue
            if absent(raw_day): raise ValueError('Candidate close is missing its date')
            try:
                day=date.fromisoformat(str(raw_day)[:10]); price=Decimal(str(raw_price))
            except (ValueError,InvalidOperation,TypeError) as exc: raise ValueError('Invalid candidate close') from exc
            if not price.is_finite() or price<=0 or day in seen or not first<=day<=last: raise ValueError('Invalid or duplicate candidate close')
            seen.add(day)
            output.append({'date':day.isoformat(),'close':str(price),'verification':'unverified candidate'})
        if output and missing: raise ValueError('Candidate history contains missing observations')
        return sorted(output,key=lambda item:item['date'])

    def daily_bars(self, ticker, start, end):
        first=date.fromisoformat(start); last=date.fromisoformat(end)
        if not ticker or last<first: raise ValueError('Ticker and valid date range are required')
        frame=self.client.get_data(universe=[ticker],fields=[
            'TR.CLOSEPRICE.date','TR.CLOSEPRICE(Adjusted=0)','TR.Volume'],
            parameters={'SDate':start,'EDate':end,'Frq':'D'})
        output=[]; seen=set(); missing=0
        for row in frame.to_dict('records'):
            raw_day=_lseg_value(row,('Date','TR.CLOSEPRICE.date'),'date')
            raw_price=_lseg_value(row,('Close Price','TR.CLOSEPRICE','TR.CLOSEPRICE(Adjusted=0)'),'close')
            raw_volume=_lseg_value(row,('Volume','TR.Volume'),'volume')
            absent=lambda value: value is None or str(value).strip().casefold() in {'','<na>','nan','nat','none'}
            if absent(raw_price):
                missing+=1
                continue
            if absent(raw_day) or absent(raw_volume): raise ValueError('Candidate date or volume is missing')
            try:
                day=date.fromisoformat(str(raw_day)[:10]); price=Decimal(str(raw_price).replace(',',''))
            except (ValueError,InvalidOperation,TypeError) as exc: raise ValueError('Invalid candidate close') from exc
            volume=_parse_share_volume(raw_volume)
            if not price.is_finite() or price<=0 or day in seen or not first<=day<=last: raise ValueError('Invalid or duplicate candidate close')
            seen.add(day)
            output.append({'ticker':str(ticker).strip().upper(),'date':day.isoformat(),'close':str(price),'volume':volume,
                           'verification':'unverified candidate','basis':'candidate_unadjusted',
                           'source':'LSEG TR.CLOSEPRICE(Adjusted=0), TR.Volume'})
        if output and missing: raise ValueError('Candidate history contains missing observations')
        return sorted(output,key=lambda item:item['date'])

    def last_close_before(self,ticker,moment,start='1900-01-01'):
        if moment.tzinfo is None or moment.utcoffset() is None: raise ValueError('Date and time must include a time zone')
        eastern=moment.astimezone(EASTERN)
        rows=self.daily_closes(ticker,start,eastern.date().isoformat())
        eligible=[r for r in rows if datetime.combine(date.fromisoformat(r['date']),time(16),EASTERN)<eastern]
        return eligible[-1] if eligible else None


class WorkspaceOfficialReader:
    """Use dated LSEG official-close observations after independent identity and exchange checks.

    listing_verifier must independently read the cited listing evidence and verify
    CIK, ticker, RIC and regular-way identity. An exchange comparison applies only
    to the instrument and reference observation supplied in evidence.
    """
    def __init__(self,client,evidence,listing_verifier):
        from urllib.parse import urlparse
        self.client=client
        self.evidence=dict(evidence)
        e=self.evidence
        if (not str(e.get('cik','')).isdigit() or not e.get('ticker') or not e.get('ric')
            or e.get('regular_way') is not True or not callable(listing_verifier)):
            raise ValueError('Verified regular-way listing identity required')
        url=urlparse(str(e.get('exchange_url','')))
        if url.scheme!='https' or not url.netloc: raise ValueError('Exchange reference URL required')
        if not listing_verifier(e): raise ValueError('Regular-way listing evidence did not verify')
        exchange=str(e.get('exchange','')).strip()
        if not exchange: raise ValueError('Listing exchange required')
        results=client.discovery.search(query=e['ticker'],view=client.discovery.Views.EQUITY_QUOTES,
            select='RIC,TickerSymbol,ExchangeName,AssetState',top=100).to_dict('records')
        matches=[row for row in results if str(row.get('TickerSymbol','')).strip().upper()==str(e['ticker']).strip().upper()
                 and str(row.get('RIC',''))==str(e['ric']) and str(row.get('AssetState','')).upper()=='AC'
                 and str(row.get('ExchangeName','')).strip().casefold()==exchange.casefold()]
        if len(matches)!=1: raise ValueError('LSEG listing-exchange quote missing or ambiguous')
        date.fromisoformat(e.get('reference_date',''))
        reference=self.daily_closes(e['reference_date'],e['reference_date'])
        if len(reference)!=1 or not matches_exchange(reference[0],{'date':e['reference_date'],'close':e.get('reference_close'),'url':e['exchange_url']}):
            raise ValueError('Official close did not match exchange reference')

    def daily_closes(self,start,end):
        first=date.fromisoformat(start); last=date.fromisoformat(end)
        if last<first: raise ValueError('end date precedes start date')
        frame=self.client.get_data(universe=[self.evidence['ric']],
            fields=['TR.OFFICIALCLOSEPRICE.date','TR.OFFICIALCLOSEPRICE(Adjusted=0)'],
            parameters={'SDate':start,'EDate':end,'Frq':'D'})
        out=[]; seen=set()
        for row in frame.to_dict('records'):
            day_value=row.get('Date'); close_value=row.get('Official Close Price')
            if str(day_value).strip().casefold() in {'','none','nat','nan','<na>'} or str(close_value).strip().casefold() in {'','none','nan','<na>'}:
                raise ValueError('Official close or date is missing')
            try: day=date.fromisoformat(str(day_value)[:10]); close=Decimal(str(close_value))
            except (ValueError,TypeError,InvalidOperation) as exc: raise ValueError('Invalid official close') from exc
            if day in seen or not first<=day<=last or not close.is_finite() or close<=0:
                raise ValueError('Invalid or duplicate official close')
            seen.add(day)
            out.append({'date':day.isoformat(),'close':str(close),'when_issued':False,
                        'basis':'official_unadjusted','source':'LSEG TR.OFFICIALCLOSEPRICE; exchange spot check: '+self.evidence['exchange_url']})
        return sorted(out,key=lambda x:x['date'])

    def daily_bars(self,start,end):
        first=date.fromisoformat(start); last=date.fromisoformat(end)
        if last<first: raise ValueError('end date precedes start date')
        frame=self.client.get_data(universe=[self.evidence['ric']],fields=[
            'TR.OFFICIALCLOSEPRICE.date','TR.OFFICIALCLOSEPRICE(Adjusted=0)','TR.Volume'],
            parameters={'SDate':start,'EDate':end,'Frq':'D'})
        out=[]; seen=set()
        for row in frame.to_dict('records'):
            day_value=_lseg_value(row,('Date','TR.OFFICIALCLOSEPRICE.date'),'date')
            close_value=_lseg_value(row,('Official Close Price','TR.OFFICIALCLOSEPRICE',
                                          'TR.OFFICIALCLOSEPRICE(Adjusted=0)'),'official close')
            volume_value=_lseg_value(row,('Volume','TR.Volume'),'volume')
            absent=lambda value: value is None or str(value).strip().casefold() in {'','none','nat','nan','<na>'}
            if absent(day_value) or absent(close_value) or absent(volume_value):
                raise ValueError('Official close, date, or share volume is missing')
            try: day=date.fromisoformat(str(day_value)[:10]); close=Decimal(str(close_value).replace(',',''))
            except (ValueError,TypeError,InvalidOperation) as exc: raise ValueError('Invalid official close') from exc
            volume=_parse_share_volume(volume_value)
            if day in seen or not first<=day<=last or not close.is_finite() or close<=0:
                raise ValueError('Invalid or duplicate official close')
            seen.add(day)
            out.append({'ticker':str(self.evidence['ticker']).strip().upper(),'date':day.isoformat(),'close':str(close),'volume':volume,
                        'when_issued':False,'basis':'official_unadjusted','session':'regular',
                        'source':'LSEG TR.OFFICIALCLOSEPRICE(Adjusted=0), TR.Volume; exchange spot check: '+self.evidence['exchange_url']})
        return sorted(out,key=lambda x:x['date'])

    def last_close_before(self,moment,start):
        if moment.tzinfo is None or moment.utcoffset() is None: raise ValueError('Date and time must include a time zone')
        end=completed_close_end(moment.astimezone(EASTERN).date().isoformat(),moment)
        if date.fromisoformat(end)<date.fromisoformat(start): return None
        rows=self.daily_closes(start,end)
        return rows[-1] if rows else None

    def factor_snapshot(self,cik,distribution,end):
        if not str(cik).isdigit() or int(cik)!=int(self.evidence['cik']): raise ValueError('Registrant CIK does not match listing')
        distribution_day=date.fromisoformat(distribution); end_day=date.fromisoformat(end)
        if end_day<=distribution_day: raise ValueError('No completed post-distribution date')
        rows=self.daily_closes(distribution,end)
        eligible=[row for row in rows if date.fromisoformat(row['date'])>distribution_day]
        expected=distribution_day+timedelta(days=1)
        while expected.weekday()>=5: expected+=timedelta(days=1)
        first=None
        if eligible and eligible[0]['date']==expected.isoformat(): first=dict(eligible[0],verified_first=True)
        return {'first':first,'last':eligible[-1] if eligible else None}

def completed_close_end(requested,now):
    """Limit requests to dates whose 4 p.m. Eastern close has passed."""
    if now.tzinfo is None or now.utcoffset() is None: raise ValueError('A timezone-aware clock is required')
    day=date.fromisoformat(requested)
    eastern=now.astimezone(EASTERN)
    last=eastern.date() if eastern.time()>time(16) else eastern.date()-timedelta(days=1)
    return min(day,last).isoformat()

class WorkspaceCandidateProbe:
    """Probe LSEG candidates without treating them as verified scoring inputs."""
    def __init__(self,client,ticker_data):
        self.client=client
        self.ticker_data=ticker_data

    def __call__(self,record,today):
        import re
        cik=str(record.get('cik',''))
        if not cik.isdigit(): raise ValueError('Registrant CIK unavailable')
        symbols={str(row.get('ticker','')).strip().upper() for row in self.ticker_data.values()
                 if str(row.get('cik_str','')).isdigit() and int(row['cik_str'])==int(cik)}
        if len(symbols)!=1: raise ValueError('SEC ticker mapping missing or ambiguous')
        ticker=next(iter(symbols))
        if not re.fullmatch(r'[A-Z0-9.\-]{1,20}',ticker): raise ValueError('Invalid SEC ticker')
        frame=self.client.discovery.search(query=ticker,view=self.client.discovery.Views.EQUITY_QUOTES,
            select='RIC,TickerSymbol,ExchangeName,IsPrimaryRIC,AssetState',top=100)
        matches=[]
        for row in frame.to_dict('records'):
            if (str(row.get('TickerSymbol','')).strip().upper()==ticker
                and str(row.get('IsPrimaryRIC','')).casefold() in {'true','1'}
                and str(row.get('AssetState','')).strip().upper()=='AC'
                and row.get('ExchangeName') and row.get('RIC')):
                matches.append(str(row['RIC']))
        if len(matches)!=1: raise ValueError('LSEG primary quote missing or ambiguous')
        start=record.get('distribution_date')
        start_day=date.fromisoformat(start)
        end=completed_close_end(today,datetime.now(EASTERN))
        rows=WorkspaceCandidateReader(self.client).daily_closes(matches[0],start,end) if start_day<=date.fromisoformat(end) else []
        return {'candidate_count':len(rows),'limitations':[
            'LSEG candidate observations are excluded from scoring: regular-way identity and first-close completeness have not been established.'
        ]}

def candidate_check(client,ticker,day):
    rows=WorkspaceCandidateReader(client).daily_closes(ticker,day,day)
    return rows[0] if rows else None


def open_workspace_session(client,key):
    if not key: raise ValueError('LSEG_APP_KEY is required')
    session=client.open_session(name='desktop.workspace',app_key=key)
    if getattr(getattr(session,'open_state',None),'name',None)!='Opened':
        raise RuntimeError('LSEG Workspace desktop session did not open; verify the desktop login and App Key')
    return session


def candidate_cli():
    import argparse
    from dotenv import dotenv_values
    parser=argparse.ArgumentParser(description='Check one LSEG candidate close; run yourself and compare with the listing exchange')
    parser.add_argument('--env',type=Path,required=True)
    parser.add_argument('--ticker',required=True,help='LSEG regular-way instrument identifier, verified by you')
    parser.add_argument('--date',required=True,help='Trading date YYYY-MM-DD')
    args=parser.parse_args()
    date.fromisoformat(args.date)
    key=dotenv_values(args.env).get('LSEG_APP_KEY')
    if not key: raise SystemExit('LSEG_APP_KEY is missing from the specified .env file.')
    import lseg.data as ld
    try:
        open_workspace_session(ld,key)
        result=candidate_check(ld,args.ticker,args.date)
        if result: print(f"{args.ticker} | {result['date']} | {result['close']} | unverified candidate close")
        else: print('not available')
    finally:
        ld.close_session()

if __name__=='__main__': candidate_cli()
