"""Read saved worksheet views and calculate the observed post-filing reaction.

The command is read-only. It never changes a saved view or its timestamp.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo('America/New_York')


def as_moment(value, label):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label} must be an ISO date and time') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'{label} must include a time zone')
    return parsed.astimezone(EASTERN)


def load_bars(path, ticker):
    path = Path(path)
    if path.suffix.casefold() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
    else:
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = data.get('bars', data.get('data', [])) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError('Reader file must contain a bar list')
    result = []
    seen = set()
    for row in rows:
        if str(row.get('ticker', ticker)).strip().upper() != ticker.upper():
            continue
        if row.get('basis') != 'official_unadjusted' or row.get('session') != 'regular' or row.get('when_issued') is True:
            continue
        day = date.fromisoformat(str(row.get('date', '')))
        if day in seen:
            raise ValueError(f'Duplicate reader bar for {day.isoformat()}')
        try:
            close = Decimal(str(row.get('close', '')).replace(',', '').replace('$', ''))
        except InvalidOperation as exc:
            raise ValueError(f'Invalid reader close for {day.isoformat()}') from exc
        if not close.is_finite() or close <= 0:
            raise ValueError(f'Invalid reader close for {day.isoformat()}')
        seen.add(day)
        result.append((day, close))
    return sorted(result)


def calculate_reaction(view, worksheet_path):
    filing = as_moment(view.get('filing_time'), 'filing_time')
    view_time = as_moment(view.get('view_time'), 'view_time')
    ticker = str(view.get('ticker') or '').strip().upper()
    if not ticker:
        raise ValueError('A live release ticker is required')
    bars_ref = view.get('reader_file')
    if not bars_ref:
        raise ValueError('A reader_file is required')
    bars_path = Path(bars_ref)
    if not bars_path.is_absolute():
        bars_path = (Path(worksheet_path).parent / bars_path).resolve()
    bars = load_bars(bars_path, ticker)
    stamped = [(datetime.combine(day, time(16, 0), EASTERN), close) for day, close in bars]
    before = [(moment, close) for moment, close in stamped if moment < filing]
    after = [(moment, close) for moment, close in stamped if moment > filing]
    first_after = after[0] if after else None
    previous = before[-1] if before else None
    direction = str(view.get('direction') or '').strip().casefold()
    output = {
        'ticker': ticker,
        'filing_time': filing.isoformat(),
        'view_time': view_time.isoformat(),
        'direction': view.get('direction') or 'not computed',
        'reaction_percent': None,
        'agreement': 'not computed',
        'first_close_after_filing': first_after[0].isoformat() if first_after else None,
    }
    if first_after and view_time > first_after[0]:
        output['agreement'] = 'after'
        output['reason'] = 'The view was recorded after the first close following the filing.'
    if not first_after or not previous:
        output.setdefault('reason', 'The reader does not supply both a close before filing and a close after filing.')
        return output
    reaction = (first_after[1] - previous[1]) / previous[1] * Decimal('100')
    output['reaction_percent'] = str(reaction)
    output['reaction_from_close'] = str(previous[1])
    output['reaction_to_close'] = str(first_after[1])
    output['reaction_from_date'] = previous[0].date().isoformat()
    output['reaction_to_date'] = first_after[0].date().isoformat()
    if output['agreement'] == 'after':
        return output
    if direction not in {'more than price', 'less than price'}:
        output['reason'] = 'The saved view is not computed.'
    elif (direction == 'more than price' and reaction > 0) or (direction == 'less than price' and reaction < 0):
        output['agreement'] = 'agree'
    else:
        output['agreement'] = 'disagree'
    return output


def worksheet_views(root):
    root = Path(root)
    paths = sorted(root.rglob('worksheet.json')) if root.is_dir() else [root]
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            view = data.get('live_view')
            if not isinstance(view, dict):
                yield path, {'ticker': data.get('ticker', 'unknown'), 'agreement': 'not computed',
                             'direction': 'not computed', 'reason': 'live_view is missing'}
                continue
            yield path, calculate_reaction(view, path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            yield path, {'ticker': 'unknown', 'agreement': 'not computed', 'direction': 'not computed',
                         'reason': f'{type(exc).__name__}: {exc}'}


def print_table(rows):
    headers = ('Ticker', 'Filing time', 'View time', 'Direction', 'Reaction', 'Agreement')
    print(' | '.join(headers))
    print(' | '.join('---' for _ in headers))
    scored = [row for _, row in rows if row.get('reaction_percent') is not None and row.get('agreement') in {'agree', 'disagree'}]
    agreements = sum(row['agreement'] == 'agree' for row in scored)
    for _, row in rows:
        reaction = f"{Decimal(row['reaction_percent']):.2f}%" if row.get('reaction_percent') is not None else 'not computed'
        print(' | '.join(str(value or '') for value in (
            row.get('ticker', 'unknown'), row.get('filing_time', 'not known'), row.get('view_time', 'not known'),
            row.get('direction', 'not computed'), reaction, row.get('agreement', 'not computed'))))
    print(f'Agreements: {agreements}/{len(scored)} runs with a reaction; excluded after rows and views not computed.')


def main():
    parser = argparse.ArgumentParser(description='Print the read-only Lab 07 live-view reaction table')
    parser.add_argument('--runs', type=Path, required=True, help='Folder with saved worksheet runs')
    args = parser.parse_args()
    rows = list(worksheet_views(args.runs))
    if not rows:
        print('No worksheet.json files found.')
        print('Agreements: 0/0 runs with a reaction; excluded after rows and views not computed.')
        return
    print_table(rows)


if __name__ == '__main__':
    main()
