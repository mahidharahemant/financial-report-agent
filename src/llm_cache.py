from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.document_store import filing_path
from src.log import get_logger
from src.schema_catalog import ensure_schema_catalog, format_schema_catalog

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "llm_cache.db"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
logger = get_logger(__name__)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL UNIQUE,
            response TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            filing_url TEXT NOT NULL DEFAULT '',
            local_file TEXT NOT NULL DEFAULT '',
            analysis_json TEXT NOT NULL,
            processed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            UNIQUE (ticker, fiscal_year)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            company_name TEXT NOT NULL DEFAULT '',
            ticker TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL,
            unit TEXT,
            period_start TEXT,
            period_end TEXT,
            xbrl_tag TEXT,
            formula TEXT,
            source_section TEXT,
            source_url TEXT,
            source TEXT NOT NULL,
            extracted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            UNIQUE (ticker, fiscal_year, metric_name, source)
        )
        """
    )
    ensure_schema_catalog(connection)
    return connection


def schema_catalog_text() -> str:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT name, description FROM schema_catalog ORDER BY name"
        ).fetchall()
    return format_schema_catalog([(str(name), str(description)) for name, description in rows])


def get_cached_response(prompt: str) -> str | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT response FROM llm_calls WHERE prompt = ?",
            (prompt,),
        ).fetchone()
    return row[0] if row else None


def store_response(prompt: str, response: str) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO llm_calls (prompt, response)
            VALUES (?, ?)
            ON CONFLICT(prompt) DO UPDATE SET response = excluded.response
            """,
            (prompt, response),
        )


def _fiscal_year(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _local_file_for(url: str) -> str:
    if not url:
        return ""
    path = filing_path(url)
    return str(path) if path.is_file() else ""


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[: cleaned.rstrip().rfind("```")]
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def _identity(payload: dict[str, Any]) -> tuple[str, int] | None:
    ticker = str(payload.get("ticker") or "").strip().upper()
    year = _fiscal_year(payload.get("fiscal_year"))
    if not ticker or year is None:
        return None
    if not any(key in payload for key in ("company_name", "financial_metrics", "filing_url", "raw_analysis")):
        return None
    return ticker, year


def _document_row(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0],
        "company_name": row[1],
        "ticker": row[2],
        "fiscal_year": row[3],
        "filing_url": row[4],
        "local_file": row[5],
        "analysis_json": row[6],
        "processed_at": row[7],
    }


def upsert_processed_document(
    *,
    company_name: str,
    ticker: str,
    fiscal_year: int,
    filing_url: str,
    local_file: str,
    analysis: dict[str, Any],
    processed_at: str | None = None,
) -> int:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO processed_documents (
                company_name, ticker, fiscal_year, filing_url, local_file, analysis_json, processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))
            ON CONFLICT(ticker, fiscal_year) DO UPDATE SET
                company_name = excluded.company_name,
                filing_url = excluded.filing_url,
                local_file = excluded.local_file,
                analysis_json = excluded.analysis_json,
                processed_at = excluded.processed_at
            """,
            (
                company_name or ticker.upper(),
                ticker.upper(),
                fiscal_year,
                filing_url or "",
                local_file or "",
                json.dumps(analysis, ensure_ascii=False),
                processed_at,
            ),
        )
        row = connection.execute(
            "SELECT id FROM processed_documents WHERE ticker = ? AND fiscal_year = ?",
            (ticker.upper(), fiscal_year),
        ).fetchone()
    return int(row[0])


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _fact_rows(metrics: Any, calculations: Any, filing_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(metrics, dict):
        for name, item in metrics.items():
            item = item if isinstance(item, dict) else {"value": item}
            rows.append(
                {
                    "metric_name": str(name),
                    "value": _as_float(item.get("value")),
                    "unit": item.get("unit"),
                    "period_start": item.get("period_start"),
                    "period_end": item.get("period_end"),
                    "xbrl_tag": item.get("xbrl_tag"),
                    "formula": None,
                    "source_section": None,
                    "source_url": item.get("source_url") or filing_url,
                }
            )
    elif isinstance(metrics, list):
        for item in metrics:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            rows.append(
                {
                    "metric_name": str(item["name"]),
                    "value": _as_float(item.get("value")),
                    "unit": item.get("unit"),
                    "period_start": None,
                    "period_end": None,
                    "xbrl_tag": None,
                    "formula": None,
                    "source_section": item.get("source_section"),
                    "source_url": item.get("source_url") or filing_url,
                }
            )
    if isinstance(calculations, dict):
        for name, item in calculations.items():
            if not isinstance(item, dict):
                item = {"value": item}
            unit = item.get("unit")
            if unit is None and "growth" in str(name):
                unit = "percent"
            rows.append(
                {
                    "metric_name": str(name),
                    "value": _as_float(item.get("value")),
                    "unit": unit,
                    "period_start": None,
                    "period_end": item.get("period_end"),
                    "xbrl_tag": None,
                    "formula": item.get("formula"),
                    "source_section": None,
                    "source_url": filing_url,
                }
            )
    return rows


def store_financial_facts(
    *,
    ticker: str,
    fiscal_year: int,
    company_name: str = "",
    filing_url: str = "",
    metrics: Any = None,
    calculations: Any = None,
    source: str = "extraction",
) -> int:
    ticker = ticker.strip().upper()
    rows = _fact_rows(metrics, calculations, filing_url or "")
    with _connect() as connection:
        document = connection.execute(
            "SELECT id FROM processed_documents WHERE ticker = ? AND fiscal_year = ?",
            (ticker, fiscal_year),
        ).fetchone()
        document_id = int(document[0]) if document else None
        if document_id is not None:
            connection.execute(
                """
                UPDATE financial_facts
                SET document_id = ?
                WHERE ticker = ? AND fiscal_year = ? AND document_id IS NULL
                """,
                (document_id, ticker, fiscal_year),
            )
        connection.execute(
            "DELETE FROM financial_facts WHERE ticker = ? AND fiscal_year = ? AND source = ?",
            (ticker, fiscal_year, source),
        )
        connection.executemany(
            """
            INSERT INTO financial_facts (
                document_id, company_name, ticker, fiscal_year, metric_name, value, unit,
                period_start, period_end, xbrl_tag, formula, source_section, source_url, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    company_name or ticker,
                    ticker,
                    fiscal_year,
                    row["metric_name"],
                    row["value"],
                    row["unit"],
                    row["period_start"],
                    row["period_end"],
                    row["xbrl_tag"],
                    row["formula"],
                    row["source_section"],
                    row["source_url"],
                    source,
                )
                for row in rows
            ],
        )
    logger.info(
        "stored financial facts ticker=%s fiscal_year=%s source=%s count=%s",
        ticker,
        fiscal_year,
        source,
        len(rows),
    )
    return len(rows)


