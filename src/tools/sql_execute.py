from __future__ import annotations

import sqlite3
from typing import Any

from langchain.tools import tool

from src.log import get_logger
from src.tools.sql_query import validate_read_sql

logger = get_logger(__name__)

ROW_LIMIT = 100


@tool
def execute_sql(sql: str) -> dict[str, Any]:
    """Execute one read-only SQL query against the application SQLite database.

    Accepts a single SELECT or WITH statement produced for the processed_documents
    or llm_calls tables. Returns the column names and up to 100 rows. Refuses
    any statement that would change the database.
    """
    statement = validate_read_sql(sql)
    logger.info("execute sql %s", statement[:500])
    from src.llm_cache import DB_PATH, _connect

    _connect().close()
    uri = f"file:{DB_PATH.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        cursor = connection.execute(statement)
        columns = [column[0] for column in cursor.description or []]
        rows = cursor.fetchmany(ROW_LIMIT)
    return {
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
        "truncated": len(rows) == ROW_LIMIT,
    }
