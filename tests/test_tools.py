from unittest.mock import patch

import pytest

from src.llm_cache import upsert_processed_document
from src.tools.financial_documents import process_financial_document
from src.tools.sql_execute import execute_sql
from src.tools.sql_query import convert_query_to_sql, validate_read_sql


def test_company_name_resolves_to_a_ticker_and_latest_filing_year():
    from src.sec_client import SECClient

    client = SECClient()
    client._ticker_map = {
        "AAPL": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."},
        "IBM": {"ticker": "IBM", "cik_str": 51143, "title": "INTERNATIONAL BUSINESS MACHINES CORP"},
    }
    assert client.ticker_for_company("Apple") == "AAPL"
    assert client.ticker_for_company("IBM") == "IBM"
    with patch.object(
        client,
        "submissions",
        return_value={"filings": {"recent": {"form": ["10-K", "10-K"], "reportDate": ["2024-09-28", "2025-09-27"]}}},
    ):
        assert client.latest_10k_year("AAPL") == 2025


def test_process_financial_document_downloads_and_processes(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    filing = {
        "company_name": "Microsoft",
        "ticker": "MSFT",
        "form": "10-K",
        "report_date": "2025-06-30",
        "filing_date": "2025-07-30",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
    }
    with (
        patch("src.tools.financial_documents.SECClient") as client_cls,
        patch("src.tools.financial_documents.fetch_filing_html", return_value="<html>filing</html>") as fetch,
        patch(
            "src.tools.financial_documents.get_financial_metrics",
            return_value={"metrics": {"revenue": {"value": 10}}, "calculations": {}, "notes": []},
        ),
        patch(
            "src.tools.financial_documents.search_report_content",
            side_effect=[{"passages": ["competition"]}, {"passages": ["growth"]}],
        ),
        patch("src.tools.financial_documents.filing_path") as path,
    ):
        client_cls.return_value.find_10k.return_value = filing
        path.return_value.is_file.return_value = True
        path.return_value.__str__.return_value = "/tmp/msft.htm"
        result = process_financial_document.invoke({"ticker": "msft", "fiscal_year": 2025})
    fetch.assert_called_once_with(filing["filing_url"])
    assert "download" in process_financial_document.description.lower()
    assert result["ticker"] == "MSFT"
    assert result["local_file"] == "/tmp/msft.htm"
    assert result["metrics"]["revenue"]["value"] == 10
    assert result["risk_factors"]["passages"] == ["competition"]
    assert result["management_outlook"]["passages"] == ["growth"]
    import sqlite3

    with sqlite3.connect(tmp_path / "cache.db") as connection:
        stored = connection.execute(
            "SELECT metric_name, value, source FROM financial_facts ORDER BY metric_name"
        ).fetchall()
        catalog = connection.execute(
            "SELECT company_name, ticker, fiscal_year FROM processed_documents"
        ).fetchall()
        linked = connection.execute("SELECT document_id FROM financial_facts").fetchone()
    assert stored == [("revenue", 10.0, "extraction")]
    assert catalog == [("Microsoft", "MSFT", 2025)]
    assert linked[0] == 1


def test_convert_query_to_sql_returns_one_select(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")

    class Reply:
        content = "```sql\nSELECT ticker, fiscal_year FROM processed_documents\n```"

    with patch("src.tools.sql_query.ChatAnthropic") as model:
        model.return_value.invoke.return_value = Reply()
        sql = convert_query_to_sql.invoke({"question": "Which filings are stored?"})
    prompt = model.return_value.invoke.call_args.args[0]
    assert sql == "SELECT ticker, fiscal_year FROM processed_documents"
    assert "does not run" in convert_query_to_sql.description.lower()
    assert "processed_documents -> One saved SEC 10-K filing" in prompt
    assert "processed_documents.ticker -> Uppercase stock ticker" in prompt
    assert "financial_facts.value -> Numeric amount" in prompt
    assert "llm_calls.prompt -> Exact prompt text" in prompt
    assert "schema_catalog.name -> Table name" in prompt


def test_convert_query_to_sql_rejects_a_write():
    class Reply:
        content = "DELETE FROM processed_documents"

    with patch("src.tools.sql_query.ChatAnthropic") as model:
        model.return_value.invoke.return_value = Reply()
        with pytest.raises(ValueError):
            convert_query_to_sql.invoke({"question": "Remove every filing"})


def test_execute_sql_reads_processed_documents(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        local_file="",
        analysis={"company_name": "Microsoft"},
    )
    result = execute_sql.invoke(
        {"sql": "SELECT ticker, fiscal_year FROM processed_documents ORDER BY ticker"}
    )
    assert "read-only" in execute_sql.description.lower()
    assert result["columns"] == ["ticker", "fiscal_year"]
    assert result["rows"] == [["MSFT", 2025]]


def test_execute_sql_rejects_a_change():
    with pytest.raises(ValueError):
        validate_read_sql("DROP TABLE processed_documents")
    with pytest.raises(ValueError):
        execute_sql.invoke({"sql": "SELECT ticker FROM processed_documents; DROP TABLE processed_documents"})
