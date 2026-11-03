from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app
from src.llm_cache import upsert_processed_document
from src.sec_client import SECClientError

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_rejects_invalid_ticker():
    response = client.post("/api/analyze", json={"ticker": "123", "fiscal_year": 2025})
    assert response.status_code == 422


def test_analyze_rejects_fiscal_year_out_of_range():
    response = client.post("/api/analyze", json={"ticker": "MSFT", "fiscal_year": 1800})
    assert response.status_code == 422


def test_analyze_returns_agent_payload():
    payload = {
        "company_name": "Microsoft Corporation",
        "ticker": "MSFT",
        "fiscal_year": 2025,
        "financial_metrics": [],
        "risk_factors": [],
        "management_outlook": [],
        "key_observations": [],
        "limitations": [],
    }
    with patch("src.api.run_analysis", return_value=payload) as analyze_company:
        response = client.post("/api/analyze", json={"ticker": " msft ", "fiscal_year": 2025})
    assert response.status_code == 200
    assert response.json()["company_name"] == "Microsoft Corporation"
    analyze_company.assert_called_once_with("MSFT", 2025)


def test_analyze_maps_missing_filing_to_404():
    with patch("src.api.run_analysis", side_effect=SECClientError("No recent 10-K found.")):
        response = client.post("/api/analyze", json={"ticker": "MSFT", "fiscal_year": 2025})
    assert response.status_code == 404
    assert "10-K" in response.json()["detail"]


def test_analyze_maps_import_errors_to_a_setup_message():
    with patch("src.api.run_analysis", side_effect=ImportError("create_agent")):
        response = client.post("/api/analyze", json={"ticker": "MSFT", "fiscal_year": 2025})
    assert response.status_code == 500
    assert "requirements.txt" in response.json()["detail"]


def test_analyze_maps_unexpected_errors_to_502():
    with patch("src.api.run_analysis", side_effect=TimeoutError("timed out")):
        response = client.post("/api/analyze", json={"ticker": "MSFT", "fiscal_year": 2025})
    assert response.status_code == 502
    assert response.json()["detail"] == "timed out"


def _use_temp_catalog(monkeypatch, tmp_path):
    monkeypatch.setattr("src.llm_cache.DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr("src.llm_cache.OUTPUT_DIR", tmp_path / "output")


def test_documents_endpoint_returns_newest_first(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    upsert_processed_document(
        company_name="Apple",
        ticker="AAPL",
        fiscal_year=2024,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/aapl.htm",
        local_file="",
        analysis={"company_name": "Apple"},
        processed_at="2024-01-01T00:00:00Z",
    )
    upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        local_file="",
        analysis={"company_name": "Microsoft"},
        processed_at="2025-01-01T00:00:00Z",
    )
    response = client.get("/api/documents")
    assert response.status_code == 200
    documents = response.json()["documents"]
    assert [item["ticker"] for item in documents] == ["MSFT", "AAPL"]
    assert set(documents[0]) == {"id", "company_name", "ticker", "fiscal_year", "filing_url"}


def test_document_endpoint_returns_the_saved_analysis(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    document_id = upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        local_file="",
        analysis={
            "company_name": "Microsoft",
            "ticker": "MSFT",
            "fiscal_year": 2025,
            "financial_metrics": [{"name": "Revenue", "value": 281724000000}],
        },
    )
    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == document_id
    assert payload["company_name"] == "Microsoft"
    assert payload["filing_url"].endswith("msft.htm")
    assert payload["financial_metrics"][0]["name"] == "Revenue"


def test_document_endpoint_rejects_an_unknown_id(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    response = client.get("/api/documents/42")
    assert response.status_code == 404


def test_documents_endpoint_is_empty(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}


def test_chat_rejects_a_blank_question():
    response = client.post("/api/chat", json={"question": "   "})
    assert response.status_code == 422


def test_chat_rejects_an_unknown_document(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    response = client.post("/api/chat", json={"question": "What was revenue?", "document_id": 42})
    assert response.status_code == 404


def test_chat_repeat_does_not_call_the_model(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    document_id = upsert_processed_document(
        company_name="Microsoft",
        ticker="MSFT",
        fiscal_year=2025,
        filing_url="https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        local_file="",
        analysis={"company_name": "Microsoft", "financial_metrics": []},
    )
    body = {"question": "What was revenue?", "document_id": document_id}
    with patch("src.agents.agent._invoke_chat", return_value="Revenue was 281.") as invoke:
        first = client.post("/api/chat", json=body)
        second = client.post("/api/chat", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["reply"] == "Revenue was 281."
    invoke.assert_called_once()


def test_run_analysis_records_the_filled_filing_url(monkeypatch, tmp_path):
    _use_temp_catalog(monkeypatch, tmp_path)
    analysis = {
        "company_name": "Microsoft",
        "ticker": "MSFT",
        "fiscal_year": 2025,
        "financial_metrics": [],
    }
    filing = {
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1/2/msft.htm",
        "company_name": "Microsoft",
    }
    with (
        patch("src.agents.agent.analyze_company", return_value=dict(analysis)),
        patch("src.sec_client.SECClient") as client_cls,
    ):
        client_cls.return_value.find_10k.return_value = filing
        from src.api import run_analysis

        result = run_analysis("MSFT", 2025)
    assert result["filing_url"] == filing["filing_url"]
    response = client.get("/api/documents")
    assert response.json()["documents"][0]["filing_url"] == filing["filing_url"]