def _catalog_exists(ticker: str, fiscal_year: int) -> bool:
    with _connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM processed_documents WHERE ticker = ? AND fiscal_year = ?",
            (ticker, fiscal_year),
        ).fetchone()
    return row is not None


def _import_payload(payload: dict[str, Any]) -> None:
    identity = _identity(payload)
    if identity is None:
        return
    ticker, fiscal_year = identity
    if _catalog_exists(ticker, fiscal_year):
        return
    filing_url = payload.get("filing_url") if isinstance(payload.get("filing_url"), str) else ""
    upsert_processed_document(
        company_name=str(payload.get("company_name") or ticker),
        ticker=ticker,
        fiscal_year=fiscal_year,
        filing_url=filing_url,
        local_file=_local_file_for(filing_url),
        analysis=payload,
    )


def backfill_processed_documents() -> None:
    if OUTPUT_DIR.is_dir():
        for path in sorted(OUTPUT_DIR.glob("analysis_*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                _import_payload(payload)
    with _connect() as connection:
        cached = connection.execute("SELECT response FROM llm_calls").fetchall()
    for (response,) in cached:
        payload = _parse_json_object(response)
        if payload:
            _import_payload(payload)


def backfill_financial_facts() -> None:
    with _connect() as connection:
        documents = connection.execute(
            """
            SELECT id, company_name, ticker, fiscal_year, filing_url, analysis_json
            FROM processed_documents
            """
        ).fetchall()
        for document_id, company_name, ticker, fiscal_year, filing_url, analysis_json in documents:
            exists = connection.execute(
                """
                SELECT 1 FROM financial_facts
                WHERE ticker = ? AND fiscal_year = ? AND source = 'analysis'
                LIMIT 1
                """,
                (ticker, fiscal_year),
            ).fetchone()
            if exists:
                continue
            try:
                analysis = json.loads(analysis_json)
            except json.JSONDecodeError:
                continue
            if not isinstance(analysis, dict):
                continue
            rows = _fact_rows(analysis.get("financial_metrics"), None, filing_url or "")
            if not rows:
                continue
            connection.executemany(
                """
                INSERT INTO financial_facts (
                    document_id, company_name, ticker, fiscal_year, metric_name, value, unit,
                    period_start, period_end, xbrl_tag, formula, source_section, source_url, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'analysis')
                """,
                [
                    (
                        document_id,
                        company_name or ticker,
                        ticker,
                        fiscal_year,
                        row["metric_name"],
                        row["value"],
                        row["unit"],
                        row["period_start"],
                        row["period_end"],
                        row["xbrl_tag"],
                        row["formula"],
                        row["source_section"],
                        row["source_url"],
                    )
                    for row in rows
                ],
            )


def list_processed_documents() -> list[dict[str, Any]]:
    backfill_processed_documents()
    backfill_financial_facts()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, company_name, ticker, fiscal_year, filing_url, local_file, analysis_json, processed_at
            FROM processed_documents
            ORDER BY processed_at DESC, id DESC
            """
        ).fetchall()
    return [_document_row(row) for row in rows]


def get_processed_document(document_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, company_name, ticker, fiscal_year, filing_url, local_file, analysis_json, processed_at
            FROM processed_documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()
    return _document_row(row) if row else None
