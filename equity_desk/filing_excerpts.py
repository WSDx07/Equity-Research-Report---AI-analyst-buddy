"""Build bounded, line-numbered filing excerpts for model context."""
from __future__ import annotations

import re

TERMS = re.compile(r"\b(business|products?|services?|customers?|competition|competitors?|strategy|growth|revenue|earnings|results|outlook|guidance|risks?|uncertaint|cash flow|management.s discussion|item\s+[178])\b", re.I)


def numbered_excerpt(text: str, limit: int, already_numbered: bool = False) -> str:
    """Keep original line numbers and disclose omissions; never exceed limit."""
    lines = text.splitlines()
    numbered = lines if already_numbered else [f"{i}: {line}" for i, line in enumerate(lines, 1)]
    joined = "\n".join(numbered)
    if len(joined) <= limit:
        return joined
    notice = "[Excerpt selected from filing; omitted lines are not evidence of absence.]\n"
    budget = max(0, limit - len(notice))
    # Favor section headings and relevant lines, with nearby context. Preserve
    # document order so the agent can cite original saved line numbers.
    relevant = {i for i, line in enumerate(numbered) if TERMS.search(line)}
    neighbors = {j for i in relevant for j in (i - 1, i + 1) if 0 <= j < len(numbered)}
    order = list(sorted(relevant)) + list(sorted(neighbors - relevant)) + list(range(len(numbered)))
    chosen, size = set(), 0
    for i in order:
        if i in chosen:
            continue
        line = numbered[i]
        if len(line) + 1 <= budget - size:
            chosen.add(i)
            size += len(line) + 1
    return notice + "\n".join(numbered[i] for i in sorted(chosen))


def cited_excerpts(report: str, filings: dict[str, str], limit_each: int = 20000) -> dict[str, str]:
    """Provide cited lines and adjacent lines first; flag incomplete excerpts."""
    result = {}
    for form, text in filings.items():
        lines = text.splitlines()
        cited = {int(m.group(1)) - 1 for m in re.finditer(re.escape(form) + r"\s*(?:,\s*[^\n]*?,\s*)?line\s+(\d+)", report, re.I)}
        indexes = {j for i in cited for j in range(max(0, i - 20), min(len(lines), i + 6))}
        excerpt = "\n".join(f"{i + 1}: {lines[i]}" for i in sorted(indexes))
        if not excerpt:
            excerpt = numbered_excerpt(text, limit_each)
        elif len(excerpt) > limit_each:
            excerpt = numbered_excerpt(excerpt, limit_each, already_numbered=True)
        result[form] = "[Only excerpts are shown; other filing lines were omitted.]\n" + excerpt
    return result
