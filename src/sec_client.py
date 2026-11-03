from __future__ import annotations

import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.config import SEC_USER_AGENT, SEC_BASE, SEC_DATA_BASE


class SECClientError(RuntimeError):
    pass


_COMPANY_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "ltd",
    "limited",
    "plc",
    "llc",
    "lp",
}


def _normalize_company_name(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    while words and words[-1] in _COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


class SECClient:
    """Small, read-only SEC client with conservative request pacing."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
        })
        self._ticker_map: dict[str, dict[str, Any]] | None = None
        self._last_request = 0.0

    def _ensure_ticker_map(self) -> dict[str, dict[str, Any]]:
        if self._ticker_map is None:
            raw = self._get("https://www.sec.gov/files/company_tickers.json")
            self._ticker_map = {
                str(row["ticker"]).upper(): row for row in raw.values()
            }
        return self._ticker_map

    def _get(self, url: str, json_response: bool = True):
        elapsed = time.monotonic() - self._last_request
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        response = self.session.get(url, timeout=30)
        self._last_request = time.monotonic()
        if response.status_code == 429:
            raise SECClientError("SEC rate limit reached. Wait and retry.")
        response.raise_for_status()
        return response.json() if json_response else response.text

    def company_by_ticker(self, ticker: str) -> dict[str, Any]:
        key = ticker.strip().upper()
        ticker_map = self._ensure_ticker_map()
        if key not in ticker_map:
            raise SECClientError(f"Ticker '{ticker}' was not found in SEC ticker data.")
        row = ticker_map[key]
        return {
            "ticker": key,
            "cik": int(row["cik_str"]),
            "company_name": row["title"],
        }

    def ticker_for_company(self, name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise SECClientError("A company name or ticker is required.")
        ticker_shape = re.fullmatch(r"[A-Za-z]{1,5}(?:\.[A-Za-z])?", cleaned)
        if ticker_shape and (cleaned.isupper() or len(cleaned) <= 4):
            try:
                return self.company_by_ticker(cleaned)["ticker"]
            except SECClientError:
                if len(cleaned) <= 4 or "." in cleaned:
                    raise
        target = _normalize_company_name(cleaned)
        exact: list[str] = []
        prefix: list[str] = []
        for ticker, row in self._ensure_ticker_map().items():
            title = _normalize_company_name(str(row.get("title") or ""))
            if not title or not target:
                continue
            if title == target:
                exact.append(ticker)
            elif title.startswith(f"{target} ") or target.startswith(f"{title} "):
                prefix.append(ticker)
        choices = exact or prefix
        if not choices:
            raise SECClientError(f"No SEC company matched '{cleaned}'.")
        return min(
            choices,
            key=lambda ticker: (
                len(_normalize_company_name(str(self._ticker_map[ticker].get("title") or ""))),
                ticker,
            ),
        )

    def latest_10k_year(self, ticker: str) -> int:
        company = self.company_by_ticker(ticker)
        recent = self.submissions(company["cik"]).get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("reportDate", [])
        years = [
            int(str(dates[index])[:4])
            for index, form in enumerate(forms)
            if form in ("10-K", "10-K/A")
            and index < len(dates)
            and str(dates[index])[:4].isdigit()
        ]
        if not years:
            raise SECClientError(f"No recent 10-K found for {ticker.upper()}.")
        return max(years)

    def submissions(self, cik: int) -> dict[str, Any]:
        return self._get(f"{SEC_DATA_BASE}/submissions/CIK{cik:010d}.json")

    def find_10k(self, ticker: str, fiscal_year: int) -> dict[str, Any]:
        company = self.company_by_ticker(ticker)
        recent = self.submissions(company["cik"]).get("filings", {}).get("recent", {})
        matches = []
        fields = ("form", "reportDate", "filingDate", "accessionNumber", "primaryDocument")
        rows = {field: recent.get(field, []) for field in fields}
        for i, form in enumerate(rows["form"]):
            if form not in ("10-K", "10-K/A"):
                continue
            report_date = rows["reportDate"][i] if i < len(rows["reportDate"]) else ""
            if not report_date.startswith(str(fiscal_year)):
                continue
            accession = rows["accessionNumber"][i]
            primary = rows["primaryDocument"][i]
            filing_date = rows["filingDate"][i]
            accession_path = accession.replace("-", "")
            matches.append({
                **company,
                "form": form,
                "report_date": report_date,
                "filing_date": filing_date,
                "accession_number": accession,
                "primary_document": primary,
                "filing_url": (
                    f"{SEC_BASE}/Archives/edgar/data/{company['cik']}/"
                    f"{accession_path}/{primary}"
                ),
                "accession_index_url": (
                    f"{SEC_BASE}/Archives/edgar/data/{company['cik']}/{accession_path}/"
                ),
            })
        if not matches:
            raise SECClientError(
                f"No recent 10-K found for {ticker.upper()} with report period ending "
                f"in calendar year {fiscal_year}. Try a nearby fiscal year."
            )
        return sorted(matches, key=lambda x: x["filing_date"], reverse=True)[0]

    def company_facts(self, cik: int) -> dict[str, Any]:
        return self._get(
            f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json"
        )

    def filing_text(self, url: str) -> str:
        from src.document_store import read_saved_filing, save_filing

        html = read_saved_filing(url)
        if html is None:
            html = self._get(url, json_response=False)
            save_filing(url, html)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return re.sub(r"\\s+", " ", soup.get_text(" ", strip=True))
