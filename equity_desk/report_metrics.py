"""Render financial calculations from saved XBRL facts, without model arithmetic."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json


def metrics(facts, peers, price=None):
    rows = {}

    def rec(dataset, name, period="current"):
        item = dataset["concepts"][name]
        record = item[period]
        if not record or record.get("val") is None or not item.get("tag"):
            raise KeyError(name)
        return Decimal(str(record["val"])), item, record

    def source(item, record):
        return f"{item['tag']}, {record.get('start', 'as of')} to {record['end']}, {record['accn']} filed {record['filed']}"

    def add(key, label, operands, formula, unit, precision=2, extra="", same_period=False):
        try:
            entries = [rec(data, name, period) for data, name, period in operands]
            if same_period and len({(record.get('start'), record.get('end')) for _, _, record in entries}) != 1:
                return
            values = [e[0] for e in entries]
            result = formula(*values).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
            detail = "; ".join(f"{name} {period}: {v} {item['unit']} ({source(item, record)})" for (_, name, period), (v, item, record) in zip(operands, entries))
            rows[key] = (label, str(result), unit, detail + extra)
        except (KeyError, TypeError, ZeroDivisionError, InvalidOperation):
            pass

    def op(name, period='current'):
        return (facts, name, period)

    for name in ('total_revenue', 'operating_income', 'net_income', 'diluted_eps', 'stockholders_equity', 'long_term_debt_noncurrent', 'long_term_debt_current', 'cash_from_operations', 'additions_to_property_and_equipment'):
        for period in ('current', 'prior'):
            add(name+'_'+period, name.replace('_', ' ')+' '+period, [op(name, period)], lambda a: a, 'USD/share' if name == 'diluted_eps' else 'USD', 2 if name == 'diluted_eps' else 0)
    add('revenue_growth_percent', 'Revenue growth', [op('total_revenue'), op('total_revenue', 'prior')], lambda a,b:(a-b)/b*100, '%', extra='; formula: (current revenue - prior revenue) / prior revenue × 100')
    add('operating_margin_percent', 'Operating margin', [op('operating_income'),op('total_revenue')], lambda a,b:a/b*100, '%', extra='; formula: operating income / total revenue × 100', same_period=True)
    add('return_on_average_equity_percent', 'Return on average equity', [op('net_income'),op('stockholders_equity'),op('stockholders_equity','prior')], lambda a,b,c:a/((b+c)/2)*100, '%', extra='; formula: net income / ((current equity + prior equity) / 2) × 100')
    if facts.get('concepts',{}).get('long_term_debt_noncurrent',{}).get('tag') == 'us-gaap:LongTermDebtNoncurrent':
        add('debt_to_equity', 'Debt to equity', [op('long_term_debt_noncurrent'),op('long_term_debt_current'),op('stockholders_equity')], lambda a,b,c:(a+b)/c, 'ratio', 4, '; formula: (noncurrent debt + current debt) / equity')
    add('free_cash_flow_usd', 'Free cash flow', [op('cash_from_operations'),op('additions_to_property_and_equipment')], lambda a,b:a-b, 'USD', 0, '; formula: operating cash flow - property and equipment additions', same_period=True)
    for ticker, peer in peers.items():
        add('peer_'+ticker, ticker+' operating margin', [(peer,'operating_income','current'),(peer,'total_revenue','current')], lambda a,b:a/b*100, '%', extra='; formula: operating income / total revenue × 100', same_period=True)
    if price is not None:
        try:
            price = Decimal(str(price))
            eps, item, record = rec(facts, 'diluted_eps')
            if price > 0 and price.is_finite() and eps:
                result = (price / eps).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                rows['price_to_earnings'] = ('Price to earnings', str(result), 'ratio', f'price: {price} USD/share (user input; date and source unverified); diluted EPS: {eps} USD/share ({source(item, record)}); formula: price / diluted EPS')
        except (KeyError, InvalidOperation, ZeroDivisionError):
            pass
    return rows


def render_metric(key, row, price=None):
    label, value, unit, detail = row
    meta = {'key': key}
    if key == 'price_to_earnings':
        meta['price'] = str(price)
    return f"| {label} | {value} {unit} | {detail} | <!-- DESK_METRIC {json.dumps(meta, separators=(',', ':'))} -->"
