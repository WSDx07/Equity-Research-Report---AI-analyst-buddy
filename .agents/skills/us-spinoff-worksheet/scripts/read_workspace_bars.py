"""Read verified LSEG regular-way official closes and share volume."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SEEKER = ROOT / '.agents' / 'skills' / 'us-spinoff-seeker' / 'scripts'
sys.path.insert(0, str(SEEKER))
import seeker  # noqa: E402
import closes_reader  # noqa: E402


def read_env(path):
    values = {}
    for raw in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def select_evidence(path, cik=None):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict) and isinstance(data.get('evidence'), dict):
        data = data['evidence']
    if isinstance(data, dict) and {'ticker', 'ric', 'cik'}.issubset(data):
        evidence = data
    elif isinstance(data, dict):
        entries = list(data.values())
        if cik:
            entries = [entry for entry in entries if str(entry.get('cik', '')).zfill(10) == str(cik).zfill(10)]
        if len(entries) != 1:
            raise ValueError('Evidence file must identify exactly one regular-way listing')
        evidence = entries[0]
    else:
        raise ValueError('Invalid listing evidence JSON')
    required = ('cik', 'ticker', 'ric', 'exchange', 'listing_url', 'regular_way',
                'exchange_url', 'reference_date', 'reference_close')
    missing = [field for field in required if evidence.get(field) in (None, '')]
    if missing:
        raise ValueError('Listing evidence is missing: ' + ', '.join(missing))
    if evidence.get('regular_way') is not True:
        raise ValueError('Listing evidence must identify regular-way trading')
    if not str(evidence['cik']).isdigit():
        raise ValueError('Invalid listing CIK')
    date.fromisoformat(str(evidence['reference_date']))
    return dict(evidence)


def main():
    parser = argparse.ArgumentParser(description='Export verified LSEG official closes and share volume outside the repository')
    parser.add_argument('--env', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True, help='SEC listing and independent exchange spot-check evidence JSON')
    parser.add_argument('--start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='YYYY-MM-DD')
    parser.add_argument('--output', type=Path, required=True, help='JSON output outside the repository')
    args = parser.parse_args()
    first = date.fromisoformat(args.start); last = date.fromisoformat(args.end)
    if last < first:
        raise ValueError('end date precedes start date')
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Keep licensed LSEG bar history outside the repository')
    settings = read_env(args.env)
    app_key = (settings.get('LSEG_APP_KEY') or '').strip()
    if not app_key:
        raise ValueError('LSEG_APP_KEY is missing from the selected .env file')
    sec_client = seeker.SecClient((settings.get('SEC_USER_AGENT') or '').strip())
    evidence = select_evidence(args.evidence)
    import lseg.data as ld
    try:
        seeker.open_workspace_session(ld, app_key)
        reader = closes_reader.WorkspaceOfficialReader(
            ld, evidence, lambda item: seeker.verify_regular_listing(item, sec_client))
        bars = reader.daily_bars(first.isoformat(), last.isoformat())
    finally:
        ld.close_session()
    result = {
        'ticker': str(evidence['ticker']).upper(),
        'cik': str(evidence['cik']).zfill(10),
        'ric': evidence['ric'],
        'exchange': evidence['exchange'],
        'listing_url': evidence['listing_url'],
        'requested_start': first.isoformat(),
        'requested_end': last.isoformat(),
        'basis': 'official_unadjusted',
        'session': 'regular',
        'when_issued': False,
        'reader_fields': ['TR.OFFICIALCLOSEPRICE(Adjusted=0)', 'TR.Volume'],
        'exchange_spot_check': {'date': evidence['reference_date'], 'close': str(evidence['reference_close']),
                                'url': evidence['exchange_url']},
        'bars': bars,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Ticker: {result['ticker']}")
    print(f"Bars written: {len(bars)}")
    print(f'Output: {output}')


if __name__ == '__main__':
    main()
