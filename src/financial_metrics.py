from __future__ import annotations

from datetime import date
from typing import Any

from src.sec_client import SECClient

TAG_CANDIDATES = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
}


def _rows_for_tag(facts: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    if tag not in us_gaap:
        return []
    units = us_gaap[tag].get("units", {})
    return units.get("USD") or (next(iter(units.values())) if units else [])


def _pick_annual_fact(
    facts: dict[str, Any], candidates: list[str], fiscal_year: int, instant: bool = False
) -> dict[str, Any] | None:
    matches = []
    for tag in candidates:
        for row in _rows_for_tag(facts, tag):
            end = row.get("end", "")
            if not end.startswith(str(fiscal_year)):
                continue
            if row.get("form") not in ("10-K", "10-K/A"):
                continue
            if instant:
                if row.get("start"):
                    continue
            else:
                start = row.get("start")
                if not start:
                    continue
                try:
                    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
                except ValueError:
                    continue
                if not 330 <= days <= 380:
                    continue
            matches.append(row)
    if not matches:
        return None
    matches.sort(key=lambda r: (r.get("filed", ""), r.get("end", "")))
    return matches[-1]


def get_financial_metrics(ticker: str, fiscal_year: int) -> dict[str, Any]:
    client = SECClient()
    filing = client.find_10k(ticker, fiscal_year)
    facts = client.company_facts(filing["cik"])
    output: dict[str, Any] = {
        "company_name": filing["company_name"],
        "ticker": filing["ticker"],
        "fiscal_year": fiscal_year,
        "report_period_end": filing["report_date"],
        "filing_url": filing["filing_url"],
        "metrics": {},
        "calculations": {},
        "notes": [
            "Standard XBRL tags do not cover every issuer; missing facts remain null.",
            "Capital expenditures are treated as a cash outflow and subtracted by absolute value.",
        ],
    }

    selected = {}
    instant_metrics = {"total_assets", "total_liabilities"}
    for name, tags in TAG_CANDIDATES.items():
        row = _pick_annual_fact(facts, tags, fiscal_year, instant=name in instant_metrics)
        selected[name] = row
        matched_tag = next(
            (tag for tag in tags if tag in facts.get("facts", {}).get("us-gaap", {})),
            None,
        )
        output["metrics"][name] = {
            "value": row.get("val") if row else None,
            "unit": "USD" if row else None,
            "period_start": row.get("start") if row else None,
            "period_end": row.get("end") if row else None,
            "xbrl_tag": matched_tag,
            "source_url": filing["filing_url"],
        }

    cashflow = selected.get("operating_cash_flow")
    capex = selected.get("capital_expenditures")
    output["calculations"]["free_cash_flow"] = {
        "value": cashflow["val"] - abs(capex["val"]) if cashflow and capex else None,
        "unit": "USD",
        "formula": "operating cash flow - abs(capital expenditures)",
    }

    revenue = selected.get("revenue")
    previous = _pick_annual_fact(facts, TAG_CANDIDATES["revenue"], fiscal_year - 1)
    if revenue and previous and previous["val"] != 0:
        output["calculations"]["revenue_growth_pct"] = round(
            (revenue["val"] - previous["val"]) / abs(previous["val"]) * 100, 2
        )
        output["calculations"]["revenue_previous_year"] = {
            "value": previous["val"], "unit": "USD", "period_end": previous.get("end")
        }
    else:
        output["calculations"]["revenue_growth_pct"] = None
        output["calculations"]["revenue_previous_year"] = None
    return output
