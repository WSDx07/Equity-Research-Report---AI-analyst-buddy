"""Extract conservative, dated worksheet inputs from a saved team run."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import prepare_worksheet


# Only accept concepts whose meaning matches the worksheet input. In
# particular, weighted-average diluted shares are not shares outstanding.
CONCEPTS = {
    'after_tax_earnings': ('net_income', 'Consolidated Statements of Operations', 'USD'),
    'depreciation': ('depreciation_and_amortization', 'Consolidated Statements of Cash Flows', 'USD'),
    'capital_spending': ('additions_to_property_and_equipment', 'Consolidated Statements of Cash Flows', 'USD'),
    'diluted_shares': ('diluted_shares_outstanding', 'Shares outstanding', 'shares'),
}

STATEMENT_HEADINGS = {
    'after_tax_earnings': re.compile(r'^(?:(?:unaudited|consolidated|combined|pro forma)\s+)*(?:statements?\s+of\s+(?:operations|income|earnings)|(?:income|operations)\s+statements?)$', re.I),
    'depreciation': re.compile(r'^(?:(?:unaudited|consolidated|combined|pro forma)\s+)*(?:statements?\s+of\s+cash\s+flows|cash\s+flows?\s+statements?)$', re.I),
    'capital_spending': re.compile(r'^(?:(?:unaudited|consolidated|combined|pro forma)\s+)*(?:statements?\s+of\s+cash\s+flows|cash\s+flows?\s+statements?)$', re.I),
    'diluted_shares': re.compile(r'^(?:diluted\s+shares\s+outstanding|common\s+shares\s+outstanding)$', re.I),
}
ROW_LABELS = {
    'after_tax_earnings': re.compile(r'^net\s+(?:(?:income|earnings)(?:\s*\(loss\))?|loss)\s*$', re.I),
    'depreciation': re.compile(r'^depreciation(?:\s+(?:and|&)\s+amortization)?\s*$', re.I),
    'capital_spending': re.compile(r'^(?:additions\s+to\s+property\s+(?:and|&)\s+equipment|capital\s+expenditures|purchases\s+of\s+(?:property(?:,?\s+plant)?\s+and\s+equipment|fixed\s+assets)|payments\s+to\s+acquire\s+property,?\s+plant\s+and\s+equipment)\s*$', re.I),
    'diluted_shares': re.compile(r'^diluted\s+shares\s+outstanding\s*$', re.I),
}


def _source_lines(source):
    raw = source.read_text(encoding='utf-8', errors='replace').splitlines()
    return [re.sub(r'^\s*\d{6}\s*\|\s*', '', line).strip() for line in raw]


def _annual_period_end(header, year):
    match = re.search(r'\byears?\s+ended\s+([A-Za-z]+\s+\d{1,2})', header, re.I)
    if match:
        try:
            month_day = datetime.strptime(match.group(1), '%B %d')
            return date(year, month_day.month, month_day.day)
        except ValueError:
            pass
    return date(year, 12, 31)


def _first_row_amount(lines, row, scale, target):
    negative = False
    for position in range(row + 1, min(row + 16, len(lines))):
        token = lines[position].strip()
        if token in {'', '$'}:
            continue
        if token in {'(', '−', '-'}:
            negative = True
            continue
        if token in {'—', '–', 'â€”'}:
            value = Decimal(0)
            value_line = position + 1
        else:
            match = re.fullmatch(r'\(?\s*([\d,]+(?:\.\d+)?)\s*\)?', token)
            if not match:
                return None
            value = Decimal(match.group(1).replace(',', ''))
            if negative or token.startswith('(') or token.startswith('-'):
                value = -value
            value_line = position + 1
        if target == 'capital_spending':
            value = abs(value)
        return value * scale, value_line
    return None


def _decimal_text(value):
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), 'f')


def _pipe_row_amount(line, scale, target):
    """Read the first numeric column from a pipe-delimited saved statement."""
    for token in (part.strip() for part in line.split('|')[1:]):
        if token in {'', '$'}:
            continue
        match = re.fullmatch(r'\(?\s*([\d,]+(?:\.\d+)?)\s*\)?', token)
        if not match:
            continue
        value = Decimal(match.group(1).replace(',', ''))
        if token.startswith('(') or token.startswith('-'):
            value = -value
        if target == 'capital_spending':
            value = abs(value)
        return value * scale
    return None


def _text_annual_input(run, target, distribution_date, as_of):
    """Read one unambiguous annual statement row when the run has no XBRL fact."""
    candidates = []
    pattern = STATEMENT_HEADINGS[target]
    allowed_rows = ROW_LABELS[target]
    for source in Path(run).rglob('*.txt'):
        lower_name = source.name.lower()
        if lower_name.startswith(('parent_', 'live_', 'distribution_', 'form4_')):
            continue
        if target == 'diluted_shares':
            continue
        lines = _source_lines(source)
        for start, heading in enumerate(lines):
            if not pattern.fullmatch(heading):
                continue
            header = lines[start + 1:start + 50]
            header_text = ' '.join(header)
            if not re.search(r'\byears?\s+ended\b', header_text, re.I):
                continue
            years = [int(match.group()) for line in header
                     for match in re.finditer(r'\b20\d{2}\b', line)]
            if not years:
                continue
            year = years[0]
            end = _annual_period_end(header_text, year)
            if end > date.fromisoformat(as_of):
                continue
            unit = next((re.search(r'\b(?:in|amounts in)\s+(dollars|shares|thousands|millions|billions)\b', line, re.I)
                         for line in header
                         if re.search(r'\b(?:in|amounts in)\s+(dollars|shares|thousands|millions|billions)\b', line, re.I)), None)
            if not unit:
                continue
            scale = {'dollars': 1, 'shares': 1, 'thousands': 1000,
                     'millions': 1000000, 'billions': 1000000000}[unit.group(1).lower()]
            stop = next(
                (pos for pos in range(start + 1, min(start + 800, len(lines)))
                 if any(item.fullmatch(lines[pos]) for item in STATEMENT_HEADINGS.values())
                 or re.match(r'^see\s+(?:the\s+)?(?:accompanying\s+)?notes\b', lines[pos], re.I)),
                min(start + 800, len(lines)))
            for row in range(start + 1, stop):
                row_label = lines[row].split('|', 1)[0].strip()
                if not allowed_rows.fullmatch(row_label):
                    continue
                amount = _pipe_row_amount(lines[row], scale, target) if '|' in lines[row] else None
                parsed = (amount, row + 1) if amount is not None else _first_row_amount(lines, row, scale, target)
                if not parsed:
                    continue
                amount, value_line = parsed
                tag = ('pro forma' if 'pro forma' in heading.lower() or 'pro forma' in header_text.lower()
                       else 'reported after the spin' if distribution_date and end.isoformat() >= distribution_date
                       else 'historical')
                accession = re.search(r'(\d{10}-\d{2}-\d{6}|\d{18})', source.name)
                candidates.append((end, {
                    'value': _decimal_text(amount), 'unit': 'shares' if target == 'diluted_shares' else 'USD',
                    'tag': tag, 'period': f'FY{year} ended {end.isoformat()}',
                    'filing': re.sub(r'\D', '', accession.group(1)) if accession else source.name,
                    'section': heading, 'source_file': str(source.relative_to(Path(run))),
                    'line': value_line,
                }))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], 'combined' in item[1]['section'].lower()), reverse=True)
    return candidates[0][1]


def _cover_share_count(run, distribution_date, as_of):
    """Read the explicitly labeled common-share count from a saved cover page."""
    candidates = []
    for source in Path(run).rglob('*.txt'):
        lower_name = source.name.lower()
        if lower_name.startswith(('parent_', 'live_', 'distribution_', 'form4_')):
            continue
        lines = _source_lines(source)
        for row, line in enumerate(lines):
            if not re.fullmatch(r'common stock, shares outstanding', line, re.I):
                continue
            parsed = _first_row_amount(lines, row, Decimal(1), 'diluted_shares')
            if not parsed:
                continue
            value, value_line = parsed
            accession = re.search(r'(\d{10}-\d{2}-\d{6}|\d{18})', source.name)
            filed = None
            try:
                source_manifest = json.loads((source.parent / 'sources.json').read_text(encoding='utf-8'))
                relative = str(source.relative_to(Path(run)))
                source_documents = []
                for key in ('saved_source_documents', 'first_company_filings_after_spin',
                            'parent_filings_after_spin', 'distribution_filing_documents'):
                    source_documents.extend(source_manifest.get(key, []))
                filed = next((doc.get('filing_date') for doc in source_documents
                              if doc.get('path') == relative), None)
            except (OSError, ValueError, TypeError):
                pass
            tag = 'reported after the spin' if distribution_date and filed and filed >= distribution_date else 'historical'
            candidates.append((filed or '', {
                'value': _decimal_text(value), 'unit': 'shares', 'tag': tag,
                'period': f'cover-page share count reported {filed or as_of}',
                'filing': re.sub(r'\D', '', accession.group(1)) if accession else source.name,
                'section': 'Cover page: Common Stock, Shares Outstanding',
                'source_file': str(source.relative_to(Path(run))), 'line': value_line,
            }))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def statement_row(source, target, expected_value, period_end):
    """Match the first-year statement row and its scale to the XBRL value."""
    raw_lines = source.read_text(encoding='utf-8', errors='replace').splitlines()
    lines = [re.sub(r'^\s*\d{6}\s*\|\s*', '', line).strip() for line in raw_lines]
    for start, heading in enumerate(lines):
        if not STATEMENT_HEADINGS[target].fullmatch(heading):
            continue
        header = lines[start + 1:start + 40]
        unit = next((re.search(r'\b(?:in|amounts in)\s+(dollars|shares|thousands|millions|billions)\b', line, re.I)
                     for line in header if re.search(r'\b(?:in|amounts in)\s+(dollars|shares|thousands|millions|billions)\b', line, re.I)), None)
        years = [int(m.group()) for line in header for m in [re.fullmatch(r'20\d\d', line)] if m]
        if not unit or not years or years[0] != date.fromisoformat(period_end).year:
            continue
        scale = {'dollars': 1, 'shares': 1, 'thousands': 1000,
                 'millions': 1000000, 'billions': 1000000000}[unit.group(1).lower()]
        for pos in range(start + 1, min(start + 650, len(lines))):
            if not ROW_LABELS[target].fullmatch(lines[pos]):
                if (re.fullmatch(r'refer to accompanying notes\.?', lines[pos], re.I)
                        or any(pattern.fullmatch(lines[pos]) for pattern in STATEMENT_HEADINGS.values())):
                    break
                continue
            negative = False
            for value_pos in range(pos + 1, min(pos + 12, len(lines))):
                token = lines[value_pos]
                if token == '(':
                    negative = True
                    continue
                if token in {'', '$', ')'}:
                    continue
                match = re.fullmatch(r'\(?\s*([\d,]+(?:\.\d+)?)\s*\)?', token)
                if not match:
                    break
                amount = Decimal(match.group(1).replace(',', '')) * scale
                if negative or token.startswith('('):
                    amount = -amount
                # Cash outflows are commonly printed in parentheses, while the
                # XBRL PaymentsToAcquire concept reports a positive amount.
                expected = abs(Decimal(str(expected_value))) if target == 'capital_spending' else Decimal(str(expected_value))
                if (abs(amount) if target == 'capital_spending' else amount) == expected:
                    return heading, value_pos + 1
                break
    return None


def depreciation_from_saved_statement(run, facts, earnings):
    """Read an unambiguous annual D&A row from the same saved annual filing."""
    if not earnings or not facts.get('fiscal_year_end'):
        return None
    try:
        current = facts['concepts']['net_income']['current']
        fiscal_end = date.fromisoformat(facts.get('fiscal_year_end') or current['end'])
        if current['end'] != fiscal_end.isoformat():
            return None
        source = Path(run) / earnings['source_file']
        lines = source.read_text(encoding='utf-8', errors='replace').splitlines()
    except (OSError, KeyError, ValueError, TypeError):
        return None
    heading = re.compile(r'^(?:(?:unaudited|consolidated|combined|pro forma)\s+)*(?:statements?\s+of\s+cash\s+flows|cash\s+flows?\s+statements?)$', re.I)
    label = re.compile(r'^depreciation\s+(?:and|&)\s+amortization\s*$', re.I)
    normalized = [re.sub(r'^\s*\d{6}\s*\|\s*', '', raw).strip() for raw in lines]
    for start, raw in enumerate(normalized):
        if not heading.fullmatch(raw):
            continue
        header = normalized[start + 1:start + 35]
        scale_match = next((re.search(r'\b(?:in|amounts in)\s+(thousands|millions|billions)\b', line, re.I) for line in header
                            if re.search(r'\b(?:in|amounts in)\s+(thousands|millions|billions)\b', line, re.I)), None)
        years = [int(match.group()) for line in header for match in [re.fullmatch(r'\s*(20\d\d)\s*', line)] if match]
        if not scale_match or not years or years[0] != fiscal_end.year:
            continue
        scale = {'thousands': 1000, 'millions': 1000000, 'billions': 1000000000}[scale_match.group(1).lower()]
        stop = next((pos for pos in range(start + 1, min(start + 500, len(normalized)))
                     if any(pattern.fullmatch(normalized[pos]) for pattern in STATEMENT_HEADINGS.values()
                            if pattern is not heading)
                     or re.match(r'^see\s+(?:the\s+)?(?:accompanying\s+)?notes\b', normalized[pos], re.I)),
                    min(start + 500, len(normalized)))
        for pos in range(start + 1, stop):
            if not label.fullmatch(normalized[pos]):
                continue
            values = []
            first_value_line = None
            for value_pos, value_line in enumerate(normalized[pos + 1:pos + 12], pos + 2):
                token = value_line.strip()
                if token in {'$', ''}:
                    continue
                match = re.fullmatch(r'([\d,]+(?:\.\d+)?)', token)
                if not match:
                    break
                if first_value_line is None:
                    first_value_line = value_pos
                values.append(Decimal(match.group(1).replace(',', '')))
                if len(values) == 2:
                    break
            if len(values) < 2:
                return None
            return {'value': str(values[0] * scale), 'unit': 'USD', 'tag': earnings['tag'],
                    'period': earnings['period'], 'filing': earnings['filing'],
                    'section': raw.strip(), 'source_file': earnings['source_file'], 'line': first_value_line}
    return None


def dated_registry(entity, as_of):
    """Do not use facts filed after the run's analysis date."""
    return prepare_worksheet.registry_as_of(entity, as_of)


