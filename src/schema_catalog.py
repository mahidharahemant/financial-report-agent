from __future__ import annotations

import sqlite3

SCHEMA_CATALOG: tuple[tuple[str, str], ...] = (
    (
        "processed_documents",
        "One saved SEC 10-K filing and its extracted analysis. Unique on ticker and fiscal_year.",
    ),
    ("processed_documents.id", "Integer primary key for the processed filing."),
    ("processed_documents.company_name", "Company name for the filing."),
    ("processed_documents.ticker", "Uppercase stock ticker, such as AAPL."),
    ("processed_documents.fiscal_year", "Fiscal year of the annual report."),
    ("processed_documents.filing_url", "SEC URL of the 10-K HTML filing."),
    ("processed_documents.local_file", "Local path of the saved filing HTML."),
    (
        "processed_documents.analysis_json",
        "JSON analysis with financial_metrics, risk_factors, management_outlook, key_observations, and limitations.",
    ),
    ("processed_documents.processed_at", "UTC timestamp when the filing was saved."),
    (
        "financial_facts",
        "One extracted financial metric per row. Unique on ticker, fiscal_year, metric_name, and source.",
    ),
    ("financial_facts.id", "Integer primary key for the metric row."),
    (
        "financial_facts.document_id",
        "processed_documents.id for the filing. Null when the filing row did not exist yet.",
    ),
    ("financial_facts.company_name", "Company name for the metric."),
    ("financial_facts.ticker", "Uppercase stock ticker, such as AAPL."),
    ("financial_facts.fiscal_year", "Fiscal year the metric belongs to."),
    (
        "financial_facts.metric_name",
        "Metric name such as revenue, net_income, total_assets, free_cash_flow, or revenue_growth_pct.",
    ),
    ("financial_facts.value", "Numeric amount. Null when the fact was not found."),
    ("financial_facts.unit", "Unit of value, such as USD or percent."),
    ("financial_facts.period_start", "Period start date for a duration fact. Null for an instant or calculated fact."),
    ("financial_facts.period_end", "Period end date for the fact."),
    ("financial_facts.xbrl_tag", "XBRL concept used to extract a reported fact. Null for a calculation."),
    ("financial_facts.formula", "Formula for a calculated metric, such as free cash flow. Null for a reported fact."),
    ("financial_facts.source_section", "Filing section or label that supplied the metric."),
    ("financial_facts.source_url", "SEC URL of the filing that supplied the metric."),
    (
        "financial_facts.source",
        "extraction for XBRL and calculated facts, or analysis for metrics copied from the saved analysis.",
    ),
    ("financial_facts.extracted_at", "UTC timestamp when the metric row was stored."),
    (
        "llm_calls",
        "Exact prompt and model response cache. The same prompt returns the stored response.",
    ),
    ("llm_calls.id", "Integer primary key for the cached model call."),
    ("llm_calls.prompt", "Exact prompt text. Unique."),
    ("llm_calls.response", "Stored model response for the prompt."),
    ("llm_calls.created_at", "UTC timestamp when the response was stored."),
    (
        "schema_catalog",
        "Descriptions of the application tables and columns. name is a table or table.column.",
    ),
    ("schema_catalog.name", "Table name, or table.column for a column description."),
    ("schema_catalog.description", "What that table or column stores."),
)


def ensure_schema_catalog(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_catalog (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO schema_catalog (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET description = excluded.description
        """,
        SCHEMA_CATALOG,
    )
    names = [name for name, _description in SCHEMA_CATALOG]
    placeholders = ", ".join("?" for _name in names)
    connection.execute(
        f"DELETE FROM schema_catalog WHERE name NOT IN ({placeholders})",
        names,
    )


def format_schema_catalog(rows: list[tuple[str, str]]) -> str:
    return "\n".join(f"{name} -> {description}" for name, description in rows)
