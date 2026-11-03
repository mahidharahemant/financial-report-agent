from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

FILINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "filings"


def filing_path(url: str) -> Path:
    parts = [part for part in urlparse(url).path.split("/") if part]
    name = "_".join(parts[-3:]) if parts else "filing.html"
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._") or "filing.html"
    return FILINGS_DIR / safe


def read_saved_filing(url: str) -> str | None:
    path = filing_path(url)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def save_filing(url: str, html: str) -> Path:
    path = filing_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
