from __future__ import annotations

import re
from collections import OrderedDict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Comment

from src.config import SEC_USER_AGENT
from src.document_store import read_saved_filing, save_filing
from src.sec_client import SECClientError

FILING_URL = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/\d+/[A-Za-z0-9._/-]+$"
)
ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "center", "col", "colgroup",
    "dd", "div", "dl", "dt", "em", "font", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "small", "span", "strong", "sub",
    "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
DROP_TAGS = {
    "script", "style", "iframe", "object", "embed", "link", "meta", "base",
    "form", "noscript", "svg", "button", "input", "textarea", "select",
}
TABLE_ATTRS = {"border", "cellpadding", "cellspacing", "width", "summary", "align"}
CELL_ATTRS = {"colspan", "rowspan", "align", "valign", "width", "nowrap"}
_CACHE: OrderedDict[str, str] = OrderedDict()
_CACHE_LIMIT = 4


def validate_filing_url(url: str) -> str:
    if not isinstance(url, str) or not FILING_URL.fullmatch(url):
        raise SECClientError("Filing URL must be an SEC EDGAR archive document.")
    return url


def fetch_filing_html(url: str) -> str:
    validate_filing_url(url)
    saved = read_saved_filing(url)
    if saved is not None:
        return saved
    response = requests.get(
        url,
        headers={"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"},
        timeout=60,
        allow_redirects=False,
    )
    if response.is_redirect:
        raise SECClientError("Filing URL redirected. The document was not downloaded.")
    if response.status_code == 429:
        raise SECClientError("SEC rate limit reached. Wait and retry.")
    response.raise_for_status()
    save_filing(url, response.text)
    return response.text


def load_filing_document(url: str) -> str:
    validate_filing_url(url)
    cached = _CACHE.get(url)
    if cached is not None:
        _CACHE.move_to_end(url)
        return cached
    document = sanitize_filing_html(fetch_filing_html(url), url)
    _CACHE[url] = document
    _CACHE.move_to_end(url)
    while len(_CACHE) > _CACHE_LIMIT:
        _CACHE.popitem(last=False)
    return document


def sanitize_filing_html(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(list(DROP_TAGS)):
        tag.decompose()
    for tag in list(soup.find_all(True)):
        if tag.name in {"html", "head", "body"}:
            continue
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        tag.attrs = _clean_attrs(tag, base_url)
    if soup.head:
        soup.head.decompose()
    container = soup.body if soup.body else soup
    return "".join(str(node) for node in container.contents).strip()


def _clean_attrs(tag, base_url: str) -> dict:
    source = tag.attrs or {}
    cleaned: dict[str, str] = {}
    style = _safe_style(source.get("style"))
    if style:
        cleaned["style"] = style
    if tag.name == "table":
        cleaned.update(_copy_attrs(source, TABLE_ATTRS))
    elif tag.name in {"td", "th"}:
        cleaned.update(_copy_attrs(source, CELL_ATTRS))
    elif tag.name == "col":
        cleaned.update(_copy_attrs(source, {"span", "width"}))
    elif tag.name == "a":
        href = _safe_url(source.get("href"), base_url)
        if href:
            cleaned["href"] = href
            cleaned["target"] = "_blank"
            cleaned["rel"] = "noreferrer"
    elif tag.name == "img":
        src = _safe_url(source.get("src"), base_url)
        if src:
            cleaned["src"] = src
        alt = source.get("alt")
        if isinstance(alt, str):
            cleaned["alt"] = alt
        cleaned.update(_copy_attrs(source, {"width", "height"}))
    return cleaned


def _copy_attrs(source: dict, names: set[str]) -> dict[str, str]:
    copied = {}
    for name in names:
        value = source.get(name)
        if isinstance(value, str) and value.strip():
            copied[name] = value.strip()
        elif isinstance(value, (int, float)):
            copied[name] = str(value)
        elif value == "" or value is True:
            copied[name] = name
    return copied


def _safe_style(value) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.lower()
    if any(token in lowered for token in ("expression", "javascript", "url(", "@import", "behavior")):
        return None
    return value


def _safe_url(value, base_url: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if value.strip().lower().startswith("javascript:"):
        return None
    absolute = urljoin(base_url, value.strip())
    if absolute.startswith("https://www.sec.gov/") or absolute.startswith("https://sec.gov/"):
        return absolute
    return None
