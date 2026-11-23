"""Render sourced worksheet claims in the numeric guard's marked format."""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import worksheet_guard
import prepare_worksheet


# A statement prints its scale as "(in thousands)", "amounts in millions", or a bare "(thousands)".
STATEMENT_UNIT = re.compile(r'(?:\b(?:in|amounts? in)\s+|\(\s*)(thousands|millions|billions)\b', re.I)


def _q(value):
    return json.dumps(str(value), ensure_ascii=False)


def _source_amount(item, run, *, allow_magnitude=False):
    """Find the printed source-unit amount; never invent a scale or source."""
    source = worksheet_guard.source_file(run, item['source_file'])
    index = int(item['line'])
    raw = source.read_text(encoding='utf-8', errors='replace').splitlines()
    nums = worksheet_guard.line_numbers(source, index)
    wanted = Decimal(str(item['value']))
    line = raw[index - 1]
    nearby = '\n'.join(raw[max(0, index - 350):index])
    candidates = []
    for n in nums:
        for factor, unit in ((Decimal(1), ''), (Decimal(1000), 'thousands'),
                             (Decimal(1000000), 'millions'), (Decimal(1000000000), 'billions')):
            if abs(n * factor) != abs(wanted):
                continue
            if factor != 1:
                statement_unit = STATEMENT_UNIT.findall(nearby)
                inline_unit = bool(re.search(re.escape(str(abs(n))) + r'\s+' + unit.rstrip('s') + r's?\b', line, re.I))
                if not inline_unit and (not statement_unit or statement_unit[-1].casefold() != unit):
                    continue
            if wanted < 0 and n >= 0:
                continue
            if wanted > 0 and n < 0 and not allow_magnitude:
                continue
            candidates.append((n, factor, unit))
    if wanted == 0 and len(candidates) > 1:
        units = STATEMENT_UNIT.findall(nearby)
        preferred = units[-1].casefold() if units else ''
        candidates = [candidate for candidate in candidates if candidate[2] == preferred]
    if len(candidates) != 1:
        raise ValueError(f"Cannot establish source amount and scale for {item['section']} line {index}")
    return candidates[0]


def _filing(label, item, run, source_run='target'):
    if not item:
        return f'- {label}: not known (not established by the automatic reader).'
    for field in ('value', 'unit', 'tag', 'period', 'filing', 'section', 'source_file', 'line'):
        if item.get(field) in (None, ''):
            raise ValueError(f'{label} is missing source field {field}')
    raw, _, scale = _source_amount(item, run, allow_magnitude=label.casefold().endswith('capital spending'))
    wanted = Decimal(str(item['value']))
    sign = ' sign=magnitude' if raw < 0 and wanted >= 0 else ''
    shown = abs(raw) if sign else raw
    unit = str(item['unit']) + (' ' + scale if scale else '')
    marker = (f'[filing file={_q(item["source_file"])} line={int(item["line"])} '
              f'section={_q(item["section"])} tag={_q(item["tag"])} period={_q(item["period"])} '
              f'source_run={source_run}{sign}]')
    # The source details remain inside the marker, so numeric identifiers are not claims.
    detail = item.get('description') or ''
    if re.search(r'\d', detail):
        raise ValueError(f'{label} has a numeric description that needs a separately sourced claim')
    description = f' | {detail}' if detail else ''
    return f'- {label}: {shown} {unit}{description} | {item["tag"]} | {item["period"]} {marker}'


def _price(label, calculated, ticker, reader):
    value = calculated['market_price']
    if value['value_usd'] is None:
        return f'- {label}: not computed (reader price not available).'
    return (f'- {label}: {value["value_usd"]} USD per share on {value["date"]} '
            f'[price ticker={ticker} date={value["date"]} reader={reader}]')


def _input_section(prefix, bundle, calculated, source_run):
    inputs = bundle['inputs']['inputs']
    rows = []
    for key, label in (('after_tax_earnings', 'After-tax earnings'),
                       ('depreciation', 'Depreciation'), ('capital_spending', 'Capital spending'),
                       ('diluted_shares', 'Diluted shares')):
        rows.append(_filing(prefix + label, inputs.get(key), bundle['run'], source_run))
    if not prefix and inputs.get('common_shares'):
        rows.append(_filing('Common shares outstanding', inputs['common_shares'], bundle['run'], source_run))
    value = calculated['owner_cash_flow']['value_usd']
    if value is None:
        rows.append(f'- {prefix}Owner cash flow: not computed.')
    else:
        ident = 'live_owner_cash_flow' if prefix else 'owner_cash_flow'
        rows.append(f'- {prefix}Owner cash flow: {value} USD [calc id={ident}]')
    return rows


