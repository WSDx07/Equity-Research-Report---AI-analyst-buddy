"""Export LSEG closes using the user's stated interpretation of the field."""
import argparse
import json
from pathlib import Path
import sys

from read_workspace_bars import ROOT, read_env
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'us-spinoff-seeker' / 'scripts'))
import closes_reader


def main():
    p = argparse.ArgumentParser()
    for name in ('env', 'ticker', 'cik', 'ric', 'exchange', 'start', 'end', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    output = Path(a.output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Keep licensed LSEG history outside the repository')
    if not a.cik.isdigit():
        raise ValueError('CIK must be numeric')
    import lseg.data as ld
    try:
        closes_reader.open_workspace_session(ld, read_env(a.env).get('LSEG_APP_KEY'))
        metadata = ld.get_data(universe=[a.ric], fields=['TR.IsPrimaryQuote', 'TR.ExchangeName', 'TR.InstrumentType']).to_dict('records')
        if len(metadata) != 1:
            raise ValueError('Instrument metadata is missing or ambiguous')
        row = metadata[0]
        if (str(row.get('Primary Quote Flag')) != '1' or
                str(row.get('Exchange Name', '')).casefold() != a.exchange.casefold() or
                str(row.get('Instrument Type', '')).casefold() != 'ordinary shares'):
            raise ValueError('Primary quote, exchange, or ordinary share metadata does not match')
        if a.ric.split('.')[0].upper() != a.ticker.upper():
            raise ValueError('RIC does not match ticker')
        bars = closes_reader.WorkspaceCandidateReader(ld).daily_bars(a.ric, a.start, a.end)
    finally:
        ld.close_session()
    for bar in bars:
        bar.update(ticker=a.ticker.upper(), basis='official_unadjusted', session='regular', when_issued=False)
    result = {'ticker': a.ticker.upper(), 'cik': a.cik.zfill(10), 'ric': a.ric,
              'basis': 'user_asserted_official_unadjusted', 'session': 'regular', 'when_issued': False,
              'reader_fields': ['TR.CLOSEPRICE(Adjusted=0)', 'TR.Volume'],
              'limitation': 'Official unadjusted regular-way status is based on the user-provided field interpretation; independent exchange comparison was not completed.',
              'bars': bars}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{a.ticker.upper()}: {len(bars)} bars written to {output}')


if __name__ == '__main__':
    main()
