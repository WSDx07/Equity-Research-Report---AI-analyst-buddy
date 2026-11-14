"""Check every numeric claim in a saved worksheet against its source or formula.

The guard reads the worksheet Markdown directly. It does not use an auxiliary
claims file. The small JSON file used by the lifecycle hook stores only the path
of the current worksheet and the Codex turn that created it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import statistics
import sys
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from worksheet_math import dec, read_rules  # noqa: E402


MARKER = re.compile(r'\[(fact|filing|calc|rule|price)\s+([^\]]+)\]', re.I)
NUMBER = re.compile(r'(?<![A-Za-z])[-+]?\$?\(?\d[\d,]*(?:\.\d+)?\)?%?(?![A-Za-z])')
IDENTIFIERS = (
    re.compile(r'\b(?:CIK|line|page|accession|form|item|section|fiscal\s+year|FY|Q[1-4])\s*[:#-]?\s*\d+(?:\.\d+)*', re.I),
    re.compile(r'\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?\b', re.I),
    re.compile(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b', re.I),
    re.compile(r'\b\d{4}\s+Q[1-4]\b', re.I),
    re.compile(r'\b\d{18,20}\b'),
    re.compile(r'https?://\S+', re.I),
    re.compile(r'\b\d+\s*[-/]\s*(?:K|Q|A|B|G)\b', re.I),
)


def parse_marker(text):
    try:
        parts = shlex.split(text)
    except ValueError as exc:
        raise ValueError('Malformed claim marker') from exc
    fields = {}
    for part in parts:
        if '=' not in part:
            fields.setdefault('id', part)
        else:
            key, value = part.split('=', 1)
            fields[key] = value
    return fields


def visible_numbers(line):
    text = MARKER.sub('', line)
    text = re.sub(r'<!--.*?-->', '', text)
    text = re.sub(r'\[[^\]]*\]\([^)]*\)', '', text)
    # A leading Markdown section or list number is an outline identifier.
    text = re.sub(r'^\s*(?:#{1,6}\s*)?\d+(?:\.\d+)*[.)]?\s+', '', text)
    for pattern in IDENTIFIERS:
        text = pattern.sub(' ', text)
    return [token for token in NUMBER.findall(text)]


def number_value(token):
    value = token.replace('$', '').replace(',', '').replace('%', '').strip()
    if value.startswith('(') and value.endswith(')'):
        value = '-' + value[1:-1]
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'Invalid number {token}') from exc


def source_file(run, field):
    value = Path(field)
    target = value.resolve() if value.is_absolute() else (run / value).resolve()
    if not target.is_relative_to(run.resolve()):
        raise ValueError('Filing source must remain inside the saved run folder')
    if not target.is_file():
        raise ValueError(f'Source file does not exist: {field}')
    return target


def line_numbers(path, line_number):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    if line_number < 1 or line_number > len(lines):
        raise ValueError(f'Source line {line_number} does not exist in {path.name}')
    line = lines[line_number - 1]
    line = re.sub(r'^\s*\d{6}\s*\|\s*', '', line)
    return [number_value(token) for token in visible_numbers(line)]


def facts_value(run, concept, period, filename='facts.json'):
    path = source_file(run, filename)
    data = json.loads(path.read_text(encoding='utf-8'))
    record = data.get('concepts', {}).get(concept)
    if not isinstance(record, dict):
        raise ValueError(f'Unknown saved fact: {concept} ({period})')
    if period in {'current', 'prior'}:
        entry = record.get(period)
    else:
        wanted_year = re.fullmatch(r'FY(\d{4})', period, re.I)
        entries = [value for name, value in record.items() if name in {'current', 'prior'} and isinstance(value, dict)]
        if wanted_year:
            entries = [value for value in entries if str(value.get('fy', '')) == wanted_year.group(1)
                       or str(value.get('end', '')).startswith(wanted_year.group(1))]
        else:
            entries = [value for value in entries if value.get('end') == period]
        entry = entries[0] if len(entries) == 1 else None
    if not isinstance(entry, dict) or entry.get('val') in (None, ''):
        raise ValueError(f'Saved fact is not available: {concept} ({period})')
    return Decimal(str(entry['val']))


def read_bars(path, ticker):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = data.get('bars', data.get('data', [])) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError('Reader file must contain a list of bars')
    result = []
    for row in rows:
        if str(row.get('ticker', ticker)).upper() != ticker.upper():
            continue
        if row.get('basis') != 'official_unadjusted' or row.get('session') != 'regular' or row.get('when_issued') is True:
            continue
        result.append({'date': date.fromisoformat(str(row['date'])).isoformat(),
                       'close': dec(row.get('close'), 'reader close'),
                       'volume': dec(row.get('volume'), 'reader share volume')})
    return result


def compare_tokens(claimed, supported, where):
    if not claimed:
        return None
    if not supported:
        return f'{where} has no numeric source value'
    for value in claimed:
        if value not in supported:
            return f'{where} does not contain {value}'
    return None


def label_number(text, label):
    pattern = re.compile(rf'^\s*(?:[-*]\s*)?{re.escape(label)}\s*[:=]\s*(.+)$', re.I | re.M)
    match = pattern.search(text)
    if not match:
        raise ValueError(f'Printed input is missing: {label}')
    values = visible_numbers(match.group(1))
    if len(values) != 1:
        raise ValueError(f'Printed input must have one number: {label}')
    number = number_value(values[0])
    if '%' in values[0]:
        number /= Decimal('100')
    return number


def expected_calculation(text, line_text, calc_id, rules, reader_path, live_reader_path, fields):
    key = calc_id.casefold()
    if key == 'owner_cash_flow':
        earnings = label_number(text, 'After-tax earnings')
        depreciation = label_number(text, 'Depreciation')
        capex = label_number(text, 'Capital spending')
        return [earnings + depreciation - capex]
    if key in {'low_equity_value', 'mid_equity_value'}:
        ocf = label_number(text, 'Owner cash flow')
        rate = label_number(text, f'{key[:3].title()} case discount rate')
        growth = label_number(text, f'{key[:3].title()} case growth rate')
        if rate <= growth:
            raise ValueError('Discount rate must exceed growth rate')
        return [ocf * (Decimal('1') + growth) / (rate - growth)]
    if key in {'low_value_per_share', 'mid_value_per_share'}:
        case = key.split('_')[0]
        equity = label_number(text, f'{case.title()} case equity value')
        shares = label_number(text, 'Diluted shares')
        if shares <= 0:
            raise ValueError('Diluted shares must be positive')
        return [equity / shares]
    if key == 'margin_of_safety':
        low = label_number(text, 'Low case value per share')
        price = label_number(text, 'Dated market price')
        if price <= 0:
            raise ValueError('Dated market price must be positive')
        return [(low - price) / price * Decimal('100')]
    if key == 'daily_dollar_volume':
        match = re.search(r'Liquidity bar:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*dollar_volume=([^\s\[]+)', line_text, re.I)
        if not match:
            raise ValueError('Use this marker on a dated Liquidity bar line with a dollar volume')
        ticker = fields.get('ticker')
        selected_reader = live_reader_path if fields.get('reader') == 'live' else reader_path
        if not ticker or not selected_reader:
            raise ValueError('Liquidity bar marker needs a ticker and reader file')
        bars = read_bars(selected_reader, ticker)
        candidates = [bar for bar in bars if bar['date'] == match.group(1)]
        if len(candidates) != 1:
            raise ValueError(f'No unique reader bar for {ticker} on {match.group(1)}')
        expected = candidates[0]['close'] * candidates[0]['volume']
        if number_value(match.group(2)) != expected:
            raise ValueError(f'Reader dollar volume does not match close x volume on {match.group(1)}')
        return [expected]
    if key == 'median_dollar_volume':
        printed = [(match.group(1), number_value(match.group(2))) for match in re.finditer(
            r'^\s*(?:[-*]\s*)?Liquidity bar:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*dollar_volume=([^\s\[]+)', text, re.I | re.M)]
        required = int(rules['lookback_days'])
        if len(printed) != required:
            raise ValueError(f'Printed liquidity bars must contain exactly {required} observations')
        days = [row[0] for row in printed]
        if len(set(days)) != required or days != sorted(days):
            raise ValueError('Printed liquidity bars must use unique dates in ascending order')
        ticker = fields.get('ticker')
        selected_reader = live_reader_path if fields.get('reader') == 'live' else reader_path
        if not ticker or not selected_reader:
            raise ValueError('Median dollar-volume marker needs a ticker and reader file')
        bars = read_bars(selected_reader, ticker)
        if len(bars) < required:
            raise ValueError(f'Reader has fewer than {required} official bars')
        expected_days = [bar['date'] for bar in bars[-required:]]
        if days != expected_days:
            raise ValueError('Printed liquidity dates are not the latest reader observations')
        rows = [row[1] for row in printed]
        return [statistics.median(rows)]
    raise ValueError(f'Unknown calculation marker: {calc_id}')


def validate_marker(kind, fields, claimed, *, line, line_text, text, run, rules, reader_path, live_reader_path):
    if not claimed:
        return None
    if kind == 'rule':
        name = fields.get('id') or fields.get('name')
        if not name or name not in rules:
            return f'line {line}: unknown worksheet rule marker'
        if len(claimed) != 1:
            return f'line {line}: put one rule number on each line'
        expected = dec(rules[name], name)
        visible = visible_numbers(line_text)
        token_values = [number_value(token) for token in visible]
        # A visible percentage is stated in percentage points. Other values use their configured units.
        for token, value in zip(visible, token_values):
            actual = value / 100 if '%' in token else value
            if actual == expected:
                return None
        return f'line {line}: number does not match rule {name}'
    if kind == 'fact':
        concept = fields.get('concept'); period = fields.get('period'); tag = fields.get('tag')
        if not concept or not period or tag not in {'historical', 'pro forma', 'reported after the spin'}:
            return f'line {line}: fact marker needs concept, period, and a valid reporting tag'
        if len(claimed) != 1:
            return f'line {line}: put one fact number on each line'
        try:
            expected = facts_value(run, concept, period, fields.get('facts_file', 'facts.json'))
        except (OSError, ValueError, KeyError) as exc:
            return f'line {line}: {exc}'
        if expected not in claimed:
            return f'line {line}: number is not in facts.json for {concept} {period}'
        if not fields.get('filing') or not fields.get('section'):
            return f'line {line}: fact marker needs its filing and section'
        source_name = fields.get('source_file')
        source_line = fields.get('line')
        if source_name or source_line:
            if not source_name or not source_line:
                return f'line {line}: fact marker needs both source_file and line'
            try:
                source = source_file(run, source_name)
                supported = line_numbers(source, int(source_line))
            except (OSError, ValueError) as exc:
                return f'line {line}: {exc}'
            if expected not in supported:
                return f'line {line}: fact value is not on filing line {source_line}'
        return None
    if kind == 'filing':
        filename = fields.get('file'); source_line = fields.get('line'); section = fields.get('section')
        if not filename or not source_line or not section or fields.get('tag') not in {'historical', 'pro forma', 'reported after the spin'} or not fields.get('period'):
            return f'line {line}: filing marker needs file, line, section, tag, and period'
        try:
            source = source_file(run, filename)
            supported = line_numbers(source, int(source_line))
        except (OSError, ValueError) as exc:
            return f'line {line}: {exc}'
        return compare_tokens(claimed, supported, f'filing line {source_line}')
    if kind == 'price':
        day = fields.get('date'); ticker = fields.get('ticker') or ''
        selected_reader = live_reader_path if fields.get('reader') == 'live' else reader_path
        if fields.get('reader') not in (None, '', 'target', 'live'):
            selected_reader = Path(fields['reader'])
            if not selected_reader.is_absolute():
                selected_reader = (run / selected_reader).resolve()
        if not selected_reader or not day or not ticker:
            return f'line {line}: price marker needs date and ticker, plus a reader file'
        try:
            bars = read_bars(selected_reader, ticker)
            expected = [bar['close'] for bar in bars if bar['date'] == day]
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return f'line {line}: reader error: {exc}'
        return compare_tokens(claimed, expected, f'reader price for {ticker} on {day}')
    if kind == 'calc':
        calc_id = fields.get('id') or ''
        try:
            expected = expected_calculation(text, line_text, calc_id, rules, reader_path, live_reader_path, fields)
        except (OSError, ValueError, KeyError, InvalidOperation) as exc:
            return f'line {line}: calculation {calc_id}: {exc}'
        if len(claimed) != len(expected) or claimed != expected:
            return f'line {line}: calculation {calc_id} does not match its printed inputs'
        return None
    return f'line {line}: unrecognized numeric claim marker'


def metadata(text, worksheet_path):
    match = re.search(r'<!--\s*lab07-worksheet-source\s*(.*?)-->', text, re.S | re.I)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if '=' in line:
            key, value = line.strip().split('=', 1)
            value = value.strip()
            try:
                decoded = json.loads(value) if value.startswith('"') else value.strip('\'')
            except json.JSONDecodeError:
                decoded = value.strip('"\'')
            fields[key.strip().casefold()] = decoded
    base = Path(worksheet_path).parent
    for key in ('run', 'rules', 'reader', 'live_reader'):
        if fields.get(key):
            path = Path(fields[key])
            fields[key] = path if path.is_absolute() else (base / path).resolve()
    return fields


def validate_worksheet(worksheet_path, *, run=None, rules_path=None, reader_path=None):
    worksheet_path = Path(worksheet_path).resolve()
    text = worksheet_path.read_text(encoding='utf-8')
    meta = metadata(text, worksheet_path)
    run = Path(run or meta.get('run') or worksheet_path.parent).resolve()
    rules_path = Path(rules_path or meta.get('rules') or 'lab07_worksheet_rules.md').resolve()
    reader_path = Path(reader_path or meta.get('reader')).resolve() if (reader_path or meta.get('reader')) else None
    rules = read_rules(rules_path)
    live_reader_path = meta.get('live_reader')
    failures = []
    in_metadata = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if '<!-- lab07-worksheet-source' in line:
            in_metadata = True
            continue
        if in_metadata:
            if '-->' in line:
                in_metadata = False
            continue
        if line.strip().startswith('<!--') and '-->' in line:
            continue
        raw = visible_numbers(line)
        if not raw:
            continue
        if len(raw) != 1:
            failures.append(f'line {line_number}: split numeric claims onto separate lines')
            continue
        markers = list(MARKER.finditer(line))
        claimed = [number_value(token) for token in raw]
        if not markers:
            failures.append(f'line {line_number}: {raw[0]} has no source, rule, reader, or calculation marker')
            continue
        if len(markers) > 1:
            failures.append(f'line {line_number}: use one claim marker per numeric line')
            continue
        marker = markers[0]
        kind = marker.group(1).casefold()
        try:
            fields = parse_marker(marker.group(2))
        except ValueError as exc:
            failures.append(f'line {line_number}: {exc}')
            continue
        issue = validate_marker(kind, fields, claimed, line=line_number, line_text=line, text=text,
                                run=run, rules=rules, reader_path=reader_path,
                                live_reader_path=live_reader_path)
        if issue:
            failures.append(issue if issue.startswith('line ') else f'line {line_number}: {issue}')
    return failures


def _tool_command(event):
    value = ((event.get('tool_input') or {}).get('command') or '')
    return value if isinstance(value, str) else ''


def _automatic_worksheet(event, run):
    """Read the exact saved worksheet path from a completed runner's output."""
    response = event.get('tool_response')
    if isinstance(response, dict):
        response = response.get('output', '')
    if not isinstance(response, str):
        raise ValueError('Worksheet runner output is unavailable')
    paths = re.findall(r'^Worksheet:\s*(.+?)\s*$', response, re.M)
    if len(paths) != 1 or not run:
        raise ValueError('Worksheet runner did not identify exactly one output and run folder')
    worksheet = Path(paths[0]).resolve()
    if not worksheet.is_relative_to(Path(run).resolve()) or not worksheet.is_file():
        raise ValueError('Worksheet output is missing or outside its saved run')
    return worksheet