def _cases(prefix, calculated):
    rows = []
    for case in ('low', 'mid'):
        values = calculated['value_range'].get(case, {})
        case_title = case.title()
        equity = values.get('equity_value_usd')
        per_share = values.get('value_per_share_usd')
        name_prefix = 'live_' if prefix else ''
        rows.append(f'- {prefix}{case_title} case equity value: ' +
                    (f'{equity} USD [calc id={name_prefix}{case}_equity_value]' if equity is not None else 'not computed.'))
        rows.append(f'- {prefix}{case_title} case value per share: ' +
                    (f'{per_share} USD per share [calc id={name_prefix}{case}_value_per_share]' if per_share is not None else 'not computed.'))
    return rows


def _purchase_lines(purchases, manifest, run, spin_date):
    result = []
    documents = [doc for doc in manifest.get('saved_source_documents', []) if doc.get('form') == 'Form4' and doc.get('path')]
    for purchase in purchases:
        matches = []
        for doc in documents:
            if str(doc.get('accession')) != str(purchase.get('accession')):
                continue
            path = worksheet_guard.source_file(run, doc['path'])
            raw = path.read_text(encoding='utf-8', errors='replace').splitlines()
            xml = '\n'.join(re.sub(r'^\s*\d{6}\s*\|\s?', '', line) for line in raw)
            rows = prepare_worksheet.parse_form4_purchases(xml, purchase['accession'], purchase.get('filing_date'))
            if any(all(str(row.get(k) or '') == str(purchase.get(k) or '') for k in
                       ('transaction_code', 'transaction_date', 'shares', 'price_per_share')) for row in rows):
                matches.append(doc)
        if len(matches) != 1:
            raise ValueError('A code-P purchase lacks a unique saved Form 4 source')
        doc = matches[0]
        reporting = ('reported after the spin' if spin_date and str(purchase.get('filing_date') or '') >= spin_date
                     else 'historical')
        for field, label, unit in (('shares', 'Insider shares purchased', 'shares'),
                                   ('price_per_share', 'Insider purchase price', 'USD per share')):
            if purchase.get(field) in (None, ''):
                result.append(f'- {label}: not known.')
                continue
            marker = (f'[form4 file={_q(doc["path"])} accession={_q(purchase["accession"])} '
                      f'date={_q(purchase["transaction_date"])} field={field}]')
            result.append(f'- {label}: {purchase[field]} {unit} | {reporting} | transaction date {purchase["transaction_date"]} {marker}')
    return result


