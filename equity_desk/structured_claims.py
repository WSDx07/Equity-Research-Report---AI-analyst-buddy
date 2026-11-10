"""Validate explicit financial-claim evidence and arithmetic without eval()."""
from __future__ import annotations

import ast
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


def parse_claim(line: str) -> dict | None:
    match = re.search(r"<!--\s*FINANCIAL_CLAIM\s+(\{.*\})\s*-->\s*$", line)
    if not match:
        return None
    try:
        claim = json.loads(match.group(1), parse_float=Decimal)
        return claim if isinstance(claim, dict) else {"invalid": True}
    except (ValueError, TypeError):
        return {"invalid": True}


def dec(value) -> Decimal:
    number = Decimal(str(value).replace(",", ""))
    if not number.is_finite():
        raise ValueError("Non-finite number")
    return number


def formula_value(expression: str, values: dict[str, Decimal]) -> Decimal:
    if len(expression) > 200:
        raise ValueError("Formula is too long")
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 80:
        raise ValueError("Formula is too complex")
    def calculate(node):
        if isinstance(node, ast.Expression):
            return calculate(node.body)
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 1000000:
            return Decimal(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = calculate(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = calculate(node.left), calculate(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if right == 0: raise ValueError("Division by zero")
            return left / right
        raise ValueError("Formula uses an unsupported operation")
    with localcontext() as context:
        context.prec = 40
        return calculate(tree)


def check_claim(claim: dict, facts: dict, filings: dict[str, str]) -> dict:
    """Return a candidate only after checking every source operand and formula."""
    result = {"status": "unsupported", "reason": "Incomplete or invalid structured financial claim."}
    try:
        reported = dec(claim["reported"])
        inputs = claim["inputs"]
        if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 8:
            return result
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,15}", claim["id"]):
            return result
        if not isinstance(claim.get("label"), str) or not claim["label"].strip() or not claim.get("unit") or not claim.get("definition"):
            return result
        values, receipts = {}, []
        for variable, item in inputs.items():
            if not re.fullmatch(r"[a-z]", variable) or not isinstance(item, dict):
                raise ValueError("Invalid operand")
            value = dec(item["value"])
            form, line_no, column = item["document"], int(item["line"]), int(item["column"])
            if form not in ("10-K", "10-Q", "8-K", "EX-99.1") or line_no < 1 or column < 1:
                raise ValueError("Invalid source reference")
            lines = filings[form].splitlines()
            source_line = lines[line_no - 1]
            tokens = re.findall(r"(?<![\w.])[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", source_line)
            if column > len(tokens) or dec(tokens[column - 1]) != value:
                raise ValueError(f"{variable} differs from the cited filing column")
            end = date.fromisoformat(item["period_end"])
            header = re.sub(r"\s+", " ", " ".join(lines[max(0, line_no - 85):line_no - 1]).replace("|", " "))
            dates = re.findall(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", header, re.I)
            if len(dates) < len(tokens):
                raise ValueError(f"{variable} reporting date is absent from the surrounding filing header")
            # A statement row's date columns follow the immediately preceding
            # statement header; do not accept a different quarter/year merely
            # because that date appears elsewhere in the header.
            column_dates = dates[-len(tokens):]
            try:
                column_end = datetime.strptime(column_dates[column - 1].replace(",", ""), "%B %d %Y").date()
            except ValueError:
                raise ValueError(f"{variable} reporting date could not be parsed") from None
            if column_end != end:
                raise ValueError(f"{variable} reporting date does not match the cited filing column")
            unit = item["unit"]
            if unit not in ("USD million", "USD/share"):
                raise ValueError("Unsupported unit")
            if unit == "USD million" and not re.search(r"\b(?:dollars|amounts)\s+in\s+millions\b", header, re.I):
                raise ValueError("The filing header does not establish amounts in millions")
            if unit == "USD/share" and not re.search(r"\bper\s+share\b", header, re.I):
                raise ValueError("The filing header does not establish per-share units")
            duration = item.get("duration_weeks")
            if not item.get("concept") and duration is None:
                raise ValueError("An uncrosschecked statement amount needs a source duration")
            if duration is not None:
                period_headers = [re.findall(r"\b(\d+)\s+weeks?\s+ended\b", h, re.I) for h in lines[max(0, line_no - 85):line_no - 1]]
                groups = next((g for g in reversed(period_headers) if g), [])
                if not groups or len(tokens) % len(groups):
                    raise ValueError("Statement duration columns could not be established")
                width = len(tokens) // len(groups)
                if int(groups[(column - 1) // width]) != int(duration):
                    raise ValueError("Statement duration does not match the cited filing column")
            if item.get("concept"):
                concept = facts["concepts"][item["concept"]]
                if not item.get("tag") or item["tag"] != concept.get("tag"):
                    raise ValueError("Fact tag does not match")
                record = concept[item["fact_period"]]
                if not record or record.get("end") != item["period_end"]:
                    raise ValueError("Fact period does not match")
                if unit == "USD million" and concept.get("unit") == "USD":
                    converted = value * 1000000
                elif unit == "USD/share" and concept.get("unit") == "USD/shares":
                    converted = value
                else:
                    raise ValueError("Fact unit does not match")
                if converted != dec(record["val"]):
                    raise ValueError("Value differs from the saved XBRL fact")
            values[variable] = value
            receipts.append(f"{variable}={value} {unit} ({item['period_end']}; {form} line {line_no}, column {column})")
        with localcontext() as context:
            context.prec = 40
            actual = formula_value(claim["formula"], values)
            places = max(0, -reported.as_tuple().exponent)
            rounded = actual.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        status = "candidate" if rounded == reported else "wrong"
        reason = f"{claim['definition']}; inputs: {'; '.join(receipts)}; formula {claim['formula']} = {actual:.6f}, rounded to {rounded} {claim['unit']}."
        result.update(status=status, reason=reason, calculated=str(rounded), actual=str(actual), receipts=receipts)
    except (ValueError, TypeError, KeyError, IndexError, InvalidOperation, SyntaxError, OverflowError) as exc:
        result["reason"] = str(exc) or "Invalid financial claim."
    return result
