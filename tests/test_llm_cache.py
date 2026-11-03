import json
from unittest.mock import patch

from src.agents.agent import analyze_company, answer_question, build_analysis_prompt
from src.document_store import read_saved_filing, save_filing
from src.llm_cache import (
    get_cached_response,
    list_processed_documents,
    store_response,
    upsert_processed_document,
)


def test_sqlite_returns_stored_prompt_response(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    assert get_cached_response("Analyze MSFT") is None
    store_response("Analyze MSFT", '{"ticker": "MSFT"}')
    assert get_cached_response("Analyze MSFT") == '{"ticker": "MSFT"}'


def test_same_prompt_skips_the_model(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    prompt = build_analysis_prompt("msft", 2025)
    store_response(prompt, '{"company_name": "Microsoft", "financial_metrics": []}')
    with patch("src.agents.agent.create_financial_agent") as create_agent:
        result = analyze_company("msft", 2025)
    create_agent.assert_not_called()
    assert result["company_name"] == "Microsoft"
    assert result["ticker"] == "MSFT"
    assert result["fiscal_year"] == 2025


def test_new_prompt_stores_the_model_response(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    prompt = build_analysis_prompt("AAPL", 2024)
    with patch("src.agents.agent._invoke_agent", return_value='{"company_name": "Apple"}') as invoke:
        first = analyze_company("AAPL", 2024)
        second = analyze_company("AAPL", 2024)
    invoke.assert_called_once_with(prompt)
    assert first["company_name"] == "Apple"
    assert second["company_name"] == "Apple"
    assert get_cached_response(prompt) == '{"company_name": "Apple"}'


def test_downloaded_filing_is_reused_from_disk(monkeypatch, tmp_path):
    monkeypatch.setattr("src.document_store.FILINGS_DIR", tmp_path / "filings")
    url = "https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm"
    save_filing(url, "<html><p>Revenue 281,724</p></html>")
    assert "281,724" in read_saved_filing(url)

    from src.filing_view import fetch_filing_html

    with patch("src.filing_view.requests.get") as get:
        html = fetch_filing_html(url)
    get.assert_not_called()
    assert "281,724" in html


MSFT_URL = "https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm"


def _use_temp_stores(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr("src.llm_cache.OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr("src.document_store.FILINGS_DIR", tmp_path / "filings")


def test_analysis_records_one_catalog_row(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    payload = json.dumps(
        {
            "company_name": "Microsoft",
            "ticker": "MSFT",
            "fiscal_year": 2025,
            "filing_url": MSFT_URL,
            "financial_metrics": [],
        }
    )
    store_response(build_analysis_prompt("MSFT", 2025), payload)
    analyze_company("MSFT", 2025)
    analyze_company("MSFT", 2025)
    documents = list_processed_documents()
    assert len(documents) == 1
    assert documents[0]["ticker"] == "MSFT"
    assert documents[0]["fiscal_year"] == 2025
    assert documents[0]["filing_url"] == MSFT_URL
    assert documents[0]["id"]


def test_repeat_analysis_updates_processed_time(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    analysis = {"company_name": "Microsoft", "financial_metrics": []}
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url=MSFT_URL,
        local_file="",
        analysis=analysis,
        processed_at="2024-01-01T00:00:00Z",
    )
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url=MSFT_URL,
        local_file="",
        analysis=analysis,
        processed_at="2025-06-01T00:00:00Z",
    )
    documents = list_processed_documents()
    assert len(documents) == 1
    assert documents[0]["processed_at"] == "2025-06-01T00:00:00Z"


def test_documents_are_newest_first(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    upsert_processed_document(
        company_name="Apple",
        ticker="AAPL",
        fiscal_year=2024,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/aapl.htm",
        local_file="",
        analysis={"company_name": "Apple", "financial_metrics": []},
        processed_at="2024-01-01T00:00:00Z",
    )
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url=MSFT_URL,
        local_file="",
        analysis={"company_name": "Microsoft", "financial_metrics": []},
        processed_at="2025-01-01T00:00:00Z",
    )
    documents = list_processed_documents()
    assert [item["ticker"] for item in documents] == ["MSFT", "AAPL"]


def test_empty_catalog_lists_nothing(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    assert list_processed_documents() == []


def test_backfill_imports_known_output_analysis(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    save_filing(MSFT_URL, "<html><p>saved filing</p></html>")
    output = tmp_path / "output"
    output.mkdir()
    (output / "analysis_MSFT_2025.json").write_text(
        json.dumps(
            {
                "company_name": "Microsoft",
                "ticker": "MSFT",
                "fiscal_year": 2025,
                "filing_url": MSFT_URL,
                "financial_metrics": [],
            }
        ),
        encoding="utf-8",
    )
    documents = list_processed_documents()
    assert documents[0]["ticker"] == "MSFT"
    assert documents[0]["fiscal_year"] == 2025
    assert documents[0]["local_file"].endswith("msft-20250630.htm")


def test_backfill_imports_cached_analysis(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    store_response(
        "previous analysis",
        json.dumps(
            {
                "company_name": "Apple",
                "ticker": "AAPL",
                "fiscal_year": 2024,
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1/2/aapl.htm",
                "financial_metrics": [],
            }
        ),
    )
    documents = list_processed_documents()
    assert documents[0]["ticker"] == "AAPL"
    assert documents[0]["fiscal_year"] == 2024


def test_chat_uses_saved_analysis_without_downloading(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    save_filing(MSFT_URL, "<html><p>Revenue was 281,724</p></html>")
    document_id = upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url=MSFT_URL,
        local_file="",
        analysis={
            "company_name": "Microsoft",
            "ticker": "MSFT",
            "fiscal_year": 2025,
            "filing_url": MSFT_URL,
            "risk_factors": [{"description": "Competition"}],
        },
    )
    with (
        patch("src.agents.agent._invoke_chat", return_value="The main risk is competition.") as invoke,
        patch("src.filing_view.requests.get") as get,
    ):
        result = answer_question("What is the main risk?", document_id)
    get.assert_not_called()
    prompt = invoke.call_args.args[0]
    assert "Competition" in prompt
    assert "281,724" in prompt
    assert result["reply"] == "The main risk is competition."
    assert result["scope"] == "MSFT 2025"
    assert result["cached"] is False


def test_repeated_question_skips_the_model(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    document_id = upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url=MSFT_URL,
        local_file="",
        analysis={"company_name": "Microsoft", "financial_metrics": []},
    )
    with patch("src.agents.agent._invoke_chat", return_value="Revenue was higher.") as invoke:
        first = answer_question("What was revenue?", document_id)
        second = answer_question("What was revenue?", document_id)
    invoke.assert_called_once()
    assert second["cached"] is True
    assert second["reply"] == first["reply"]


def test_unknown_document_is_rejected(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    with patch("src.agents.agent._invoke_chat") as invoke:
        try:
            answer_question("What was revenue?", 999)
        except LookupError:
            invoke.assert_not_called()
            return
    raise AssertionError("expected LookupError")


def test_question_without_document_uses_every_analysis(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    upsert_processed_document(
        company_name="Apple",
        ticker="AAPL",
        fiscal_year=2024,
        filing_url="",
        local_file="",
        analysis={"company_name": "Apple", "financial_metrics": [{"name": "Revenue", "value": 100}]},
    )
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url="",
        local_file="",
        analysis={"company_name": "Microsoft", "financial_metrics": [{"name": "Revenue", "value": 200}]},
    )
    with patch("src.agents.agent._invoke_chat", return_value="Microsoft reported higher revenue.") as invoke:
        result = answer_question("Which company reported higher revenue?", None)
    prompt = invoke.call_args.args[0]
    assert "Scope: all" in prompt
    assert "Apple" in prompt
    assert "Microsoft" in prompt
    assert result["scope"] == "all processed documents"


def test_chat_with_no_documents_does_not_call_the_model(monkeypatch, tmp_path):
    _use_temp_stores(monkeypatch, tmp_path)
    with patch("src.agents.agent._invoke_chat") as invoke:
        result = answer_question("What was revenue?", None)
    invoke.assert_not_called()
    assert "no documents" in result["reply"].lower()


def test_extraction_stores_financial_facts_and_replaces_them(monkeypatch, tmp_path):
    import sqlite3

    from src.agents.agent import record_analysis
    from src.llm_cache import store_financial_facts

    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    store_financial_facts(
        ticker="msft",
        fiscal_year=2025,
        company_name="Microsoft",
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        metrics={
            "revenue": {
                "value": 100,
                "unit": "USD",
                "period_start": "2024-07-01",
                "period_end": "2025-06-30",
                "xbrl_tag": "Revenue",
            }
        },
        calculations={"free_cash_flow": {"value": 40, "unit": "USD", "formula": "operating_cash_flow - capital_expenditures"}},
    )
    store_financial_facts(
        ticker="MSFT",
        fiscal_year=2025,
        company_name="Microsoft",
        metrics={"revenue": {"value": 110, "unit": "USD"}},
        calculations={},
    )
    record_analysis(
        {
            "company_name": "Microsoft",
            "ticker": "MSFT",
            "fiscal_year": 2025,
            "filing_url": "https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
            "financial_metrics": [
                {"name": "Revenue", "value": "110", "unit": "USD", "source_section": "Income statement"}
            ],
        }
    )
    with sqlite3.connect(tmp_path / "cache.db") as connection:
        rows = connection.execute(
            """
            SELECT source, metric_name, value, document_id
            FROM financial_facts
            ORDER BY source, metric_name
            """
        ).fetchall()
    assert rows == [
        ("analysis", "Revenue", 110.0, 1),
        ("extraction", "revenue", 110.0, 1),
    ]