def render(bundle, calculations, manifest, purchases, judgment, live, live_calc, rules,
           registry_lines, *, rules_path, reader_path, live_reader_path):
    run = Path(bundle['run']).resolve()
    release = manifest.get('live_release') or {}
    lines = [f"Filings read: Form 10 accession {manifest.get('registration_accession') or 'not read'}; live release accession {release.get('accession') or 'not read'}",
             '', f"# Worksheet: {bundle['ticker']} | analysis date {bundle['as_of']}", '',
             '## Spinoff facts', *registry_lines,
             _price('Dated market price', calculations, bundle['ticker'], 'target'),
             '- Reader interpretation: see reader metadata; user-asserted fields do not have an independent exchange comparison.',
             '', '## Judgment', judgment['story'],
             'Evidence in the next filing that would change the view: ' + judgment['change'],
             '', '## Owner cash flow and value range',
             'Owner cash flow is after-tax earnings plus depreciation minus capital spending. Source amounts use the filing units and the calculation converts them to whole USD.',
             *_input_section('', bundle, calculations, 'target')]
    for case in ('low', 'mid'):
        for typ in ('discount_rate', 'growth_rate'):
            lines.append(f'- {case.title()} case {typ.replace("_", " ")}: {rules[case + "_" + typ]} [rule id={case}_{typ}]')
    lines.extend(_cases('', calculations))
    lines.append('- Price against low case: ' + ('computed in the margin of safety below.' if calculations['low_case_comparison']['margin_of_safety_percent'] is not None else 'not computed.'))
    if calculations['low_case_comparison']['margin_of_safety_percent'] is not None:
        lines.append(f"- Margin of safety: {calculations['low_case_comparison']['margin_of_safety_percent']}% [calc id=margin_of_safety]")
    lines += ['', '## Debt and parent']
    financing = bundle.get('financing', {})
    for key, label in (('debt_raised', 'Debt raised'), ('cash_use', 'Cash use'),
                       ('parent_liabilities', 'Parent liabilities'), ('restrictions', 'Parent restrictions')):
        item = financing.get(key)
        try:
            numeric = item is not None and Decimal(str(item.get('value'))).is_finite()
        except (InvalidOperation, ValueError, TypeError):
            numeric = False
        if item and numeric and item.get('unit') and item.get('line'):
            lines.append(_filing(label, item, run))
        elif item:
            description = str(item.get('description') or item.get('value') or 'not known')
            if re.search(r'\d', description):
                raise ValueError(f'{label} contains numeric details that require separate source markers')
            lines.append(f'- {label}: {description} | {item.get("tag", "source classification not known")} | {item.get("filing", "source not known")} | {item.get("section", "section not known")}')
        else:
            lines.append(f'- {label}: ' + ('not known.' if bundle['present'] or key in ('debt_raised', 'cash_use') else 'not applicable.'))
    covenant = bundle.get('explicit_absences', {}).get('debt covenants')
    if covenant:
        text = str(covenant.get('description') or covenant.get('value') or '')
        if re.search(r'\d', text):
            raise ValueError('Debt covenant details need separate numeric source markers')
        lines.append(f'- Debt covenants: {text} | {covenant.get("filing", "source not known")} | {covenant.get("section", "section not known")}')
    else:
        lines.append('- Debt covenants: not known (automatic reader coverage is limited).')
    parent = bundle.get('parent_after_spin')
    if parent:
        description = str(parent.get('description') or parent.get('value') or '')
        if re.search(r'\d', description):
            raise ValueError('Parent after the spin contains numeric details that require separate source markers')
        lines.append(f'- Parent after the spin: {description} | {parent.get("filing", "source not known")} | {parent.get("section", "section not known")}')
    else:
        lines.append('- Parent after the spin: not known (automatic reader coverage is limited).' if bundle['present'] else '- Parent after the spin: not applicable.')
    lines += ['', '## Insider purchases']
    if purchases:
        spin = prepare_worksheet.registry_value(bundle['registry'], 'distribution_date') if bundle['present'] else None
        lines.extend(_purchase_lines(purchases, manifest, run, spin))
    else:
        lines.append('- Insider purchases: not known (no code P purchase established in the saved filing coverage).')
    coverage = manifest.get('form4_coverage') or {}
    lines.append(f"- Filing-list coverage: {coverage.get('first_filing_date') or 'not known'} to {coverage.get('last_filing_date') or 'not known'}.")
    liq = calculations['liquidity']
    lines += ['', '## Liquidity', f"- Client purchase: {rules['purchase_size_usd']} USD [rule id=purchase_size_usd]"]
    for bar in liq['observations_used']:
        lines.append(f"- Liquidity bar: {bar['date']} | dollar_volume={bar['dollar_volume_usd']} [calc id=daily_dollar_volume ticker={bundle['ticker']} reader=target]")
    if liq['median_daily_dollar_volume_usd'] is not None:
        lines.append(f"- Median daily dollar volume: {liq['median_daily_dollar_volume_usd']} USD [calc id=median_dollar_volume ticker={bundle['ticker']} reader=target as_of={bundle['as_of']}]")
        lines.append('- Liquidity support: ' + ('supported.' if liq['supported'] else 'not supported.'))
    else:
        lines.append('- Median daily dollar volume: not known (insufficient reader data).')
    lines += ['', '## Live release view', f"- Company: {live['ticker']} | release accession {release.get('accession') or 'not known'} | acceptance {((release.get('filing_time') or {}).get('value') or 'not known')}.",
              _filing('Release revenue', live.get('release_facts', {}).get('revenue'), run),
              _price('Live dated market price', live_calc, live['ticker'], 'live'),
              *_input_section('Live ', live, live_calc, 'live'), *_cases('Live ', live_calc)]
    comparison = live_calc['low_case_comparison']
    if comparison['margin_of_safety_percent'] is not None:
        lines.append(f"- Live margin of safety: {comparison['margin_of_safety_percent']}% [calc id=live_margin_of_safety]")
    else:
        lines.append('- Live margin of safety: not computed.')
    lines += [f"- View: {comparison['view']}.", f"- Conviction: {live_calc['conviction']['level']} | {live_calc['conviction']['reason']}.", '', '## Not known']
    gaps = list(dict.fromkeys(calculations['not_known'] + live_calc['not_known']))
    for gap in gaps:
        text = str(gap)
        if re.fullmatch(r'Only \d+ verified reader bars are available; \d+ are required', text):
            continue  # Presented below as independently checked reader and rule claims.
        lines.append('- ' + text)
    for name, result, reader, cutoff in (('Target', calculations, reader_path, None),
                                         ('Live', live_calc, live_reader_path, (release.get('filing_time') or {}).get('value'))):
        if result['liquidity']['median_daily_dollar_volume_usd'] is None:
            if name == 'Live' and reader and cutoff:
                lines.append(f"- Live eligible bars: {len(live['inputs']['bars'])} [calc id=eligible_live_bars ticker={live['ticker']} cutoff={cutoff} as_of={live['as_of']}]")
            lines.append(f"- {name} liquidity lookback required: {rules['lookback_days']} trading days [rule id=lookback_days]")
    for error in manifest.get('errors', []):
        lines.append('- Source gap: ' + str(error.get('stage', 'unknown')) + ' | ' + str(error.get('error', 'not known')))
    lines += ['- Automatic filing extraction may miss debt, restrictions, parent facts, insider purchases, or release facts.',
              '', '<!-- lab07-worksheet-source',
              'run=' + _q(run), 'live_run=' + _q(Path(live['run']).resolve()),
              'rules=' + _q(Path(rules_path).resolve()),
              'reader=' + (_q(Path(reader_path).resolve()) if reader_path else ''),
              'live_reader=' + (_q(Path(live_reader_path).resolve()) if live_reader_path else ''), '-->', '']
    return '\n'.join(lines)