def read_financial_inputs(run, facts, distribution_date=None):
    """Accept only annual XBRL facts traceable to a saved filing in this run."""
    run = Path(run)
    as_of = date.fromisoformat(facts['as_of'])
    found = {}
    for target, (concept, section, unit) in CONCEPTS.items():
        item = (facts.get('concepts') or {}).get(concept) or {}
        current = item.get('current') or {}
        accession = str(current.get('accn') or '')
        compact = re.sub(r'\D', '', accession)
        sources = [p for p in run.rglob('*.txt') if compact and compact in re.sub(r'\D', '', p.name)]
        if not sources or current.get('val') is None or item.get('unit') != unit:
            continue
        try:
            filed = date.fromisoformat(current['filed'])
            end = date.fromisoformat(current['end'])
            if filed > as_of or end > as_of or current.get('form') not in {'10-K', '10-12B', '10-12B/A', '10-12G', '10-12G/A'}:
                continue
            if target != 'diluted_shares':
                start = date.fromisoformat(current['start'])
                if not 350 <= (end - start).days <= 380:
                    continue
                period = f'{start.isoformat()} to {end.isoformat()}'
            else:
                period = f'as of {end.isoformat()}'
        except (KeyError, ValueError, TypeError):
            continue
        statement = None
        source_line = None
        source_path = None
        for source in sources:
            match = statement_row(source, target, current['val'], current['end'])
            if match:
                statement, source_line = match
                source_path = source
                break
        if not statement:
            continue
        period_start = start.isoformat() if target != 'diluted_shares' else end.isoformat()
        tag = ('pro forma' if 'pro forma' in statement.lower() else
               'reported after the spin' if distribution_date and period_start >= distribution_date else 'historical')
        found[target] = {'value': str(current['val']), 'unit': unit, 'tag': tag, 'period': period,
                         'filing': accession, 'section': statement,
                         'source_file': str(source_path.relative_to(run)), 'line': source_line,
                         'xbrl_concept': item.get('tag')}
    if 'depreciation' not in found:
        item = depreciation_from_saved_statement(run, facts, found.get('after_tax_earnings'))
        if item:
            found['depreciation'] = item
    # Some Form 10 registrations, especially new registrants, have no
    # companyfacts history yet. Read a matching annual table from the saved
    # filing itself, with the table heading, scale, year, accession, and line.
    for target in ('after_tax_earnings', 'depreciation', 'capital_spending'):
        if target not in found:
            item = _text_annual_input(run, target, distribution_date, as_of.isoformat())
            if item:
                found[target] = item
    if 'diluted_shares' not in found:
        item = _cover_share_count(run, distribution_date, as_of.isoformat())
        if item:
            found['common_shares'] = item
    # Mixing different annual periods would produce an invented cash flow.
    periods = {found[k]['period'] for k in ('after_tax_earnings', 'depreciation', 'capital_spending') if k in found}
    if len(periods) > 1:
        for key in ('after_tax_earnings', 'depreciation', 'capital_spending'):
            found.pop(key, None)
    return found


