from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from src.filing_view import load_filing_document
from src.log import get_logger
from src.sec_client import SECClientError

logger = get_logger(__name__)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,11}$")

app = FastAPI(title="Financial Report Intelligence Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    fiscal_year: int = Field(ge=1994, le=2100)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not TICKER_PATTERN.fullmatch(ticker):
            raise ValueError("Use a ticker such as MSFT or BRK.B.")
        return ticker


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/filing")
def filing(url: str = Query(min_length=1)) -> dict[str, str]:
    try:
        html = load_filing_document(url)
    except SECClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The filing could not be downloaded.") from exc
    return {"filing_url": url, "html": html}


def run_analysis(ticker: str, fiscal_year: int) -> dict:
    from src.agents.agent import analyze_company, record_analysis
    from src.sec_client import SECClient

    result = analyze_company(ticker, fiscal_year)
    if isinstance(result, dict) and not result.get("filing_url"):
        try:
            filing = SECClient().find_10k(ticker, fiscal_year)
        except SECClientError:
            record_analysis(result)
            return result
        result["filing_url"] = filing.get("filing_url")
        result.setdefault("company_name", filing.get("company_name"))
    if isinstance(result, dict):
        record_analysis(result)
    return result


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    question: str
    document_id: int | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)

    @field_validator("question")
    @classmethod
    def require_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Enter a question.")
        return question


@app.get("/api/documents/{document_id}")
def document(document_id: int) -> dict:
    import json

    from src.llm_cache import get_processed_document

    row = get_processed_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="That document is not in the catalog.")
    try:
        analysis = json.loads(row["analysis_json"])
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="The saved analysis could not be read.") from exc
    if not isinstance(analysis, dict):
        raise HTTPException(status_code=500, detail="The saved analysis could not be read.")
    analysis.setdefault("company_name", row["company_name"])
    analysis.setdefault("ticker", row["ticker"])
    analysis.setdefault("fiscal_year", row["fiscal_year"])
    if row["filing_url"] and not analysis.get("filing_url"):
        analysis["filing_url"] = row["filing_url"]
    analysis["id"] = row["id"]
    return analysis


@app.get("/api/documents")
def documents() -> dict:
    from src.llm_cache import list_processed_documents

    rows = list_processed_documents()
    return {
        "documents": [
            {
                "id": row["id"],
                "company_name": row["company_name"],
                "ticker": row["ticker"],
                "fiscal_year": row["fiscal_year"],
                "filing_url": row["filing_url"],
            }
            for row in rows
        ]
    }


@app.post("/api/chat")
def chat(body: ChatRequest) -> dict:
    from src.agents.agent import answer_question

    logger.info("chat document_id=%s question=%s", body.document_id, body.question[:200])
    try:
        history = [{"role": turn.role, "text": turn.text} for turn in body.history if turn.text.strip()]
        return answer_question(body.question, body.document_id, history)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "The analysis agent could not start. Install requirements.txt "
                "in this Python environment and restart the API."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("chat failed")
        raise HTTPException(status_code=502, detail=str(exc) or "The question could not be answered.") from exc


@app.post("/api/analyze")
def analyze(body: AnalyzeRequest) -> dict:
    logger.info("analyze ticker=%s fiscal_year=%s", body.ticker, body.fiscal_year)
    try:
        return run_analysis(body.ticker, body.fiscal_year)
    except SECClientError as exc:
        logger.info("analyze missing filing ticker=%s fiscal_year=%s", body.ticker, body.fiscal_year)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "The analysis agent could not start. Install requirements.txt "
                "in this Python environment and restart the API."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("analyze failed ticker=%s fiscal_year=%s", body.ticker, body.fiscal_year)
        raise HTTPException(status_code=502, detail=str(exc) or "Analysis failed.") from exc


@app.get("/")
def root():
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return {
        "service": "Financial Report Intelligence Agent",
        "ui": "From frontend/, run npm install and npm run dev. Build the page to serve it from this process.",
        "health": "/api/health",
    }


def _mount_frontend() -> None:
    assets = DIST / "assets"
    if assets.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    icon = DIST / "favicon.svg"
    if icon.is_file():

        @app.get("/favicon.svg", include_in_schema=False)
        def favicon() -> FileResponse:
            return FileResponse(icon)


_mount_frontend()
