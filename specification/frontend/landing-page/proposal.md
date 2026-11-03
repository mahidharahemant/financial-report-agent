# Proposal: Processed-document landing

## Intent

Processed filings appear only after a new ticker search. The first screen should list them and accept natural-language questions.

## Scope

### In Scope

- Catalog row on a completed analysis: company, ticker, fiscal year, filing URL, local file, processed time.
- `GET /api/documents` for that catalog.
- Landing page: document list on the left, chat transcript and composer on the right.
- `POST /api/chat` for a question scoped to the selected document, or to all processed documents when none is selected.
- Reuse `data/llm_cache.db` so an identical chat prompt returns the stored reply.

### Out of Scope

- Replacing the filing viewer and extracted-data workspace.
- Accounts, sharing, or deleting documents.
- Vector search or fuzzy matching.
- Token streaming.

## Approach

Upsert `processed_documents` after a successful analysis. The home page replaces the empty start state. The left pane reads `GET /api/documents`. The right pane posts the question and optional document id to `POST /api/chat`, which checks that exact prompt in `data/llm_cache.db` and calls the Anthropic agent only on a miss.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/agents/agent.py` | Modified | Record a processed document after analysis |
| `src/llm_cache.py` | Modified | Catalog table beside the prompt cache |
| `src/api.py` | New | List and chat endpoints |
| `frontend/src/App.jsx` | Modified | Landing replaces the empty start state |
| `frontend/src/components/` | New | Document list pane and chat pane |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Older filings missing from the list | Med | Backfill from `data/filings/` when ticker and year are known |
| Answers beyond saved evidence | Med | Limit context to the selected analysis and filing |
| Rephrased questions miss the cache | Med | Identical prompt text skips the model |

## Rollback Plan

Remove the landing route and both endpoints. Leave `processed_documents` unused. The ticker form and analysis workspace remain.

## Dependencies

- `data/llm_cache.db`, `data/filings/`, and `ANTHROPIC_API_KEY` for an uncached question

## Success Criteria

- [ ] Opening the app shows processed documents on the left and a chat composer on the right.
- [ ] A newly analyzed document appears in the list.
- [ ] A question about a selected document is answered from that document, and the same question does not call the model again.
