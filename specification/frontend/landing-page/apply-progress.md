# Apply progress: processed-document landing

**Mode**: TDD for the API and catalog. Frontend checked in the browser.

## Completed

- [x] Catalog table, upsert, newest-first list, and backfill from known analyses
- [x] Record a document when analysis completes, including a filing URL filled afterward
- [x] `GET /api/documents` and `POST /api/chat` with exact-prompt cache
- [x] Landing list and chat replace the empty start; ticker form and workspace remain

## Tests

`tests/test_llm_cache.py` and `tests/test_api.py`: 32 passed with `tests/test_filing_view.py`.

## Deviations

None. Chat reads a saved filing excerpt and does not call the filing tools.
