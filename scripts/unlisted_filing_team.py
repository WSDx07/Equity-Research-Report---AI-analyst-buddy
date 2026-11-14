"""Run the desk's model roles on an unlisted issuer's saved SEC evidence."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from dotenv import dotenv_values
from google.genai import types
from pydantic import BaseModel, Field

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from equity_desk.equity_research_roles import ProviderRouter  # noqa: E402


class Claim(BaseModel):
    text: str
    document: str
    line: int
    quote: str


class RoleOutput(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    judgment: str = ''
    gaps: list[str] = Field(default_factory=list)


def excerpt(path: Path, pattern: re.Pattern, limit: int = 45000):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    positions = {j for i, line in enumerate(lines) if pattern.search(line)
                 for j in range(max(0, i - 1), min(len(lines), i + 3))}
    output = []
    size = 0
    for i in sorted(positions):
        piece = f'{i + 1}: {lines[i]}'
        if size + len(piece) > limit:
            break
        output.append(piece)
        size += len(piece)
    return lines, '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--cik', required=True)
    parser.add_argument('--analysis-date', type=date.fromisoformat, required=True)
    parser.add_argument('--form10-filed', type=date.fromisoformat, required=True)
    parser.add_argument('--report-filed', type=date.fromisoformat, required=True)
    parser.add_argument('--form10', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.form10_filed > args.analysis_date or args.report_filed > args.analysis_date:
        raise ValueError('A filing date is after the analysis date')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    form_lines, form_text = excerpt(args.form10, re.compile(
        r'not (?:currently )?listed|business development company|investment objective|risk factors|'
        r'repurchase|net asset value|quarterly|asset coverage|securities registered|management fee', re.I))
    report_lines = args.report.read_text(encoding='utf-8', errors='replace').splitlines()
    report_text = '\n'.join(f'{i}: {line}' for i, line in enumerate(report_lines, 1))[:45000]
    sources = {'form10': form_lines, 'weekly_filing': report_lines}
    settings = dotenv_values(ROOT / '.env')
    key = (settings.get('PURDUE_API_KEY') or '').strip()
    if not key:
        raise ValueError('PURDUE_API_KEY is unavailable')
    model = (settings.get('PURDUE_MODEL') or '').strip() or 'gpt-oss:120b'
    client = ProviderRouter(None, key, model)
    roles = [('research', 'research_analyst.txt'), ('financial', 'financial_analyst.txt'),
             ('advisor', 'investment_advisor.txt'), ('manager', 'strategy_manager.txt')]
    results = {}
    issues = []
    for name, role_file in roles:
        prompt = {'issuer': args.name, 'cik': args.cik, 'analysis_date': args.analysis_date.isoformat(),
                  'filing_dates': {'form10': args.form10_filed.isoformat(), 'weekly_filing': args.report_filed.isoformat()},
                  'source_excerpts': {'form10': form_text, 'weekly_filing': report_text},
                  'prior_role_outputs': results,
                  'task': ('Use only these SEC sources. Return claims with exact source document, line number and copied quote. '
                           'Distinguish filing facts from judgment; state gaps. No invented numbers. '
                           'This issuer is unlisted: no exchange price, no pre-release close, no tradeable '
                           'market reaction, and no per-share comparison may be assumed. '
                           'If information is insufficient for an investment view say so. '
                           'The weekly Form D is an offering notice, not an earnings release.')}
        (args.output_dir / f'{name}_input.json').write_text(json.dumps(prompt, indent=2, ensure_ascii=False), encoding='utf-8')
        instructions = (ROOT / 'roles' / role_file).read_text(encoding='utf-8')
        instructions += '\nFor this unlisted-fund task, use the supplied response schema and task instead of any conflicting format instruction.'
        print('Running', name, flush=True)
        response = client.models.generate_content(model=model, contents=json.dumps(prompt, ensure_ascii=False),
                    config=types.GenerateContentConfig(system_instruction=instructions,
                    response_mime_type='application/json', response_schema=RoleOutput))
        result = RoleOutput.model_validate(response.parsed).model_dump()
        for claim in result['claims']:
            lines = sources.get(claim['document'])
            if not lines or not 1 <= claim['line'] <= len(lines) or claim['quote'] not in lines[claim['line'] - 1]:
                issues.append(f"{name}: unsupported quotation at {claim['document']} line {claim['line']}")
            # Numerical semantics require human review even when a digit appears in the source.
            if re.search(r'\d', claim['text']):
                issues.append(f"{name}: numeric claim requires independent review at {claim['document']} line {claim['line']}")
        results[name] = result
        (args.output_dir / f'{name}_output.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    (args.output_dir / 'verification.json').write_text(json.dumps({'issues': issues, 'limitations': [
        'Checks exact quote location only; it does not establish semantic support, dates, units, or completeness.',
        'Not the listed-company desk flow; no full financial statements or market-price comparison were established.']}, indent=2), encoding='utf-8')
    print('Saved unlisted-fund role outputs; unresolved verifier issues:', len(issues), flush=True)


if __name__ == '__main__':
    main()
