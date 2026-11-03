# Proposal: Financial report backend

## Intent

Analysts need an evidence-backed reading of a public 10-K without inventing numbers. The backend finds the filing, computes metrics in Python, searches the narrative, and asks Claude only to synthesize tool output. Repeat requests must not call the model or EDGAR again when the same prompt or document is already stored.

## Scope

### In Scope

- Resolve a ticker and fiscal year to one SEC 10-K.
- Retrieve standard XBRL facts and calculate revenue growth and free cash flow.
- Search filing narrative for risks, strategy, and management commentary.
- Run a tool-calling agent on Anthropic and return a structured analysis.
- Cache an exact analysis prompt and its model response in SQLite.
- Save downloaded filing HTML under `data/filings/` and reuse it.
- Serve analysis and a sanitized filing document over HTTP.
- Keep a CLI that prints and writes the same analysis JSON.

### Out of Scope

- Personalized investment advice.
- Authentication, multi-user storage, or a hosted database.
- Semantic or fuzzy prompt matching.
- Caching intermediate tool-calling turns inside one agent run.
- Full XBRL taxonomy coverage or guaranteed section detection.
- The React layout, highlight behavior, and sample filing.

## Approach

`SECClient` reads EDGAR ticker, submission, and company-facts APIs. `get_financial_metrics` selects annual facts in Python. `search_report_content` downloads the filing and searches heuristic 10-K sections. `analyze_company` looks up the exact user prompt in `data/llm_cache.db` before creating the LangChain agent. On a miss it calls `claude-sonnet-5-5` with tools, then stores the raw model text. `fetch_filing_html` and `filing_text` read `data/filings/` before the network and write the raw HTML after a download. FastAPI exposes `POST /api/analyze` and `GET /api/filing`. The filing response is sanitized HTML limited to `https://www.sec.gov/Archives/edgar/data/`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sec_client.py` | Current | Read-only EDGAR access and filing text |
| `src/financial_metrics.py` | Current | XBRL selection and deterministic calculations |
| `src/report_search.py` | Current | Heuristic narrative search |
| `src/agents/agent.py` | Current | Anthropic agent and prompt cache lookup |
| `src/llm_cache.py` | Current | SQLite prompt and response store |
| `src/document_store.py` | Current | On-disk filing files |
| `src/filing_view.py` | Current | Download, reuse, and HTML sanitizing |
| `src/api.py` | Current | Health, analysis, and filing HTTP API |
| `src/cli.py` | Current | JSON stdout and `output/` file |
| `src/schemas.py` | Current | Expected analysis contract |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| A changed system prompt still hits an old cached user prompt | Med | Cache key is the exact user prompt; change that text to invalidate |
| A saved filing or response is stale after an SEC amendment | Med | Delete the file or database row and rerun |
| Sanitizer strips layout the filing needs | Med | Allow presentational table attributes and safe inline styles |
| EDGAR rate limits or blocks a missing user agent | Med | Send `SEC_USER_AGENT` and do not follow redirects |

## Rollback Plan

Remove the cache lookup in `analyze_company` and the disk read in `fetch_filing_html` and `filing_text`. Delete `data/llm_cache.db` and `data/filings/`. The agent and EDGAR calls then run on every request.

## Dependencies

- `ANTHROPIC_API_KEY` and `MODEL` in `.env`
- `SEC_USER_AGENT` that identifies the caller to EDGAR
- Python packages in `requirements.txt`, including LangChain 1 and `langchain-anthropic`
- Network access to `www.sec.gov` and `data.sec.gov` on a cache miss

## Success Criteria

- [ ] A valid ticker and fiscal year returns filing metadata, metrics, narrative evidence, and source URLs, or an explicit limitation when data is missing.
- [ ] The same analysis prompt does not call Anthropic again.
- [ ] A filing URL that was downloaded once is served from `data/filings/` afterward.
- [ ] Non-SEC filing URLs are rejected and active HTML is stripped before the document is returned.