def load_bars(path, ticker, cik, as_of):
    """Read the verified reader output, rejecting a different instrument."""
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or str(data.get('ticker', '')).upper() != ticker.upper():
        raise ValueError('Reader ticker does not match the saved run')
    if str(data.get('cik', '')).zfill(10) != str(cik).zfill(10):
        raise ValueError('Reader CIK does not match the saved run')
    if data.get('basis') not in ('official_unadjusted', 'user_asserted_official_unadjusted') or data.get('session') != 'regular' or data.get('when_issued') is not False:
        raise ValueError('Reader data is not verified regular-way official closes')
    bars = data.get('bars')
    if not isinstance(bars, list):
        raise ValueError('Reader output has no bars list')
    if any(str(row.get('ticker', '')).upper() != ticker.upper() for row in bars):
        raise ValueError('A reader bar has a different ticker')
    import worksheet_math
    return worksheet_math._validated_bars(bars, as_of)


def registry_record(entity, key):
    values = prepare_worksheet.registry_value(entity, key)
    if values is None:
        return None
    records = entity.get(key, [])
    records = [records] if isinstance(records, dict) else records
    return next((r for r in records if str(r.get('value')) == values and r.get('filing') and r.get('section')), None)


ABSENCE_PATTERNS = {
    'debt covenants': re.compile(r'\b(?:we|the company|the registrant)\s+(?:have|has|had)\s+no\s+material\s+debt\s+covenants\b', re.I),
    'parent liabilities': re.compile(r'\b(?:the\s+)?parent\s+transferred\s+no\s+liabilities\b', re.I),
    'parent restrictions': re.compile(r'\b(?:the\s+)?separation agreement\s+imposes\s+no\s+restrictions\b', re.I),
}


