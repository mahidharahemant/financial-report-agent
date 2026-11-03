from __future__ import annotations

import re

from langchain.tools import tool
from langchain_anthropic import ChatAnthropic

from src.config import ANTHROPIC_API_KEY, MODEL
from src.llm_cache import schema_catalog_text

_READ_SQL = re.compile(r"(?is)^(select|with)\b")
_FORBIDDEN = re.compile(
    r"(?is)\b(insert|update|delete|drop|alter|attach|detach|pragma|replace|create|vacuum|reindex|into)\b"
)


def validate_read_sql(sql: str) -> str:
    statement = sql.strip()
    if statement.startswith("```"):
        statement = statement.split("\n", 1)[-1]
        if statement.rstrip().endswith("```"):
            statement = statement.rstrip()[: statement.rstrip().rfind("```")]
        statement = statement.strip()
    statement = statement.rstrip(";").strip()
    if not statement or ";" in statement:
        raise ValueError("Provide one SQL statement.")
    if not _READ_SQL.match(statement) or _FORBIDDEN.search(statement):
        raise ValueError("Only a single read-only SELECT query is allowed.")
    return statement


@tool
def convert_query_to_sql(question: str) -> str:
    """Convert a database question into one read-only SQLite SELECT statement.

    Use this for questions about processed filings, extracted financial facts,
    or stored model calls. The schema catalog of tables and columns is sent
    with the question. Returns SQL text only and does not run the query or
    give investment advice.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and add your key.")
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Enter a database question.")
    catalog = schema_catalog_text()
    model = ChatAnthropic(
        model=MODEL,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=1024,
    )
    message = model.invoke(
        "Write one SQLite SELECT statement and no other text.\n"
        "Schema catalog. Each line is table -> description or table.column -> description.\n"
        f"{catalog}\n"
        f"Question: {cleaned}"
    )
    content = getattr(message, "content", message)
    if isinstance(content, list):
        content = "\n".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return validate_read_sql(str(content))
