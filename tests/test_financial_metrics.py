from src.financial_metrics import _pick_annual_fact


def test_pick_annual_duration_fact():
    facts = {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [{
            "val": 100, "start": "2024-07-01", "end": "2025-06-30",
            "form": "10-K", "fp": "FY", "filed": "2025-08-01"
        }]}}
    }}}
    row = _pick_annual_fact(
        facts, ["RevenueFromContractWithCustomerExcludingAssessedTax"], 2025
    )
    assert row is not None
    assert row["val"] == 100


def test_missing_fact_returns_none():
    assert _pick_annual_fact({"facts": {"us-gaap": {}}}, ["Assets"], 2025, instant=True) is None