def hook_main():
    """Codex lifecycle hook. State contains paths only, never worksheet claims."""
    try:
        event = json.loads(sys.stdin.read() or '{}')
    except json.JSONDecodeError:
        print(json.dumps({'decision': 'block', 'reason': 'Worksheet hook received invalid JSON.'}))
        return 0
    event_name = event.get('hook_event_name')
    session = str(event.get('session_id') or '')
    turn = str(event.get('turn_id') or '')
    state_key = hashlib.sha256(session.encode('utf-8')).hexdigest()[:16] if session else 'unknown'
    state_path = Path(tempfile.gettempdir()) / f'lab07_worksheet_hook_{state_key}.json'
    if event_name == 'PostToolUse':
        command = _tool_command(event)
        automatic = 'run_worksheet.py' in command.casefold()
        if not automatic and 'save_worksheet.py' not in command.casefold():
            return 0
        args = {}
        tokens = shlex.split(command, posix=False)
        for name in ('--output', '--run', '--rules', '--reader', '--bars'):
            if name in tokens:
                i = tokens.index(name)
                if i + 1 < len(tokens):
                    args[name] = tokens[i + 1].strip('"\'')
        if not automatic and '--output' not in args:
            print(json.dumps({'decision': 'block', 'reason': 'Worksheet writer did not give the hook an output path.'}))
            return 0
        try:
            worksheet = _automatic_worksheet(event, args.get('--run')) if automatic else Path(args['--output']).resolve()
        except ValueError as exc:
            print(json.dumps({'decision': 'block', 'reason': str(exc)}))
            return 0
        state = {'session_id': session, 'turn_id': turn, 'worksheet': str(worksheet),
                 'run': args.get('--run'), 'rules': args.get('--rules'), 'reader': args.get('--reader') or args.get('--bars')}
        state_path.write_text(json.dumps(state), encoding='utf-8')
        try:
            issues = validate_worksheet(worksheet, run=state['run'], rules_path=state['rules'], reader_path=state['reader'])
        except Exception as exc:
            issues = [f'worksheet could not be checked: {type(exc).__name__}: {exc}']
        if issues:
            print(json.dumps({'decision': 'block', 'reason': 'Worksheet check failed: ' + '; '.join(issues[:8]),
                              'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': 'Fix every reported worksheet line before you finish.'}}))
        return 0
    if event_name == 'Stop':
        try:
            state = json.loads(state_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return 0
        if state.get('session_id') != session or state.get('turn_id') != turn:
            return 0
        try:
            issues = validate_worksheet(state['worksheet'], run=state.get('run'),
                                        rules_path=state.get('rules'), reader_path=state.get('reader'))
        except Exception as exc:
            issues = [f'worksheet could not be checked: {type(exc).__name__}: {exc}']
        if issues:
            print(json.dumps({'decision': 'block', 'reason': 'Worksheet check failed: ' + '; '.join(issues[:8])}))
        else:
            state_path.unlink(missing_ok=True)
        return 0
    return 0


def main():
    parser = argparse.ArgumentParser(description='Verify every numeric claim in a Lab 07 worksheet')
    parser.add_argument('--worksheet', type=Path, help='Worksheet Markdown file')
    parser.add_argument('--run', type=Path, help='Saved run folder')
    parser.add_argument('--rules', type=Path, help='lab07_worksheet_rules.md')
    parser.add_argument('--reader', type=Path, help='Reader bars JSON file')
    args = parser.parse_args()
    if not args.worksheet:
        hook_main()
        return
    issues = validate_worksheet(args.worksheet, run=args.run, rules_path=args.rules, reader_path=args.reader)
    if issues:
        for issue in issues:
            print('refused: ' + issue)
        raise SystemExit(1)
    print('Worksheet numeric claims verified.')


if __name__ == '__main__':
    main()
