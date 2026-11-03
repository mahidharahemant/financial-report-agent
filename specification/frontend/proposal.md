# Proposal: Financial report frontend

## Intent

A reader should see the 10-K and the extracted analysis at the same time. Selecting a figure or quoted passage should move the filing to that text and mark it, so the source can be checked without leaving the page.

## Scope

### In Scope

- A React single-page app for one analysis at a time.
- Ticker and fiscal-year input, example tickers, and a sample filing.
- API health, loading, validation, and analysis errors.
- A two-panel workspace: filing on the left, extracted data on the right.
- Loading the sanitized filing from the backend.
- Click-to-highlight for metric values, risk evidence, outlook, and observations.
- JSON download of the analysis.
- A compact request bar once a result is showing.
- Stacked panels on a narrow viewport.

### Out of Scope

- Filing discovery, XBRL math, narrative search, and the model call.
- Editing the filing or saving highlights.
- Accounts, history, or comparing two companies.
- The Streamlit screen.
- Highlighting text that is only a paraphrase of the filing.

## Approach

Vite serves the React app and proxies `/api` to the FastAPI process. The page posts `{ ticker, fiscal_year }` to `/api/analyze`, then loads `/api/filing` when the result has a `filing_url`. Sample filing skips the network and uses a built-in excerpt. Extracted values become buttons. A click builds search strings for the amount, including millions and billions as printed in filings, or for the quoted passage. The left panel finds the best match, prefers text near the metric name, paints a highlight, and scrolls that range into view.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/App.jsx` | Current | Request form, health, loading, and workspace state |
| `frontend/src/api.js` | Current | Health, analyze, and filing requests |
| `frontend/src/components/Workspace.jsx` | Current | Two-panel composition and selection |
| `frontend/src/components/DocumentPanel.jsx` | Current | Filing render, status, and scroll |
| `frontend/src/components/AnalysisView.jsx` | Current | Metrics, risks, outlook, observations, download |
| `frontend/src/locators.js` | Current | Search strings and match choice |
| `frontend/src/highlight.js` | Current | Document highlight and scroll |
| `frontend/src/sample.js` | Current | Offline sample filing and analysis |
| `frontend/src/styles.css` | Current | Desk, panels, and highlight color |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| XBRL dollars do not appear as full dollars in the HTML | High | Search scaled whole-number forms and the nearby label |
| Model prose is not a verbatim quote | High | Say the passage was not found; do not highlight a weak fragment |
| A large 10-K is slow to render | Med | Load it once per result and scroll inside the left panel |
| SEC HTML could carry script | Med | Render only HTML already sanitized by the backend; the sample is local |

## Rollback Plan

Restore the single-column results view and stop calling `/api/filing`. Analysis, download, and the request form continue to work without document highlight.

## Dependencies

- The backend health, analyze, and filing endpoints
- Node.js 20 and the Vite dev server, or a built `frontend/dist`
- A browser that can paint CSS highlights for the yellow mark

## Success Criteria

- [ ] After analysis, the filing and the extracted data are visible together.
- [ ] Clicking a value that exists in the filing highlights that text and scrolls it into view.
- [ ] Clicking text that is not in the filing leaves the document unmarked and explains the miss.
- [ ] Sample filing demonstrates the layout without an API key or EDGAR call.
