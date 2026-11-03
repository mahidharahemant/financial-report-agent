from __future__ import annotations

import re
from typing import Any

from src.sec_client import SECClient

SECTION_PATTERNS = {
    "Business": r"item\\s*1[.\\s]+business",
    "Risk Factors": r"item\\s*1a[.\\s]+risk factors",
    "Management Discussion and Analysis": r"item\\s*7[.\\s]+management.{0,80}discussion",
    "Market Risk": r"item\\s*7a[.\\s]+quantitative",
}


def extract_sections(text: str) -> dict[str, str]:
    lower = text.lower()
    hits = []
    for section, pattern in SECTION_PATTERNS.items():
        match = re.search(pattern, lower)
        if match:
            hits.append((match.start(), section))
    hits.sort()
    sections = {}
    for index, (start, section) in enumerate(hits):
        end = hits[index + 1][0] if index + 1 < len(hits) else min(len(text), start + 40000)
        sections[section] = text[start:end][:40000]
    return sections


def search_report_content(
    ticker: str, fiscal_year: int, query: str, max_passages: int = 5
) -> dict[str, Any]:
    client = SECClient()
    filing = client.find_10k(ticker, fiscal_year)
    text = client.filing_text(filing["filing_url"])
    sections = extract_sections(text)
    terms = [word.lower() for word in re.findall(r"[A-Za-z][A-Za-z-]{2,}", query)]
    query_lower = query.lower()
    if any(word in query_lower for word in ("risk", "cyber", "regulat", "competition")):
        preferred = ["Risk Factors", "Market Risk"]
    elif any(word in query_lower for word in ("outlook", "expect", "strategy", "investment", "growth")):
        preferred = ["Management Discussion and Analysis", "Business", "Risk Factors"]
    else:
        preferred = list(sections)

    passages = []
    for section in preferred + [s for s in sections if s not in preferred]:
        body = sections.get(section, "")
        sentences = re.split(r"(?<=[.!?])\\s+", body)
        ranked = []
        for sentence in sentences:
            score = sum(1 for term in terms if term in sentence.lower())
            if score and len(sentence.strip()) >= 60:
                ranked.append((score, sentence.strip()))
        for score, sentence in sorted(ranked, key=lambda item: item[0], reverse=True):
            passages.append({
                "section": section,
                "score": score,
                "text": sentence[:1600],
                "source_url": filing["filing_url"],
            })
            if len(passages) >= max_passages:
                break
        if len(passages) >= max_passages:
            break
    return {
        "company_name": filing["company_name"],
        "ticker": filing["ticker"],
        "fiscal_year": fiscal_year,
        "filing_url": filing["filing_url"],
        "query": query,
        "passages": passages,
        "available_sections": list(sections),
        "warning": "Keyword-based best-effort search; verify excerpts against the original filing.",
    }
