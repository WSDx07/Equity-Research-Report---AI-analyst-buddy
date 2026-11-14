"""Demonstrate the pre-specified factor comparison on synthetic records only."""
from __future__ import annotations

from decimal import Decimal
from statistics import mean


SIZE_LIMIT = Decimal('2000000000')
WEAKNESS_LIMIT = Decimal('15')
INSIDER_LIMIT = Decimal('5')

# Synthetic observations only. Returns are decimal fractions, not percentages.
DEMO = (
    {'id': 'SYN-A', 'market_cap_usd': '1500000000', 'decline_pct': '20', 'insider_pct': '6', 'stock_return': '0.12', 'benchmark_return': '0.04'},
    {'id': 'SYN-B', 'market_cap_usd': '2500000000', 'decline_pct': '4', 'insider_pct': '1', 'stock_return': '0.03', 'benchmark_return': '0.05'},
    {'id': 'SYN-C', 'market_cap_usd': '1800000000', 'decline_pct': '3', 'insider_pct': '2', 'stock_return': '0.06', 'benchmark_return': '0.04'},
    {'id': 'SYN-D', 'market_cap_usd': None, 'decline_pct': '18', 'insider_pct': '6', 'stock_return': '0.09', 'benchmark_return': '0.04'},
)


def compare(records):
    """Calculate exactly one group contrast, with missing cases counted."""
    groups = {0: [], 25: [], 50: [], 75: []}
    seen = set()
    excluded = 0
    for row in records:
        ident = row['id']
        if ident in seen:
            raise ValueError('Duplicate synthetic observation')
        seen.add(ident)
        names = ('market_cap_usd', 'decline_pct', 'insider_pct', 'stock_return', 'benchmark_return')
        if any(row.get(name) is None for name in names):
            excluded += 1
            continue
        cap, decline, insider, stock, benchmark = (Decimal(str(row[name])) for name in names)
        if not all(x.is_finite() for x in (cap, decline, insider, stock, benchmark)) or cap < 0 or not 0 <= insider <= 100 or decline > 100:
            raise ValueError('Invalid synthetic input')
        score = 25 * (int(cap <= SIZE_LIMIT) + int(decline >= WEAKNESS_LIMIT) + int(insider >= INSIDER_LIMIT))
        groups[score].append(stock - benchmark)
    means = {score: mean(values) if values else None for score, values in groups.items()}
    difference = means[75] - means[0] if means[75] is not None and means[0] is not None else None
    return {'counts': {score: len(values) for score, values in groups.items()},
            'excluded': excluded, 'means': means, 'difference': difference,
            'comparisons': int(difference is not None)}


def main():
    result = compare(DEMO)
    print('SYNTHETIC DEMONSTRATION ONLY - no historical data or investment result')
    print('Eligible groups by score:', ', '.join(f'{k}: {v}' for k, v in result['counts'].items()))
    print('Excluded for missing inputs:', result['excluded'])
    if result['difference'] is None:
        print('Primary comparison: insufficient data')
    else:
        print('Mean benchmark-adjusted return, 75 points:', result['means'][75])
        print('Mean benchmark-adjusted return, 0 points:', result['means'][0])
        print('Primary difference, decimal return:', result['difference'])
    print('Comparisons performed:', result['comparisons'])


if __name__ == '__main__':
    main()
