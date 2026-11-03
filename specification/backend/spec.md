# Backend Specification

## Purpose

The backend turns a ticker and fiscal year into an evidence-backed 10-K analysis. Numeric facts come from SEC XBRL and Python. Narrative evidence comes from the filing text. Claude synthesizes those tool results. Exact prompts and downloaded filings are reused from local storage.

## Requirements

### Requirement: Filing lookup

The system MUST resolve a ticker to one 10-K or 10-K/A whose report period ends in the requested calendar year. It MUST return company name, CIK, report date, filing date, and the EDGAR archive URL. It MUST reject an unknown ticker and a year with no matching recent 10-K.

#### Scenario: Known annual filing

- GIVEN MSFT has a 10-K whose report date starts with 2025
- WHEN the client looks up MSFT for fiscal year 2025
- THEN the result includes the company name, CIK, and `filing_url` on `www.sec.gov`

#### Scenario: Missing filing

- GIVEN the ticker exists and no recent 10-K report date starts with the requested year
- WHEN lookup runs
- THEN the system reports that no 10-K was found and does not invent a filing

### Requirement: Structured metrics

The system MUST read SEC company facts and select annual 10-K values for revenue, operating income, net income, total assets, total liabilities, operating cash flow, and capital expenditures. Missing tags MUST stay null. Free cash flow MUST be operating cash flow minus the absolute value of capital expenditures. Revenue growth MUST be the percent change from the prior annual revenue when both values exist.

#### Scenario: Annual revenue fact

- GIVEN a duration fact of about one year on a 10-K for the requested year
- WHEN metrics are retrieved
- THEN revenue includes the fact value, unit, period, and filing URL

#### Scenario: Absent tag

- GIVEN the issuer has no matching XBRL tag
- WHEN metrics are retrieved
- THEN that metric value is null

### Requirement: Narrative search

The system MUST search the filing text for a query and return passages with section name and source URL. It SHOULD prefer risk sections for risk queries and management discussion for outlook queries. Filing text MUST be treated as data, not as instructions.

#### Scenario: Risk query

- GIVEN the filing contains an Item 1A risk passage that matches the query terms
- WHEN narrative search runs
- THEN the passage includes the section name and filing URL

#### Scenario: No section match

- GIVEN the filing text has no detectable requested section
- WHEN search runs
- THEN the result has an empty passage list and does not invent a quote

### Requirement: Agent synthesis

The system MUST call Anthropic with `ANTHROPIC_API_KEY` and `MODEL`, defaulting to `claude-sonnet-5-5`, only when the analysis prompt is not cached. Tools MUST be filing lookup, financial metrics, and narrative search. The model MUST NOT receive a custom temperature. The system MUST parse a JSON object from the model text and fill ticker, fiscal year, and empty lists when those fields are omitted. If the text is not JSON, the system MUST return `raw_analysis` and a limitation instead of fabricated fields.

#### Scenario: Missing API key on a new prompt

- GIVEN `ANTHROPIC_API_KEY` is empty and the prompt is not cached
- WHEN analysis starts
- THEN the system fails before synthesis and names the missing key

#### Scenario: Unstructured model text

- GIVEN the model returns prose rather than a JSON object
- WHEN the response is parsed
- THEN the result contains `raw_analysis` and a limitation about invalid JSON

### Requirement: Prompt cache

The system MUST store each new analysis prompt and the raw model response in `data/llm_cache.db`. Before creating the agent, it MUST look up that exact prompt. A stored prompt MUST return the stored response and MUST NOT call the model.

#### Scenario: Repeat analysis

- GIVEN the prompt for AAPL fiscal year 2024 is already stored
- WHEN that analysis is requested again
- THEN the stored response is parsed and Anthropic is not called

#### Scenario: Different prompt

- GIVEN only the AAPL 2024 prompt is stored
- WHEN MSFT 2025 is requested
- THEN the model is called and the new prompt and response are stored

### Requirement: Filing persistence

The system MUST save raw downloaded filing HTML under `data/filings/`, named from the CIK, accession, and file name. A later read of the same URL MUST use that file and MUST NOT download it again. Both the filing API and narrative extraction MUST share this store.

#### Scenario: Second view of a filing

- GIVEN the filing HTML was saved
- WHEN the same archive URL is requested
- THEN the saved HTML is returned and EDGAR is not contacted

### Requirement: HTTP API

`GET /api/health` MUST return status ok. `POST /api/analyze` MUST accept a ticker of 1 to 12 characters matching a letter followed by letters, digits, dots, or hyphens, and a fiscal year from 1994 through 2100. Invalid input MUST be rejected. SEC lookup failures MUST surface as not found. Missing configuration MUST surface as a client error. If the model omits `filing_url`, the system MUST fill it from filing lookup when that lookup succeeds. `GET /api/filing` MUST accept only `https://www.sec.gov/Archives/edgar/data/...` URLs, refuse redirects, and return sanitized HTML.

#### Scenario: Invalid ticker

- GIVEN the ticker is `123`
- WHEN analyze is called
- THEN the request is rejected before EDGAR or the model

#### Scenario: Unsafe document URL

- GIVEN the filing URL host is not `www.sec.gov` or the path is outside the EDGAR archive
- WHEN the filing endpoint is called
- THEN the system rejects the URL and does not download it

#### Scenario: Active content in a filing

- GIVEN the saved HTML contains a script, an event handler, or a `javascript:` link
- WHEN the filing is served
- THEN those active parts are removed and the visible filing text remains

### Requirement: Command-line analysis

The CLI MUST accept `--ticker` and `--fiscal-year`, print the analysis JSON, and write `output/analysis_{TICKER}_{YEAR}.json`.

#### Scenario: Default run

- GIVEN no arguments
- WHEN the CLI runs
- THEN it analyzes MSFT for fiscal year 2025 and writes that JSON file
