# Design: Processed-document landing

## Technical Approach

Keep the ticker form, analysis workspace, and exact-prompt cache. Add a `processed_documents` table in `data/llm_cache.db`, list and chat routes on the existing FastAPI app, and replace the idle capability cards with a two-pane landing. Specs: backend catalog, list, and chat; frontend list, chat, and modified empty start.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Catalog store | New database, or the existing cache file | A second file splits backups; one file matches the proposal | Table in `llm_cache.db`, created in `_connect()` |
| Identity | Filing filename, or ticker + year | Filenames are CIK, accession, and document name | Unique on ticker + fiscal year; repeat analysis updates one row |
| When to record | Inside `analyze_company` only, or again after URL fill | The API may fill `filing_url` after the agent returns | Upsert in `analyze_company`, then again in `run_analysis` |
| Chat evidence | SEC tools, or saved JSON plus local HTML | Tools can re-download and leave the selected filing | No tools. Pass stored analysis JSON and a local HTML excerpt |
| Cache key | Question text only, or question plus scope | Same wording about another filing would collide | Exact prompt includes the question and document id, or `all` |
| Empty catalog chat | Call the model, or answer locally | A model call has no evidence | Return a fixed “no documents” reply and do not call the model |
| Backfill | Parse filing names, or read known analyses | Names do not contain ticker and year | On list, import `output/analysis_*.json` and cached analysis JSON when ticker and year exist |

## Data Flow

```
analyze_company ──→ llm_calls
       │
       └──→ processed_documents ←── run_analysis (filing URL, local path)
                      │
GET /api/documents ───┤── backfill output JSON + cached analyses
                      │
POST /api/chat ── exact prompt ── llm_calls hit ── stored reply
                      └── miss ── ChatAnthropic (no tools) ── store reply
```

Landing loads the list. A row sets `document_id`; clearing it sends `all`. A completed analysis still opens the workspace. “Back to documents” clears that result and reloads the list.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/llm_cache.py` | Modify | `processed_documents` plus upsert, list, get, and backfill |
| `src/agents/agent.py` | Modify | Record the analysis; add a tool-free chat prompt and invoke |
| `src/api.py` | Modify | `GET /api/documents` and `POST /api/chat` |
| `frontend/src/api.js` | Modify | `listDocuments` and `askQuestion` |
| `frontend/src/App.jsx` | Modify | Landing instead of capability cards; return control |
| `frontend/src/components/Landing.jsx` | Create | List pane and chat pane |
| `frontend/src/styles.css` | Modify | Landing grid; stack at the existing 800px breakpoint |
| `tests/test_llm_cache.py` | Modify | Upsert, order, backfill |
| `tests/test_api.py` | Modify | List, chat cache hit, unknown id, blank question |

## Interfaces / Contracts

`processed_documents`: `id`, `company_name`, `ticker`, `fiscal_year`, `filing_url`, `local_file`, `analysis_json`, `processed_at`. Unique `(ticker, fiscal_year)`.

`GET /api/documents` → `{ "documents": [{ "id", "company_name", "ticker", "fiscal_year", "filing_url" }] }`, newest `processed_at` first.

`POST /api/chat` body: `{ "question": string, "document_id": int | null }`. Reply: `{ "reply": string, "cached": bool, "scope": string }`. Blank question is 422. Unknown id is 404. Same errors as analyze for a missing key or model failure. The prompt tells the model to answer only from the supplied analysis and excerpt and not to give investment advice. Excerpt cap: 12,000 characters of saved HTML.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Upsert, list order, backfill, cache skip | pytest, temp `DB_PATH`, patch `_invoke_agent` |
| Integration | Documents and chat status codes | `TestClient`; patch chat invoke |
| UI | List, empty state, select and clear, blank send, failed reply, return from workspace | Browser on the Vite app; no frontend test runner exists |

## Migration / Rollout

No flag. The first list call backfills rows whose ticker and year are already known. Filings with no analysis record stay unlisted. Rollback removes the routes and landing; the table can remain unused.

## Open Questions

None.
