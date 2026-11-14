"""Deterministic worksheet arithmetic. No company facts are inferred here."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median


def dec(value, label):
    try:
        number = Decimal(str(value).replace(',', '').replace('$', '').replace('%', '').strip())
    except (InvalidOperation, TypeError, AttributeError) as exc:
        raise ValueError(f'Invalid {label}') from exc
    if not number.is_finite():
        raise ValueError(f'Invalid {label}')
    return number


def _section(text, start, end=None):
    i = text.lower().find(start.lower())
    if i < 0:
        raise ValueError(f'Worksheet rules are missing: {start}')
    j = text.lower().find(end.lower(), i + len(start)) if end else -1
    return text[i:] if j < 0 else text[i:j]


def _one(pattern, text, label):
    match = re.search(pattern, text, re.I | re.M)
    if not match:
        raise ValueError(f'Worksheet rules are missing {label}')
    return match.group(1)


def read_rules(path):
    text = Path(path).read_text(encoding='utf-8')
    low = _section(text, '## 3. Low and mid cases', '## 4.')
    purchase = _one(r'Client purchase size:\s*\$([\d,]+)\s*USD', text, 'client purchase size')
    lookback = _one(r'Lookback period:\s*(\d+)\s+completed trading days', text, 'lookback period')
    low_case = _section(low, 'Low case (conservative floor):', 'Mid case (base case):')
    mid_case = _section(low, 'Mid case (base case):', 'Case comparison:')
    low_r = _one(r'Discount rate\s*\(\$r\$\):\s*([\d.]+)%', low_case, 'low discount rate')
    low_g = _one(r'Perpetual growth rate\s*\(\$g\$\):\s*([\d.]+)%', low_case, 'low growth rate')
    mid_r = _one(r'Discount rate\s*\(\$r\$\):\s*([\d.]+)%', mid_case, 'mid discount rate')
    mid_g = _one(r'Perpetual growth rate\s*\(\$g\$\):\s*([\d.]+)%', mid_case, 'mid growth rate')
    safety = _one(r'Dated market price\s*<=\s*([\d.]+)\s*x\s*Low-Case Value Per Share', text, 'margin-of-safety cutoff')
    participation = _one(r'\$[\d,]+\s*<=\s*([\d.]+)\s*x\s*median daily dollar volume', text, 'liquidity limit')
    return {
        'purchase_size_usd': str(Decimal(purchase.replace(',', ''))),
        'lookback_days': int(lookback),
        'low_discount_rate': str(Decimal(low_r) / 100),
        'low_growth_rate': str(Decimal(low_g) / 100),
        'mid_discount_rate': str(Decimal(mid_r) / 100),
        'mid_growth_rate': str(Decimal(mid_g) / 100),
        'safety_price_multiple': safety,
        'max_volume_participation': participation,
    }


def _sourced_number(inputs, key, *, allow_negative=False):
    item = inputs.get(key)
    if not isinstance(item, dict) or item.get('value') in (None, ''):
        return None, f'{key} is not known'
    required = ('tag', 'period', 'filing', 'section')
    missing = [field for field in required if not item.get(field)]
    if missing:
        return None, f'{key} is missing source fields: {", ".join(missing)}'
    if item.get('tag') not in {'historical', 'pro forma', 'reported after the spin'}:
        return None, f'{key} has an invalid reporting tag'
    try:
        number = dec(item['value'], key)
    except ValueError as exc:
        return None, str(exc)
    if not allow_negative and number < 0:
        return None, f'{key} must be a non-negative amount'
    return number, None


def _validated_bars(bars, as_of):
    if not isinstance(bars, list):
        raise ValueError('Reader bars must be a list')
    seen = set()
    clean = []
    cutoff = date.fromisoformat(as_of)
    for bar in bars:
        if not isinstance(bar, dict):
            raise ValueError('Invalid reader bar')
        day = date.fromisoformat(str(bar.get('date', '')))
        if day > cutoff or day.isoformat() in seen:
            if day.isoformat() in seen:
                raise ValueError('Duplicate reader bar date')
            continue
        if bar.get('basis') != 'official_unadjusted' or bar.get('session') != 'regular' or bar.get('when_issued') is True:
            raise ValueError('Liquidity bars must be official, unadjusted regular-way observations')
        close = dec(bar.get('close'), 'close')
        volume = dec(bar.get('volume'), 'share volume')
        if close <= 0 or volume < 0 or volume != volume.to_integral_value():
            raise ValueError('Invalid reader close or share volume')
        seen.add(day.isoformat())
        clean.append({'date': day.isoformat(), 'close': close, 'volume': volume})
    return sorted(clean, key=lambda row: row['date'])


def calculate(inputs, rules):
    """Return reproducible arithmetic and reasons for any missing result.

    ``inputs`` is a structured evidence object. Each financial amount must carry
    its reporting tag, period, filing and section. ``rules`` comes from read_rules.
    """
    sources = inputs.get('inputs', {}) if isinstance(inputs, dict) else {}
    as_of = date.fromisoformat(str(inputs.get('as_of', '')))
    earnings, e_gap = _sourced_number(sources, 'after_tax_earnings', allow_negative=True)
    depreciation, d_gap = _sourced_number(sources, 'depreciation')
    capex, c_gap = _sourced_number(sources, 'capital_spending')
    shares, s_gap = _sourced_number(sources, 'diluted_shares')
    price_item = sources.get('market_price') if isinstance(sources, dict) else None
    price = None
    price_gap = None
    price_date = None
    if not isinstance(price_item, dict) or price_item.get('value') in (None, ''):
        price_gap = 'market price is not available from the closes reader'
    else:
        try:
            price = dec(price_item['value'], 'market price')
            price_date = date.fromisoformat(str(price_item['date'])).isoformat()
            if (price <= 0 or date.fromisoformat(price_date) > as_of
                    or not price_item.get('reader_source') or price_item.get('basis') != 'official_unadjusted'):
                raise ValueError('Market price is missing its verified reader source')
        except (ValueError, KeyError, TypeError) as exc:
            price = None
            price_gap = str(exc)

    ocf = None
    ocf_gap = None
    if earnings is None or depreciation is None or capex is None:
        ocf_gap = '; '.join(item for item in (e_gap, d_gap, c_gap) if item)
    else:
        ocf = earnings + depreciation - capex

    cases = {}
    if ocf is not None:
        for name, r_key, g_key in (
            ('low', 'low_discount_rate', 'low_growth_rate'),
            ('mid', 'mid_discount_rate', 'mid_growth_rate'),
        ):
            rate = dec(rules[r_key], f'{name} discount rate')
            growth = dec(rules[g_key], f'{name} growth rate')
            if rate <= growth:
                raise ValueError(f'{name} discount rate must exceed growth rate')
            equity_value = ocf * (Decimal('1') + growth) / (rate - growth)
            per_share = equity_value / shares if shares and shares > 0 else None
            cases[name] = {
                'discount_rate': str(rate), 'growth_rate': str(growth),
                'equity_value_usd': str(equity_value),
                'value_per_share_usd': str(per_share) if per_share is not None else None,
                'formula': 'Owner cash flow x (1 + g) / (r - g)',
            }

    raw_bars = inputs.get('bars', [])
    if not raw_bars and inputs.get('bars_file'):
        bars_path = Path(inputs['bars_file'])
        if not bars_path.is_absolute():
            bars_path = Path(inputs.get('_input_directory', '.')) / bars_path
        data = json.loads(bars_path.read_text(encoding='utf-8'))
        raw_bars = data.get('bars', data.get('data', [])) if isinstance(data, dict) else data
    bars = _validated_bars(raw_bars, as_of.isoformat())
    lookback = int(rules['lookback_days'])
    liquidity = {'lookback_days': lookback, 'median_daily_dollar_volume_usd': None,
                 'observations_used': [], 'client_purchase_size_usd': rules['purchase_size_usd'],
                 'supported': None, 'reason': None}
    if len(bars) < lookback:
        liquidity['reason'] = f'Only {len(bars)} verified reader bars are available; {lookback} are required'
    else:
        recent = bars[-lookback:]
        dollar_volumes = [row['close'] * row['volume'] for row in recent]
        med = median(dollar_volumes)
        participation = dec(rules['max_volume_participation'], 'volume participation limit')
        purchase = dec(rules['purchase_size_usd'], 'purchase size')
        liquidity.update({
            'median_daily_dollar_volume_usd': str(med),
            'observations_used': [
                {'date': row['date'], 'dollar_volume_usd': str(dv)}
                for row, dv in zip(recent, dollar_volumes)
            ],
            'supported': purchase <= participation * med,
            'maximum_supported_purchase_usd': str(participation * med),
            'participation_limit': str(participation),
        })

    low_per_share = cases.get('low', {}).get('value_per_share_usd')
    margin = None
    view = 'not computed'
    if price is not None and low_per_share is not None:
        low_number = dec(low_per_share, 'low-case value per share')
        margin = (low_number - price) / price * Decimal('100')
        view = 'more than price' if margin > 0 else 'less than price'

    material_unknowns = inputs.get('material_unknowns', [])
    if not isinstance(material_unknowns, list):
        raise ValueError('material_unknowns must be a list')
    conviction = 'not computed'
    conviction_reason = None
    if price is None:
        conviction_reason = price_gap or 'market price is not known'
    else:
        price_pass = None
        if low_per_share is not None:
            price_cutoff = dec(rules['safety_price_multiple'], 'margin-of-safety cutoff') * dec(low_per_share, 'low-case value per share')
            price_pass = price <= price_cutoff
        high_conditions = [
            ('price at or below low-case threshold', price_pass),
            ('purchase size within liquidity limit', liquidity['supported']),
            ('no material debt, covenant, parent-liability, or restriction gaps', not material_unknowns),
        ]
        states = [ok for _, ok in high_conditions]
        conviction = 'low' if False in states else ('high' if all(ok is True for ok in states) else 'not computed')
        conviction_reason = '; '.join(f'{label}: {"unknown" if ok is None else "pass" if ok else "fail"}' for label, ok in high_conditions)

    missing = [gap for gap in (ocf_gap, s_gap, price_gap, liquidity['reason']) if gap]
    missing.extend(str(item) for item in material_unknowns if item)
    return {
        'as_of': as_of.isoformat(),
        'owner_cash_flow': {
            'value_usd': str(ocf) if ocf is not None else None,
            'formula': 'After-tax earnings + depreciation - capital spending',
            'inputs': {
                'after_tax_earnings': str(earnings) if earnings is not None else None,
                'depreciation': str(depreciation) if depreciation is not None else None,
                'capital_spending': str(capex) if capex is not None else None,
            },
            'reason': ocf_gap,
        },
        'value_range': cases,
        'shares': str(shares) if shares is not None else None,
        'share_gap': s_gap,
        'market_price': {
            'value_usd': str(price) if price is not None else None,
            'date': price_date,
            'source': price_item.get('reader_source') if isinstance(price_item, dict) else None,
            'reason': price_gap,
        },
        'low_case_comparison': {
            'margin_of_safety_percent': str(margin) if margin is not None else None,
            'formula': '(Low-case value per share - dated market price) / dated market price x 100',
            'view': view,
        },
        'liquidity': liquidity,
        'conviction': {'level': conviction, 'reason': conviction_reason},
        'not_known': missing,
    }


def main():
    parser = argparse.ArgumentParser(description='Calculate Lab 07 worksheet values from sourced inputs')
    parser.add_argument('--inputs', type=Path, required=True, help='JSON evidence inputs; no estimates')
    parser.add_argument('--rules', type=Path, required=True, help='lab07_worksheet_rules.md')
    parser.add_argument('--output', type=Path, required=True, help='Output calculations JSON path')
    args = parser.parse_args()
    inputs = json.loads(args.inputs.read_text(encoding='utf-8'))
    inputs['_input_directory'] = str(args.inputs.resolve().parent)
    result = calculate(inputs, read_rules(args.rules))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Calculations: {args.output.resolve()}')


if __name__ == '__main__':
    main()
