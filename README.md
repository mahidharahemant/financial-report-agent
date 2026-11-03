# Financial Report Intelligence Agent

A small portfolio project using Python, LangChain, SEC EDGAR, XBRL, Pydantic, and a React single-page app.

## Features
- Find a company's SEC 10-K annual filing by ticker and fiscal year.
- Retrieve common financial metrics from the SEC Company Facts XBRL API.
- Calculate revenue growth and free cash flow in Python.
- Search filing narrative for risks, business strategy, and management commentary.
- Use a LangChain tool-calling agent to select tools and synthesize a structured answer.
- Display source links and download JSON output.

This is an educational prototype, not investment advice. XBRL tagging varies by issuer; narrative search is heuristic and all findings should be verified against the source filing.

## Setup
Python 3.11+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` and a descriptive `SEC_USER_AGENT` in `.env`. The model defaults to `claude-sonnet-5-5`. Example:
`FinancialReportAgent contact you@example.com`

## Run the web app
The React single-page app is the frontend. FastAPI runs the same agent as the CLI. Node.js 20+ is required for the UI.

```bash
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Enter a ticker and fiscal year, then choose Analyze annual report. The filing opens on the left and the extracted values on the right. Click a value to highlight that passage in the filing. A full analysis calls SEC EDGAR and the model, and often takes about a minute. Sample filing shows the layout without calling the model.

Repeated analysis prompts are read from `data/llm_cache.db` instead of calling the model again. Downloaded filings are saved under `data/filings/`.

To serve the built page from the API process:

```bash
cd frontend && npm run build
uvicorn src.api:app --port 8000
```

Then open http://127.0.0.1:8000.

The Streamlit UI is still available with `streamlit run app.py`. The CLI is:

```bash
python -m src.cli --ticker MSFT --fiscal-year 2025
```

## Architecture
1. `find_10k_filing` uses SEC ticker mapping and submissions metadata.
2. `get_financial_metrics` uses SEC Company Facts (XBRL) and calculates metrics deterministically.
3. `search_report_content` downloads the filing HTML and searches relevant sections.
4. A LangChain agent chooses tools and synthesizes evidence-backed analysis.
5. Pydantic models define the expected output contract; the UI renders JSON and sources.

## Tests
```bash
pytest -q
```
Unit tests do not require an API key or live SEC access.
