"""Save a completed worksheet beside its source run and create hit-rate metadata."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def save(args):
    run = args.run.resolve()
    if not (run / 'facts.json').is_file() or not (run / 'filings.json').is_file():
        raise ValueError('The worksheet must be saved beside a run with facts.json and filings.json')
    output = args.output.resolve()
    if not output.is_relative_to(run):
        raise ValueError('Worksheet output must be inside the saved run folder')
    if output.exists():
        raise FileExistsError(f'Worksheet already exists: {output}')
    index_path = output.with_name('worksheet.json')
    if index_path.exists():
        raise FileExistsError(f'Worksheet index already exists: {index_path}')
    for input_path in (args.draft, args.rules, args.reader):
        if input_path and not input_path.is_file():
            raise ValueError(f'Input file does not exist: {input_path}')
    live_reader = (args.live_reader or args.reader).resolve()
    if not live_reader.is_file():
        raise ValueError(f'Live-release reader file does not exist: {live_reader}')
    view = json.loads(args.live_view.read_text(encoding='utf-8'))
    if not isinstance(view, dict):
        raise ValueError('Live view file must contain a JSON object')
    if not str(view.get('ticker') or '').strip():
        raise ValueError('Live view must identify its ticker')
    draft = args.draft.read_text(encoding='utf-8')
    rules = args.rules.resolve()
    reader = args.reader.resolve()
    header = (
        '<!-- lab07-worksheet-source\n'
        f'run={json.dumps(str(run))}\n'
        f'rules={json.dumps(str(rules))}\n'
        f'reader={json.dumps(str(reader))}\n'
        f'live_reader={json.dumps(str(live_reader))}\n'
        '-->\n'
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + draft.lstrip(), encoding='utf-8')

    view['reader_file'] = str(live_reader)
    meta = {
        'schema_version': 1,
        'ticker': str(view.get('ticker') or '').upper(),
        'live_view': view,
        'worksheet_file': output.name,
        'saved_at': datetime.now(timezone.utc).isoformat(),
    }
    index_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description='Save a dated Lab 07 worksheet in its saved run')
    parser.add_argument('--draft', type=Path, required=True, help='Completed worksheet Markdown draft')
    parser.add_argument('--run', type=Path, required=True, help='Saved run folder')
    parser.add_argument('--rules', type=Path, required=True, help='Worksheet rules Markdown file')
    parser.add_argument('--reader', type=Path, required=True, help='Reader bars JSON file')
    parser.add_argument('--live-reader', type=Path, help='Optional close history for a separate live-release ticker')
    parser.add_argument('--live-view', type=Path, required=True, help='Live release view JSON')
    parser.add_argument('--output', type=Path, required=True, help='New worksheet path inside the saved run')
    args = parser.parse_args()
    output = save(args)
    print(f'Worksheet: {output}')
    print(f'Worksheet index: {output.with_name("worksheet.json")}')


if __name__ == '__main__':
    main()
