"""Collect and save Lab 07 source filings beside an existing agent-team run.

This command prepares sources only. It does not create or score a worksheet and
does not call a model. SEC requests use SEC_USER_AGENT and the seeker's 5 rps
client, so the same user agent and rate limit apply to every request.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[4]
SEEKER = ROOT / '.agents' / 'skills' / 'us-spinoff-seeker' / 'scripts'
EASTERN = ZoneInfo('America/New_York')
sys.path.insert(0, str(SEEKER))
import seeker  # noqa: E402


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def registry_value(entity, key):
    records = entity.get(key, []) if isinstance(entity, dict) else []
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        return None
    values = {str(record.get('value')) for record in records if isinstance(record, dict) and record.get('value') not in (None, '')}
    return next(iter(values)) if len(values) == 1 else None


def registry_accessions(entity, filing_rows, target_cik):
    accession_forms = {}
    for row in filing_rows:
        accession = re.sub(r'\D', '', str(row.get('accessionNumber', '')))
        if accession:
            accession_forms[accession] = row
    found = []
    for key, records in entity.items() if isinstance(entity, dict) else []:
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            filing = str(record.get('filing', ''))
            match = re.search(r'/Archives/edgar/data/(\d+)/(\d{18,20})(?:/|\.)', filing)
            if match and int(match.group(1)) == int(target_cik):
                accession = match.group(2)
                found.append((key, accession, accession_forms.get(accession), filing,
                              str(record.get('filing_date', ''))))
    return found


def registry_source_accessions(entity, key):
    records = entity.get(key, []) if isinstance(entity, dict) else []
    if isinstance(records, dict):
        records = [records]
    found = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        filing = str(record.get('filing', ''))
        match = re.search(r'/Archives/edgar/data/(\d+)/(\d{18,20})(?:/|\.)', filing)
        if match:
            found.append((match.group(1), match.group(2), filing,
                          str(record.get('filing_date', ''))))
    return found


def choose_registration(entity, filing_rows, target_cik):
    from_registry = registry_accessions(entity, filing_rows, target_cik)
    preferred = []
    for key, accession, row, url, filing_date in from_registry:
        form = str((row or {}).get('form', '')).upper()
        is_registration_fact = key in {'parent', 'distribution_ratio', 'record_date'}
        if form in {'10-12B', '10-12B/A', '10-12G', '10-12G/A', '10', '10/A'} or (not row and is_registration_fact):
            preferred.append((accession, row, url, filing_date))
    if preferred:
        accession, row, url, _ = max(preferred, key=lambda item: (str((item[1] or {}).get('filingDate', '')), item[3]))
        return accession, row, url
    # The user requires the accession to be established in the registry.
    return None


def registry_as_of(entity, as_of):
    """A later filing must never supply a fact to a historical run."""
    result = {}
    for key, records in (entity or {}).items():
        records = [records] if isinstance(records, dict) else records
        if not isinstance(records, list):
            continue
        result[key] = [record for record in records if isinstance(record, dict)
                       and record.get('filing_date') and record['filing_date'] <= as_of]
    return result


def numbered(text):
    lines = str(text).replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return '\n'.join(f'{index:06d} | {line}' for index, line in enumerate(lines, 1)) + '\n'


def safe_component(value):
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', str(value)).strip('._')[:120] or 'document'


def save_document(folder, accession, document_name, content, url, form, *, is_raw=False):
    safe_name = safe_component(document_name or 'submission.txt')
    safe_form = safe_component(form or 'filing')
    output = folder / f'{safe_form}_{accession}_{safe_name}.txt'
    text = str(content) if is_raw else seeker.html_text(str(content))
    output.write_text(numbered(text), encoding='utf-8')
    return {'form': form, 'accession': accession, 'name': document_name,
            'url': url, 'path': str(output.relative_to(folder.parent)), 'kind': 'raw' if is_raw else 'readable text'}


def sec_row(cik, accession, form, filing_date):
    compact = re.sub(r'\D', '', str(accession))
    if not str(cik).isdigit() or not re.fullmatch(r'\d{18}', compact):
        raise ValueError('Invalid CIK or SEC accession')
    return {'form': form, 'date': filing_date, 'cik': str(cik).zfill(10),
            'path': f'edgar/data/{int(cik)}/{compact[:10]}-{compact[10:12]}-{compact[12:]}.txt'}


def get_form_folder(client, row, target, *, expected_form=None):
    records = []
    accession = row['path'].rsplit('/', 1)[-1].removesuffix('.txt').replace('-', '')
    docs = seeker.read_filing_folder(client, row)
    for index, doc in enumerate(docs, 1):
        if not isinstance(doc.get('text'), str):
            records.append({'form': row['form'], 'accession': accession, 'url': doc.get('url'),
                            'error': doc.get('error', 'document text unavailable')})
            continue
        basename = urlparse(doc.get('url', '')).path.rsplit('/', 1)[-1]
        if doc.get('embedded_filename'):
            basename = doc['embedded_filename']
        record = save_document(target, accession, basename or f'document_{index}.txt',
                               doc['text'], doc.get('url', ''), expected_form or row['form'])
        record['filing_date'] = row.get('date')
        records.append(record)
    return records


def parse_form4_purchases(text, accession, filing_date):
    """Count transaction-table rows with transaction code P from one Form 4."""
    from xml.etree import ElementTree
    docs = seeker.submission_text_documents(text)
    if not docs:
        # Many Form 4 archive folders expose doc4.xml directly instead of a
        # complete-submission SGML file.
        try:
            ElementTree.fromstring(text)
        except ElementTree.ParseError:
            pass
        else:
            docs = {'ownership.xml': text}
    purchases = []
    for filename, body in docs.items():
        if not filename.lower().endswith(('.xml', '.txt')):
            continue
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            continue
        def first(node, suffix):
            for item in node.iter():
                if item.tag.rsplit('}', 1)[-1] == suffix:
                    # SEC ownership XML typically nests the actual text in
                    # a <value> child rather than on the enclosing element.
                    for child in item.iter():
                        if child is not item and child.tag.rsplit('}', 1)[-1] == 'value':
                            return (child.text or '').strip()
                    return (item.text or '').strip()
            return ''
        for transaction in root.iter():
            if transaction.tag.rsplit('}', 1)[-1] not in {'nonDerivativeTransaction', 'derivativeTransaction'}:
                continue
            code = first(transaction, 'transactionCode')
            if code != 'P':
                continue
            purchases.append({
                'accession': accession,
                'filing_date': filing_date,
                'transaction_date': first(transaction, 'transactionDate'),
                'transaction_code': code,
                'shares': first(transaction, 'transactionShares'),
                'price_per_share': first(transaction, 'transactionPricePerShare'),
                'security_title': first(transaction, 'securityTitle'),
                'document': filename,
            })
    return purchases


def read_form4_folder(client, row, target):
    """Read Form 4's actual archive folder and return sourced code-P rows."""
    accession = re.sub(r'\D', '', str(row['path'].rsplit('/', 1)[-1].removesuffix('.txt')))
    documents = seeker.read_filing_folder(client, row)
    saved = []
    purchases = []
    errors = []
    for index, doc in enumerate(documents, 1):
        url = doc.get('url', '')
        name = doc.get('embedded_filename') or urlparse(url).path.rsplit('/', 1)[-1]
        body = doc.get('text')
        if not isinstance(body, str):
            errors.append({'stage': 'Form 4 document', 'accession': accession,
                           'error': doc.get('error', 'document text unavailable')})
            continue
        if str(name).lower().endswith(('.xml', '.txt')):
            purchases.extend(parse_form4_purchases(body, accession, row.get('date')))
        saved.append(save_document(target, accession, name or f'document_{index}.txt',
                                   body, url, 'Form4', is_raw=str(name).lower().endswith(('.xml', '.txt'))))
        saved[-1]['filing_date'] = row.get('date')
    return saved, purchases, errors