def find_explicit_absences(run, facts, as_of, distribution_date=None):
    """Accept only explicit, sourced absence statements in the saved annual filing."""
    current = ((facts.get('concepts') or {}).get('net_income') or {}).get('current') or {}
    accession = str(current.get('accn') or '')
    compact = re.sub(r'\D', '', accession)
    filed = str(current.get('filed') or '')
    if current.get('form') != '10-K' or not compact or not filed or filed > as_of:
        return {}
    heading = re.compile(r'^(?:notes?\s+to\s+financial\s+statements|debt|indebtedness|covenants|financing|separation|restrictions|liabilities)(?:\s+[\w,&()\-/]+){0,9}\s*$', re.I)
    found = {}
    for source in Path(run).rglob('*.txt'):
        if compact not in re.sub(r'\D', '', source.name):
            continue
        section = None
        for line_no, raw in enumerate(source.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            line = re.sub(r'^\s*\d{6}\s*\|\s*', '', raw).strip()
            if heading.fullmatch(line) and len(line) < 100:
                section = line
                continue
            if not section:
                continue
            for name, pattern in ABSENCE_PATTERNS.items():
                if pattern.fullmatch(line.rstrip('.').strip()):
                    found[name] = {'value': 'none', 'unit': '(reported absence)',
                                   'tag': 'reported after the spin' if distribution_date and filed >= distribution_date else 'historical',
                                   'period': f'filing date {filed}', 'filing': accession,
                                   'section': section, 'source_file': str(source.relative_to(run)), 'line': line_no}
    return found


def extract_financing_facts(run, manifest, entity, as_of):
    """Read a small set of explicit transactions from the registry's Form 10.

    Reject ambiguous references and documents without a recognizable section.
    Unmatched text is reported as not established, never as zero.
    """
    accession = str(manifest.get('registration_accession') or '')
    if not accession:
        return {}
    registry_dates = [str(record.get('filing_date'))
                      for records in entity.values() if isinstance(records, list)
                      for record in records if isinstance(record, dict)
                      and accession in re.sub(r'\D', '', str(record.get('filing', '')))
                      and record.get('filing_date')]
    if not registry_dates:
        return {}
    filed = max(registry_dates)
    if filed > as_of:
        return {}
    distribution = prepare_worksheet.registry_value(entity, 'distribution_date')
    amount = r'\$\s*(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion)?'
    patterns = {
        'debt_raised': re.compile(r'\b(?:we|the company|the registrant)\s+(?:have\s+)?(?:borrowed|incurred|issued)\s+' + amount + r'\s+(?:of\s+|in\s+)?(?:debt|notes|loans)\b', re.I),
        'cash_use': re.compile(r'\b(?:we|the company|the registrant)\s+used\s+' + amount + r'\s+of\s+(?:the\s+)?proceeds\s+to\s+([^.;\n]{3,160})', re.I),
        'parent_liabilities': re.compile(r'\b(?:the\s+)?parent\s+transferred\s+' + amount + r'\s+of\s+([^.;\n]{3,120}liabilities)\b', re.I),
    }
    restriction = re.compile(r'\b(?:the separation agreement|the parent)\s+(?:prohibits|restricts)\s+(?:us|the company|the registrant)\s+(?:from\s+)?([^.;\n]{3,160})', re.I)
    heading = re.compile(r'^(?:(?:unaudited\s+)?pro forma consolidated financial statements|(?:the\s+)?(?:separation|distribution|financing|indebtedness|debt|use of proceeds|liabilities|financial statements|pro forma|tax matters|restrictions)(?:\s+[\w,&()\-/]+){0,9})\s*$', re.I)
    found = {}
    for document in manifest.get('saved_source_documents', []):
        if str(document.get('accession')) != accession or not document.get('path') or not document.get('url'):
            continue
        path = (Path(run) / document['path']).resolve()
        if not path.is_relative_to(Path(run).resolve()) or not path.is_file():
            continue
        section = None
        for line_no, raw in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            line = re.sub(r'^\s*\d{6}\s*\|\s*', '', raw).strip()
            if ('tax matters agreement' in line.casefold() and
                    re.search(r'will be obligated to indemnify .+? against such taxes .+? in certain circumstances', line, re.I)):
                found.setdefault('parent_liabilities', []).append({
                    'value': 'conditional tax indemnity; amount not stated', 'unit': '(contingent obligation)',
                    'tag': 'pro forma', 'period': f'filing date {filed}; agreement expected',
                    'filing': document['url'], 'section': 'Risk Factors — tax-free treatment of the spin-off',
                    'source_file': document['path'], 'line': line_no})
            if ('tax matters agreement' in line.casefold() and
                    re.search(r'for the two-year period following the distribution date, we are prohibited, except in certain circumstances', line, re.I)):
                found.setdefault('restrictions', []).append({
                    'value': 'conditional restrictions on certain transactions for two years following distribution',
                    'unit': '(restriction)', 'tag': 'pro forma', 'period': f'filing date {filed}; agreement expected',
                    'filing': document['url'], 'section': 'Risk Factors — tax-free treatment of the spin-off',
                    'source_file': document['path'], 'line': line_no})
            if heading.fullmatch(line) and len(line) < 100:
                section = line
                continue
            if not section or len(line) > 2000:
                continue
            if re.search(r'pro forma consolidated financial statements', section, re.I):
                proforma_patterns = {
                    'debt_raised': re.compile(r'principal indebtedness of an assumed amount equal to\s*' + amount, re.I),
                    'cash_use': re.compile(r'expected distribution of an aggregate amount equal to\s*' + amount + r'\s+of cash to\s+([^,;.]+)', re.I),
                }
                for key, pattern in proforma_patterns.items():
                    match = pattern.search(line)
                    if not match:
                        continue
                    multiplier = {'thousand': 1000, 'million': 1000000, 'billion': 1000000000}.get((match.group(2) or '').lower(), 1)
                    item = {'value': str(Decimal(match.group(1).replace(',', '')) * multiplier), 'unit': 'USD',
                            'tag': 'pro forma', 'period': f'filing date {filed}; assumed transaction',
                            'filing': document['url'], 'section': section, 'source_file': document['path'], 'line': line_no,
                            'description': 'assumed principal debt, net of applicable issuance costs' if key == 'debt_raised' else 'expected cash distribution to ' + match.group(3).strip()}
                    found.setdefault(key, []).append(item)
            for key, pattern in patterns.items():
                match = pattern.search(line)
                if not match or len(re.findall(r'\$', line)) != 1:
                    continue
                value = Decimal(match.group(1).replace(',', ''))
                multiplier = {'thousand': 1000, 'million': 1000000, 'billion': 1000000000}.get((match.group(2) or '').lower(), 1)
                tag = 'pro forma' if 'pro forma' in section.lower() else ('reported after the spin' if distribution and filed >= distribution else 'historical')
                item = {'value': str(value * multiplier), 'unit': 'USD', 'tag': tag,
                        'period': f'filing date {filed}', 'filing': document['url'],
                        'section': section, 'source_file': document['path'], 'line': line_no}
                if key != 'debt_raised':
                    item['description'] = match.group(3).strip()
                found.setdefault(key, []).append(item)
            match = restriction.search(line)
            if match and not re.search(r'\d|\$', match.group(1)):
                tag = 'reported after the spin' if distribution and filed >= distribution else 'historical'
                found.setdefault('restrictions', []).append({
                    'value': match.group(1).strip(), 'unit': '(restriction)', 'tag': tag,
                    'period': f'filing date {filed}', 'filing': document['url'],
                    'section': section, 'source_file': document['path'], 'line': line_no})
    # Conflicting extracted claims are preserved as unknown rather than guessed.
    return {key: values[0] for key, values in found.items()
            if len({(value['value'], value.get('description')) for value in values}) == 1}


def extract_parent_after_spin(run, manifest, distribution_date, as_of):
    """Find an explicit parent operations statement in a post-spin filing."""
    if not distribution_date:
        return None
    heading = re.compile(r'^(?:business|overview|our business|operations|results of operations)\s*$', re.I)
    statement = re.compile(r'\b(?:following|after)\s+the\s+(?:spin-off|distribution|separation),?\s+(?:we|the company)\s+(?:continue to operate|operated|operate)\s+([^.;\n]{3,160})', re.I)
    for doc in manifest.get('parent_filings_after_spin', []):
        filed = doc.get('filing_date')
        if not filed or not distribution_date < filed <= as_of or not doc.get('path') or not doc.get('url'):
            continue
        path = (Path(run) / doc['path']).resolve()
        if not path.is_relative_to(Path(run).resolve()) or not path.is_file():
            continue
        section = None
        for line_no, raw in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            line = re.sub(r'^\s*\d{6}\s*\|\s*', '', raw).strip()
            if heading.fullmatch(line):
                section = line
            match = statement.search(line) if section else None
            if match and not re.search(r'\d|\$', match.group(1)):
                return {'value': match.group(1).strip(), 'unit': '(operations)',
                        'tag': 'reported after the spin', 'period': f'filing date {filed}',
                        'filing': doc['url'], 'section': section, 'source_file': doc['path'], 'line': line_no}
    return None


def extract_release_facts(run, release):
    """Extract only an explicit revenue amount from the selected release."""
    accession = str(release.get('accession') or '')
    filed = release.get('filing_date')
    if not accession or not filed:
        return {}
    revenue = re.compile(r'^(?:quarterly\s+)?revenue\s+(?:was|were|of|:)\s*\$\s*(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion)\b', re.I)
    found = []
    for doc in release.get('documents', []):
        if str(doc.get('accession')) != accession or not doc.get('path') or not doc.get('url'):
            continue
        path = (Path(run) / doc['path']).resolve()
        if not path.is_relative_to(Path(run).resolve()) or not path.is_file():
            continue
        for line_no, raw in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            line = re.sub(r'^\s*\d{6}\s*\|\s*', '', raw).strip()
            match = revenue.search(line)
            if not match:
                continue
            scale = {'thousand': 1000, 'million': 1000000, 'billion': 1000000000}[match.group(2).lower()]
            found.append({'value': str(Decimal(match.group(1).replace(',', '')) * scale),
                          'unit': 'USD', 'tag': 'historical', 'period': f'release filed {filed}; reporting period not established',
                          'filing': doc['url'], 'section': 'Earnings release: revenue',
                          'source_file': doc['path'], 'line': line_no})
    return {'revenue': found[0]} if len({item['value'] for item in found}) == 1 else {}
