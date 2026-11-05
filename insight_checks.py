"""Validation helpers for analyst Insight lines."""
from __future__ import annotations
import re
from desk_verifier import quoted_line_matches

MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"

def release_first_paragraph(text: str) -> dict:
    """Locate a datelined announcement; saved text loses HTML boundaries."""
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(MONTH + r"\s+\d{1,2},?\s+\d{4}", line, re.I) and re.search(r"\b(?:announc\w*|report\w*)\b", line, re.I):
            return {"status": "candidate", "document": "EX-99.1", "line": number, "text": line, "limitation": "Saved text has no original HTML paragraph boundaries; confirm this is the release's first paragraph."}
    return {"status": "unavailable", "document": "EX-99.1", "line": None, "text": "", "limitation": "Could not identify the release's first paragraph from saved text."}

def insight_errors(insight: str, filings: dict[str, str], first_paragraph: dict) -> list[str]:
    if not isinstance(insight, str) or not insight.strip():
        return ["No Insight line was supplied."]
    errors = []
    if not insight.startswith("Insight:") or "\n" in insight or "\r" in insight:
        errors.append('Insight must be one line beginning exactly with "Insight:".')
    if quoted_line_matches(insight, filings) is not True:
        errors.append("Insight needs a filing, line number, and exact quote from that line.")
    if first_paragraph.get("status") != "candidate":
        errors.append("The first release paragraph could not be identified; the Insight cannot pass the headline check.")
    elif (claim := insight.split(" — ", 1)[0].removeprefix("Insight:").strip()) and claim.casefold() in first_paragraph["text"].casefold():
        errors.append("Insight repeats the release's first paragraph.")
    return errors
