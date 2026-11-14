"""Build a dated worksheet from saved filings, registry facts, and reader bars."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import requests

import prepare_worksheet
import worksheet_evidence
import worksheet_math


ROOT = Path(__file__).resolve().parents[4]
EASTERN = ZoneInfo('America/New_York')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def settings(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def snapshot(run, registry, bars_path, cutoff=None):
    run = Path(run).resolve()
    facts = load(run / 'facts.json')
    company = facts.get('company') or {}
    ticker = str(company.get('ticker') or '').strip().upper()
    cik = str(company.get('cik') or '').zfill(10)
    if not ticker or not cik.isdigit() or int(cik) == 0:
        raise ValueError('Saved run must identify its ticker and CIK')
    as_of = date.fromisoformat(str(facts.get('as_of', ''))).isoformat()
    financial_as_of = as_of
    if cutoff is not None and cutoff is not False:
        # Filing lists have a date but not necessarily a time. Exclude the
        # release day for annual inputs so a later same-day filing cannot leak.
        financial_as_of = min(as_of, (cutoff.astimezone(EASTERN).date() - timedelta(days=1)).isoformat())
    present = cik in registry
    entity = worksheet_evidence.dated_registry(registry.get(cik), financial_as_of)
    spin_date = prepare_worksheet.registry_value(entity, 'distribution_date') if present else None
    dated_facts = dict(facts, as_of=financial_as_of)
    financial = worksheet_evidence.read_financial_inputs(run, dated_facts, spin_date)
    bars = worksheet_evidence.load_bars(bars_path, ticker, cik, as_of)
    if cutoff is False:
        bars = []
    elif cutoff is not None:
        bars = [row for row in bars if datetime.combine(date.fromisoformat(row['date']), time(16), EASTERN) < cutoff]
    # Convert the reader's validated Decimal values into the calculator schema.
    clean_bars = [{'ticker': ticker, 'date': b['date'], 'close': str(b['close']),
                   'volume': str(b['volume']), 'basis': 'official_unadjusted',
                   'session': 'regular', 'when_issued': False} for b in bars]
    if clean_bars:
        last = clean_bars[-1]
        reader_data = load(bars_path)
        reader_source = str(Path(bars_path).resolve())
        if reader_data.get('basis') == 'user_asserted_official_unadjusted':
            reader_source += ' | LSEG TR.CLOSEPRICE(Adjusted=0), TR.Volume; field interpretation supplied by user; independent exchange comparison not completed'
        financial['market_price'] = {'value': last['close'], 'date': last['date'],
                                     'reader_source': reader_source,
                                     'basis': 'official_unadjusted'}
    absences = worksheet_evidence.find_explicit_absences(run, dated_facts, financial_as_of, spin_date)
    unknowns = ['debt covenants', 'parent liabilities', 'parent restrictions'] if present else ['debt covenants']
    unknowns = [name for name in unknowns if name not in absences]
    inputs = {'as_of': as_of, 'inputs': financial, 'bars': clean_bars,
              'material_unknowns': unknowns}
    return {'run': run, 'facts': facts, 'ticker': ticker, 'cik': cik, 'as_of': as_of, 'financial_as_of': financial_as_of,
            'present': present, 'registry': entity, 'inputs': inputs, 'explicit_absences': absences}


def fact_line(label, item):
    if not item:
        return f'- {label}: not known (not established by the automatic reader).'
    detail = f" | {item['description']}" if item.get('description') else ''
    line = f" | line {item['line']}" if item.get('line') else ''
    return (f"- {label}: {item['value']} {item['unit']}{detail} | {item['tag']} | {item['period']} | "
            f"filing {item['filing']} | {item['section']}{line} | saved file {item['source_file']}")


def registry_lines(bundle, manifest=None):
    labels = [('parent', 'Parent'), ('distribution_ratio', 'Distribution ratio'),
              ('record_date', 'Record date'), ('distribution_date', 'Distribution date')]
    output = []
    for key, label in labels:
        if not bundle['present']:
            output.append(f'- {label}: not applicable')
            continue
        item = worksheet_evidence.registry_record(bundle['registry'], key)
        if manifest is not None:
            urls = set()
            source_documents = []
            for source_key in ('saved_source_documents', 'distribution_filing_documents',
                               'first_company_filings_after_spin', 'parent_filings_after_spin'):
                source_documents.extend(manifest.get(source_key, []))
            for doc in source_documents:
                if not doc.get('path') or not doc.get('url'):
                    continue
                source = (bundle['run'] / doc['path']).resolve()
                if not source.is_relative_to(bundle['run']) or not source.is_file():
                    continue
                urls.add(str(doc['url']))
            records = bundle['registry'].get(key, [])
            records = [records] if isinstance(records, dict) else records
            values = prepare_worksheet.registry_value(bundle['registry'], key)
            matching = [r for r in records if isinstance(r, dict) and str(r.get('value')) == values
                        and r.get('filing') in urls and r.get('section')]
            matching.sort(key=lambda record: str(record.get('filing_date') or ''))
            item = matching[-1] if matching else None
        if item:
            output.append(f"- {label}: {item['value']} | {item['filing']} | {item['section']}")
        else:
            output.append(f'- {label}: not known (the dated registry fact was not established in a saved information statement).')
    return output


def model_judgment(key, model, persona, payload, post=requests.post):
    if not key:
        raise ValueError('PURDUE_API_KEY is missing from the selected .env file')
    prompt = ('Use only the supplied sourced facts and already calculated comparison. '
              'Make no calculations and do not introduce new factual claims or any numbers. '
              'Return JSON with two short strings named story and change: explain whether '
              'the spinoff may be cheap or the story does not fit, and specify evidence '
              'in the next filing that would change that view. If evidence is missing say so.\n'
              + json.dumps(payload, ensure_ascii=False))
    system = persona + ('\n\nFor this worksheet, do not calculate, estimate, give a Buy/Hold/Sell '
                        'rating, introduce facts, or include numbers in the response. '
                        'The supplied worksheet rules control if they conflict with the persona.')
    body = {'model': model, 'messages': [{'role': 'system', 'content': system},
                                       {'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'worksheet_judgment',
                'schema': {'type': 'object', 'properties': {'story': {'type': 'string'},
                           'change': {'type': 'string'}}, 'required': ['story', 'change'],
                           'additionalProperties': False}}}, 'stream': False}
    response = post('https://genai.rcac.purdue.edu/api/chat/completions',
                    headers={'Authorization': 'Bearer ' + key}, json=body, timeout=180)
    response.raise_for_status()
    parsed = json.loads(response.json()['choices'][0]['message']['content'])
    if not isinstance(parsed, dict) or not all(isinstance(parsed.get(k), str) and parsed[k].strip() for k in ('story', 'change')):
        raise ValueError('Model did not return the required two judgment fields')
    if any(re.search(r'\d', parsed[k]) for k in ('story', 'change')):
        raise ValueError('Model judgment contained numbers; no worksheet was saved')
    return {'story': parsed['story'].strip(), 'change': parsed['change'].strip()}


def fmt(value):
    return str(value) if value is not None else 'not computed'


def render(bundle, calculations, manifest, purchases, judgment, live, live_calc, rules):
    registration = manifest.get('registration_accession')
    sources = registration if registration and any(
        str(doc.get('accession')) == str(registration) and doc.get('path')
        for doc in manifest.get('saved_source_documents', [])) else 'not read'
    release = manifest.get('live_release') or {}
    release_read = release.get('accession') if any(doc.get('path') for doc in release.get('documents', [])) else 'not read'
    financial_sources = sorted({str(item['filing']) for key, item in bundle['inputs']['inputs'].items()
                                if key != 'market_price' and isinstance(item, dict) and item.get('filing')})
    lines = [f"Filings read: Form 10 accession {sources}; statement accessions {', '.join(financial_sources) or 'not read'}; live release accession {release_read}",
             '', f"# Worksheet: {bundle['ticker']} | analysis date {bundle['as_of']}", '',
             '## Spinoff facts', *registry_lines(bundle, manifest)]
    if bundle['present']:
        completed = worksheet_evidence.registry_record(bundle['registry'], 'distribution_date')
        if completed:
            lines.append(f"- Completed distribution date: {completed['value']} | {completed['filing']} | {completed['section']}")
    price = calculations['market_price']
    lines.append(f"- Dated market price: {fmt(price['value_usd'])} USD per share on {price['date'] or 'not computed'} | {price.get('source') or 'reader unavailable'}")
    lines.extend(['', '## Judgment', judgment['story'],
                  'Evidence in the next filing that would change the view: ' + judgment['change'],
                  '', '## Owner cash flow and value range'])
    for key, label in [('after_tax_earnings', 'After-tax earnings'), ('depreciation', 'Depreciation'),
                       ('capital_spending', 'Capital spending'), ('diluted_shares', 'Diluted shares outstanding')]:
        lines.append(fact_line(label, bundle['inputs']['inputs'].get(key)))
    if bundle['inputs']['inputs'].get('common_shares'):
        lines.append(fact_line('Common shares outstanding (cover page)', bundle['inputs']['inputs']['common_shares']))
    ocf = calculations['owner_cash_flow']
    values = ocf['inputs']
    lines.append(f"- Owner cash flow: {fmt(ocf['value_usd'])} USD = {fmt(values['after_tax_earnings'])} + {fmt(values['depreciation'])} - {fmt(values['capital_spending'])}.")
    for case in ('low', 'mid'):
        item = calculations['value_range'].get(case, {})
        lines.append(f"- {case.title()} case equity value: {fmt(ocf['value_usd'])} x (1 + {rules[case + '_growth_rate']}) / ({rules[case + '_discount_rate']} - {rules[case + '_growth_rate']}) = {fmt(item.get('equity_value_usd'))} USD.")
        lines.append(f"- {case.title()} case value per share: {fmt(item.get('equity_value_usd'))} / {fmt(calculations['shares'])} shares = {fmt(item.get('value_per_share_usd'))} USD per share.")
    lines.append(f"- Price against low case: {fmt(price['value_usd'])} USD on {price['date'] or 'not computed'} versus {fmt(calculations['value_range'].get('low', {}).get('value_per_share_usd'))} USD per share.")
    financing = bundle.get('financing', {})
    lines.extend(['', '## Debt and parent',
                  fact_line('Debt raised', financing.get('debt_raised')),
                  fact_line('Expected cash distribution', financing.get('cash_use')),
                  fact_line('Debt covenants', bundle['explicit_absences'].get('debt covenants')),
                  fact_line('Parent liabilities', financing.get('parent_liabilities') or bundle['explicit_absences'].get('parent liabilities')) if bundle['present'] else '- Parent liabilities: not applicable',
                  fact_line('Parent restrictions', financing.get('restrictions') or bundle['explicit_absences'].get('parent restrictions')) if bundle['present'] else '- Parent restrictions: not applicable',
                  fact_line('Parent after the spin', bundle.get('parent_after_spin')) if bundle['present'] else '- Parent after the spin: not applicable',
                  '', '## Insider purchases'])
    if purchases:
        for row in purchases:
            spin_date = prepare_worksheet.registry_value(bundle['registry'], 'distribution_date') if bundle['present'] else None
            reporting = 'reported after the spin' if spin_date and str(row.get('filing_date') or '') >= spin_date else 'historical'
            source = (f"{reporting} | transaction date {row.get('transaction_date') or 'not known'} | "
                      f"Form 4 {row.get('accession')} | transaction table, code P | {row.get('document')}")
            lines.append(f"- Insider shares purchased: {row.get('shares') or 'not known'} shares | {source}")
            lines.append(f"- Insider purchase price: {row.get('price_per_share') or 'not known'} USD per share | {source}")
    else:
        lines.append('- Insider purchases: not known (no code P transaction established within the saved filing-list coverage).')
    coverage = manifest.get('form4_coverage') or {}
    lines.append(f"- Filing-list coverage: {coverage.get('first_filing_date') or 'not known'} to {coverage.get('last_filing_date') or 'not known'}.")
    liquidity = calculations['liquidity']
    lines.extend(['', '## Liquidity',
                  f"- Median daily dollar volume: {fmt(liquidity['median_daily_dollar_volume_usd'])} USD | {liquidity['lookback_days']} completed observations | {price.get('source') or 'reader unavailable'}.",
                  f"- Client purchase: {liquidity['client_purchase_size_usd']} USD | liquidity support: {liquidity['supported'] if liquidity['supported'] is not None else 'not known'}."])
    for bar in liquidity['observations_used']:
        lines.append(f"- Daily dollar volume: {bar['dollar_volume_usd']} USD on {bar['date']}.")
    comparison = live_calc['low_case_comparison']
    live_price = live_calc['market_price']
    lines.extend(['', '## Live release view',
                  f"- Company: {live['ticker']} | saved run analysis date {live['as_of']} | financial filings through {live['financial_as_of']} | filing {release.get('accession') or 'not known'} | acceptance {((release.get('filing_time') or {}).get('value') or 'not known')}.",
                  fact_line('Release revenue', live.get('release_facts', {}).get('revenue')),
                  f"- Price: {fmt(live_price['value_usd'])} USD per share on {live_price['date'] or 'not computed'} | {live_price.get('source') or 'reader unavailable'}.",
                  fact_line('Live after-tax earnings', live['inputs']['inputs'].get('after_tax_earnings')),
                  fact_line('Live depreciation', live['inputs']['inputs'].get('depreciation')),
                  fact_line('Live capital spending', live['inputs']['inputs'].get('capital_spending')),
                  fact_line('Live diluted shares outstanding', live['inputs']['inputs'].get('diluted_shares')),
                  f"- Live owner cash flow: {fmt(live_calc['owner_cash_flow']['value_usd'])} USD = {fmt(live_calc['owner_cash_flow']['inputs']['after_tax_earnings'])} + {fmt(live_calc['owner_cash_flow']['inputs']['depreciation'])} - {fmt(live_calc['owner_cash_flow']['inputs']['capital_spending'])}.",
                  f"- Low case: {fmt(live_calc['value_range'].get('low', {}).get('value_per_share_usd'))} USD per share | owner cash flow x (1 + {rules['low_growth_rate']}) / ({rules['low_discount_rate']} - {rules['low_growth_rate']}) / diluted shares.",
                  f"- View: {comparison['view']} | deciding margin of safety: {str(comparison['margin_of_safety_percent']) + '%' if comparison['margin_of_safety_percent'] is not None else 'not computed'} | (low-case value - dated price) / dated price x 100.",
                  f"- Conviction: {live_calc['conviction']['level']} | {live_calc['conviction']['reason']}.",
                  '', '## Not known'])
    gaps = list(calculations['not_known'] + live_calc['not_known'])
    for key, label in [('debt_raised', 'Debt raised'), ('cash_use', 'Use of debt proceeds'),
                       ('parent_liabilities', 'Parent liabilities')]:
        if key not in financing and not (key == 'parent_liabilities' and bundle['explicit_absences'].get('parent liabilities')) and (key != 'parent_liabilities' or bundle['present']):
            gaps.append(label + ': automatic reader did not establish the fact')
    if bundle['present']:
        if 'restrictions' not in financing and not bundle['explicit_absences'].get('parent restrictions'):
            gaps.append('Parent restrictions: automatic reader did not establish the fact')
        if not bundle.get('parent_after_spin'):
            gaps.append('Parent after the spin: automatic reader did not establish the fact')
        gaps.extend(line.removeprefix('- ') for line in registry_lines(bundle, manifest) if 'not known' in line)
    if not purchases:
        gaps.append('Insider purchases: no code P transaction established within the saved filing-list coverage')
    if not release.get('accession'):
        gaps.append('Live release filing: no selected earnings release was established')
    if not (release.get('filing_time') or {}).get('value'):
        gaps.append('Live release acceptance time: not established')
    if not live.get('release_facts'):
        gaps.append('Release revenue: automatic reader did not establish a sourced amount')
    gaps = list(dict.fromkeys(gaps))
    lines.extend('- ' + gap for gap in gaps)
    for error in manifest.get('errors', []):
        lines.append('- Source gap: ' + str(error.get('stage', 'unknown')) + ' | ' + str(error.get('error', 'not known')))
    lines.append('')
    return '\n'.join(lines)


def run(args, prepare=prepare_worksheet.prepare, judge=model_judgment):
    facts = load(args.run / 'facts.json')
    ticker = str((facts.get('company') or {}).get('ticker') or '').upper()
    registry = load(args.registry)
    cfg = settings(args.env)
    if not cfg.get('PURDUE_API_KEY'):
        raise ValueError('PURDUE_API_KEY is missing from the selected .env file')
    persona = args.persona.read_text(encoding='utf-8')
    rules = worksheet_math.read_rules(args.rules)
    target = snapshot(args.run, registry, args.bars)
    print('Collecting saved-run and SEC sources.', flush=True)
    source_args = SimpleNamespace(run=args.run, ticker=ticker, registry=args.registry, env=args.env,
                                  live_run=args.live_run, release_accession=args.release_accession,
                                  as_of=None, output_dir=None)
    source_dir, manifest = prepare(source_args)
    # Form 10 files fetched by prepare can supply additional sourced inputs.
    target = snapshot(args.run, registry, args.bars)
    target['financing'] = worksheet_evidence.extract_financing_facts(
        args.run, manifest, target['registry'], target['as_of']) if target['present'] else {}
    target['parent_after_spin'] = worksheet_evidence.extract_parent_after_spin(
        args.run, manifest, prepare_worksheet.registry_value(target['registry'], 'distribution_date'),
        target['as_of']) if target['present'] else None
    calculated = worksheet_math.calculate(target['inputs'], rules)
    release = manifest.get('live_release') or {}
    raw_time = (release.get('filing_time') or {}).get('value')
    cutoff = None
    if raw_time:
        cutoff = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            cutoff = None
    live_run = args.live_run or args.run
    # Without an acceptance time there is no defensible pre-release close.
    live = snapshot(live_run, registry, args.live_bars or (args.bars if not args.live_run else None), cutoff=cutoff if cutoff else False)
    live['release_facts'] = worksheet_evidence.extract_release_facts(args.run, release)
    live_calculated = worksheet_math.calculate(live['inputs'], rules)
    filing_inputs = {key: value for key, value in target['inputs']['inputs'].items() if key != 'market_price'}
    live_filing_inputs = {key: value for key, value in live['inputs']['inputs'].items() if key != 'market_price'}
    purchases = load(manifest['form4_purchase_file']) if manifest.get('form4_purchase_file') else []
    payload = {'filing_facts': registry_lines(target, manifest),
               'financing_facts': target['financing'], 'explicit_absences': target['explicit_absences'],
               'parent_after_spin': target['parent_after_spin'],
               'insider_purchases': purchases,
               'financial_inputs': filing_inputs,
               'owner_cash_flow': calculated['owner_cash_flow'],
               'value_range': calculated['value_range'],
               'price_against_low': {'price': calculated['market_price']['value_usd'],
                                     'date': calculated['market_price']['date'],
                                     'comparison': calculated['low_case_comparison']},
               'missing_filing_facts': [key for key in ('after_tax_earnings', 'depreciation', 'capital_spending', 'diluted_shares')
                                        if key not in filing_inputs],
               'material_unknowns': target['inputs']['material_unknowns'],
               'live_release': {'accession': release.get('accession'), 'filing_date': release.get('filing_date'),
                                'filing_facts': live['release_facts'],
                                'explicit_absences': live['explicit_absences'],
                                'financial_inputs': live_filing_inputs,
                                'value_range': live_calculated['value_range'],
                                'price': live_calculated['market_price']['value_usd'],
                                'price_date': live_calculated['market_price']['date'],
                                'comparison': live_calculated['low_case_comparison']}}
    # Never send the licensed history or liquidity calculations to the model.
    print('Requesting the single qualitative judgment.', flush=True)
    judgment = judge(cfg['PURDUE_API_KEY'], cfg.get('PURDUE_MODEL') or 'gpt-oss:120b', persona, payload)
    text = render(target, calculated, manifest, purchases, judgment, live, live_calculated, rules)
    stamp = datetime.now().astimezone().strftime('%Y%m%d-%H%M%S-%f')
    output = args.run.resolve() / f'worksheet-{stamp}.md'
    output.write_text(text, encoding='utf-8')
    selected_live_bars = args.live_bars or (args.bars if not args.live_run else None)
    record = {'schema_version': 1, 'ticker': live['ticker'], 'worksheet_file': '../' + output.name,
              'live_view': {'ticker': live['ticker'], 'filing_time': raw_time,
                            'view_time': datetime.now(timezone.utc).isoformat(),
                            'direction': live_calculated['low_case_comparison']['view'],
                            'reader_file': str(selected_live_bars.resolve()) if selected_live_bars else None}}
    index_dir = args.run.resolve() / f'worksheet-{stamp}'
    index_dir.mkdir()
    (index_dir / 'worksheet.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(f'Worksheet: {output}')
    print(f'Sources: {source_dir}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--env', type=Path, default=ROOT / '.env')
    parser.add_argument('--rules', type=Path, default=ROOT / 'lab07_worksheet_rules.md')
    parser.add_argument('--persona', type=Path, default=ROOT / 'personas' / 'investment_advisor.md')
    parser.add_argument('--bars', type=Path, help='Verified reader bars for the worksheet ticker')
    parser.add_argument('--live-run', type=Path, help='Saved team run for a separate live-release company')
    parser.add_argument('--live-bars', type=Path, help='Verified reader bars for the live-release ticker')
    parser.add_argument('--release-accession', help='Select the live release 8-K accession')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