def accession_acceptance_time(client, cik, accession, filing_date):
    """Find SEC's accepted timestamp for an accession without guessing a time."""
    base = 'https://data.sec.gov/submissions/'
    cik = str(cik).zfill(10)
    wanted = re.sub(r'\D', '', str(accession))
    main = json.loads(client.get(base + 'CIK' + cik + '.json'))
    filings = main.get('filings') or {}
    sources = [filings.get('recent') or {}]
    for item in filings.get('files', []):
        name = str(item.get('name', ''))
        filing_from = str(item.get('filingFrom', '0000-00-00'))
        filing_to = str(item.get('filingTo', '9999-99-99'))
        if (filing_from <= filing_date <= filing_to
                and re.fullmatch(r'CIK\d{10}-submissions-\d+\.json', name)):
            sources.append(json.loads(client.get(base + name)))
    for source in sources:
        accessions = source.get('accessionNumber', [])
        timestamps = source.get('acceptanceDateTime', [])
        for candidate, timestamp in zip(accessions, timestamps):
            if re.sub(r'\D', '', str(candidate)) != wanted or not timestamp:
                continue
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
            except ValueError:
                return None
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None
            return {'value': parsed.isoformat(), 'source': 'SEC submissions acceptanceDateTime'}
    return None


def prepare(args):
    run = args.run.resolve()
    facts_path = run / 'facts.json'
    filings_path = run / 'filings.json'
    if not facts_path.is_file() or not filings_path.is_file():
        raise ValueError('The selected run needs facts.json and filings.json')
    facts = read_json(facts_path)
    filings = read_json(filings_path)
    company = facts.get('company') or {}
    ticker = str(args.ticker).strip().upper()
    if ticker != str(company.get('ticker', '')).strip().upper():
        raise ValueError('Ticker does not match the selected saved run')
    cik = str(company.get('cik', '')).zfill(10)
    if not cik.isdigit():
        raise ValueError('The saved run has no valid company CIK')
    as_of = date.fromisoformat(str(args.as_of or facts.get('as_of', '')))
    registry = read_json(args.registry)
    raw_entity = registry.get(cik)
    present = raw_entity is not None
    entity = registry_as_of(raw_entity, as_of.isoformat()) if present else None
    filing_rows = ((filings.get('filings') or {}).get('filing_list') or [])
    selected_registration = choose_registration(entity or {}, filing_rows, cik) if present else None

    settings = {}
    for raw in args.env.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        settings[key.strip()] = value.strip().strip('"\'')
    client = seeker.SecClient((settings.get('SEC_USER_AGENT') or '').strip())
    output = args.output_dir.resolve() if args.output_dir else run / ('worksheet_sources_' + datetime.now().astimezone().strftime('%Y%m%d_%H%M%S'))
    output.mkdir(parents=True, exist_ok=False)
    saved = []
    errors = []
    registration_accession = None

    if present:
        if selected_registration:
            registration_accession, row, source_url = selected_registration
            if not row or not row.get('path'):
                row = sec_row(cik, registration_accession,
                              str((row or {}).get('form', '10')),
                              str((row or {}).get('filingDate') or as_of.isoformat()))
            try:
                saved.extend(get_form_folder(client, row, output, expected_form=str(row.get('form', 'Form 10'))))
            except Exception as exc:
                errors.append({'stage': 'Form 10 folder', 'accession': registration_accession,
                               'error': type(exc).__name__})
        else:
            errors.append({'stage': 'Form 10', 'error': 'No Form 10 accession was established in the registry or saved filing list'})

    live_run = args.live_run.resolve() if args.live_run else run
    live_facts_path = live_run / 'facts.json'
    live_filings_path = live_run / 'filings.json'
    live_release = {'run': str(live_run), 'ticker': None, 'cik': None, 'form': None,
                    'filing_date': None, 'accession': None, 'filing_time': None, 'documents': []}
    live_run_source_files = []
    if live_facts_path.is_file() and live_filings_path.is_file():
        live_facts = read_json(live_facts_path)
        live_company = live_facts.get('company') or {}
        live_ticker = str(live_company.get('ticker') or '').strip().upper()
        live_cik = str(live_company.get('cik') or '').zfill(10)
        live_as_of = date.fromisoformat(str(live_facts.get('as_of') or as_of.isoformat()))
        live_filings = read_json(live_filings_path)
        if live_run != run:
            for source in [live_facts_path, live_filings_path, live_run / 'calculations.json',
                           *live_run.glob('*_10-K_*.txt'), *live_run.glob('*_10-Q_*.txt'),
                           *live_run.glob('*_8-K_*.txt'), *live_run.glob('*_EX-99.1_*.txt')]:
                if not source.is_file():
                    continue
                destination = output / ('live_' + source.name)
                shutil.copyfile(source, destination)
                live_run_source_files.append(str(destination.relative_to(run)))
        live_rows = (live_filings.get('filings') or {}).get('filing_list') or []
        eligible = [row for row in live_rows if str(row.get('form', '')).upper() in {'8-K', '8-K/A'}
                    and row.get('filingDate') and row['filingDate'] <= live_as_of.isoformat()]
        if args.release_accession:
            wanted = re.sub(r'\D', '', args.release_accession)
            eligible = [row for row in eligible if re.sub(r'\D', '', str(row.get('accessionNumber', ''))) == wanted]
        else:
            # A recent 8-K can cover an unrelated event. Only choose an
            # earnings release automatically when its items identify one.
            eligible = [row for row in eligible if re.search(r'(?<!\d)2\.02(?!\d)', str(row.get('items', '')))]
        chosen = max(eligible, key=lambda row: (row['filingDate'], str(row.get('accessionNumber', '')))) if eligible else None
        live_release.update({'ticker': live_ticker or None, 'cik': live_cik if live_cik.isdigit() else None})
        if chosen and live_cik.isdigit():
            accession = re.sub(r'\D', '', str(chosen.get('accessionNumber', '')))
            release_row = sec_row(live_cik, accession, str(chosen['form']), chosen['filingDate'])
            live_release.update({'form': chosen['form'], 'filing_date': chosen['filingDate'],
                                 'accession': accession,
                                 'filing_time': accession_acceptance_time(client, live_cik, accession, chosen['filingDate'])})
            if live_release['filing_time'] is None:
                errors.append({'stage': 'live release acceptance time', 'accession': accession,
                               'error': 'SEC submissions data did not provide the accepted timestamp'})
            try:
                live_release['documents'] = get_form_folder(client, release_row, output, expected_form='live_release_' + str(chosen['form']))
                saved.extend(live_release['documents'])
            except Exception as exc:
                errors.append({'stage': 'live release filing folder', 'accession': accession,
                               'error': type(exc).__name__})
        else:
            errors.append({'stage': 'live release', 'error': 'No matching saved 8-K filing was found through the run analysis date'})
    else:
        errors.append({'stage': 'live release', 'error': 'Live release run needs facts.json and filings.json'})

    distribution_date = registry_value(entity or {}, 'distribution_date') if present else None
    parent_cik = registry_value(entity or {}, 'parent_cik') if present else None
    distribution_filing_documents = []
    if present:
        for source_cik, accession, source_url, filed in registry_source_accessions(entity or {}, 'distribution_date'):
            try:
                event_row = sec_row(source_cik, accession, '8-K', filed or as_of.isoformat())
                distribution_filing_documents.extend(
                    get_form_folder(client, event_row, output, expected_form='distribution_8-K'))
            except Exception as exc:
                errors.append({'stage': 'distribution filing folder', 'accession': accession,
                               'error': type(exc).__name__})
    company_first_post_spin = []
    if present and distribution_date:
        try:
            own_rows = seeker.submissions(client, cik, distribution_date)
            own_rows = [row for row in own_rows if row.get('form') in {'10-K', '10-Q'}
                        and row.get('date') and distribution_date < row['date'] <= as_of.isoformat()]
            if own_rows:
                first_day = min(row['date'] for row in own_rows)
                for row in own_rows:
                    if row['date'] == first_day:
                        try:
                            company_first_post_spin.extend(get_form_folder(client, row, output, expected_form='first_post_spin_' + row['form']))
                        except Exception as exc:
                            errors.append({'stage': 'first company filing after spin', 'form': row['form'], 'error': type(exc).__name__})
        except Exception as exc:
            errors.append({'stage': 'company submissions after spin', 'error': type(exc).__name__})
    parent_filing_rows = []
    if present and parent_cik and distribution_date:
        try:
            parent_rows = seeker.submissions(client, parent_cik, distribution_date)
            eligible = [row for row in parent_rows if row.get('form') in {'10-K', '10-Q'}
                        and row.get('date') and row['date'] <= as_of.isoformat()]
            latest_by_form = {}
            for row in eligible:
                if row['form'] not in latest_by_form or row['date'] > latest_by_form[row['form']]['date']:
                    latest_by_form[row['form']] = row
            for form, row in latest_by_form.items():
                try:
                    parent_filing_rows.extend(get_form_folder(client, row, output, expected_form='parent_' + form))
                except Exception as exc:
                    errors.append({'stage': 'parent filing folder', 'form': form, 'error': type(exc).__name__})
        except Exception as exc:
            errors.append({'stage': 'parent submissions', 'error': type(exc).__name__})

    form4_purchases = []
    form4_rows = [row for row in filing_rows if str(row.get('form', '')).upper() in {'4', '4/A'}
                  and row.get('filingDate') and row['filingDate'] <= as_of.isoformat()]
    if present and distribution_date:
        form4_rows = [row for row in form4_rows if row['filingDate'] >= distribution_date]
    for row in form4_rows:
        accession = re.sub(r'\D', '', str(row.get('accessionNumber', '')))
        if not accession:
            continue
        try:
            form4_row = sec_row(cik, accession, str(row.get('form', '4')), row['filingDate'])
            form4_documents, purchases, document_errors = read_form4_folder(client, form4_row, output)
            saved.extend(form4_documents)
            form4_purchases.extend(purchases)
            errors.extend(document_errors)
        except Exception as exc:
            code = getattr(exc, 'code', None)
            error = f'{type(exc).__name__} HTTP {code}' if code else type(exc).__name__
            errors.append({'stage': 'Form 4', 'accession': accession, 'error': error})

    (output / 'form4_purchases.json').write_text(json.dumps(form4_purchases, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    run_filing_paths = sorted(str(path.relative_to(run)) for pattern in ('*_10-K_*.txt', '*_10-Q_*.txt', '*_10-K*.txt', '*_10-Q*.txt') for path in run.glob(pattern))
    manifest = {
        'schema_version': 1,
        'ticker': ticker,
        'company_name': company.get('name'),
        'cik': cik,
        'as_of': as_of.isoformat(),
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'saved_run': str(run),
        'facts_file': str(facts_path),
        'filings_file': str(filings_path),
        'registry_file': str(args.registry.resolve()),
        'registry_present': present,
        'registry_facts': entity or {},
        'parent_cik': parent_cik,
        'distribution_date': distribution_date,
        'registration_accession': registration_accession,
        'distribution_filing_documents': distribution_filing_documents,
        'live_release': live_release,
        'live_run_source_files': live_run_source_files,
        'run_filing_texts': run_filing_paths,
        'first_company_filings_after_spin': company_first_post_spin,
        'parent_filings_after_spin': parent_filing_rows,
        'saved_source_documents': saved,
        'form4_purchase_transactions': len(form4_purchases),
        'form4_purchase_file': str((output / 'form4_purchases.json').resolve()),
        'form4_coverage': {
            'filing_count_checked': len(form4_rows),
            'first_filing_date': min((row['filingDate'] for row in form4_rows), default=None),
            'last_filing_date': max((row['filingDate'] for row in form4_rows), default=None),
            'scope': 'Form 4 filings in the saved run filing list, through the saved run analysis date',
        },
        'errors': errors,
        'limitations': [
            'This command collects and saves sources only; it does not extract worksheet facts, calculate values, call a model, or create a report.',
            'A missing or conflicting fact stays not known. Registry presence is distinct from an absent CIK entry.',
            'The saved agent run may not include every filing. The worksheet must state the saved filing-list coverage.',
        ],
    }
    (output / 'sources.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description='Save Lab 07 source filings beside a saved agent-team run')
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--ticker', required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--env', type=Path, required=True)
    parser.add_argument('--live-run', type=Path, help='Optional saved run for a separate live-release company')
    parser.add_argument('--release-accession', help='Optional SEC accession for the selected live-release 8-K')
    parser.add_argument('--as-of', help='Use a YYYY-MM-DD date; defaults to the saved run date')
    parser.add_argument('--output-dir', type=Path, help='Optional new output folder; it must not already exist')
    args = parser.parse_args()
    output, manifest = prepare(args)
    print(f'Source pack: {output.resolve()}')
    print(f"Registry present: {'yes' if manifest['registry_present'] else 'no'}")
    print(f"Saved documents: {len(manifest['saved_source_documents'])}")
    print(f"Form 4 code-P transactions: {manifest['form4_purchase_transactions']}")
    if manifest['errors']:
        print(f"Source gaps: {len(manifest['errors'])} (see sources.json)")


if __name__ == '__main__':
    main()
