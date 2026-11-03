import { useEffect, useState } from "react";
import { analyzeCompany, askQuestion, checkHealth, fetchDocument, fetchFiling, listDocuments } from "./api.js";
import Landing from "./components/Landing.jsx";
import Workspace from "./components/Workspace.jsx";
import { SAMPLE_ANALYSIS, SAMPLE_HTML } from "./sample.js";

const EXAMPLES = [
  { ticker: "MSFT", year: 2025 },
  { ticker: "AAPL", year: 2024 },
  { ticker: "NVDA", year: 2025 },
];

const TICKER_PATTERN = /^[A-Za-z][A-Za-z0-9.\-]{0,11}$/;

export default function App() {
  const [ticker, setTicker] = useState("MSFT");
  const [fiscalYear, setFiscalYear] = useState("2025");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [result, setResult] = useState(null);
  const [apiReady, setApiReady] = useState(null);
  const [documentHtml, setDocumentHtml] = useState("");
  const [documentStatus, setDocumentStatus] = useState("idle");
  const [documentError, setDocumentError] = useState("");
  const [inlineDocument, setInlineDocument] = useState("");
  const [documents, setDocuments] = useState([]);
  const [documentsError, setDocumentsError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatStatus, setChatStatus] = useState("idle");
  const [activity, setActivity] = useState("analyze");

  useEffect(() => {
    let cancelled = false;
    listDocuments()
      .then((rows) => {
        if (!cancelled) {
          setDocuments(rows);
          setDocumentsError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDocumentsError(err instanceof Error ? err.message : "The document list could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    checkHealth()
      .then(() => {
        if (!cancelled) setApiReady(true);
      })
      .catch(() => {
        if (!cancelled) setApiReady(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!result) {
      setDocumentHtml("");
      setDocumentStatus("idle");
      setDocumentError("");
      return undefined;
    }
    if (inlineDocument) {
      setDocumentHtml(inlineDocument);
      setDocumentStatus("ready");
      setDocumentError("");
      return undefined;
    }
    if (!result.filing_url) {
      setDocumentHtml("");
      setDocumentStatus("missing");
      setDocumentError("");
      return undefined;
    }
    let cancelled = false;
    setDocumentStatus("loading");
    setDocumentError("");
    fetchFiling(result.filing_url)
      .then((html) => {
        if (!cancelled) {
          setDocumentHtml(html);
          setDocumentStatus("ready");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setDocumentHtml("");
          setDocumentStatus("error");
          setDocumentError(err instanceof Error ? err.message : "The filing could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [result, inlineDocument]);

  function applyExample(example) {
    setTicker(example.ticker);
    setFiscalYear(String(example.year));
    setFieldError("");
  }

  async function onSubmit(event) {
    event.preventDefault();
    const cleaned = ticker.trim().toUpperCase();
    const year = Number(fiscalYear);
    if (!TICKER_PATTERN.test(cleaned)) {
      setFieldError("Use a ticker such as MSFT or BRK.B.");
      return;
    }
    if (!Number.isInteger(year) || year < 1994 || year > 2100) {
      setFieldError("Enter a fiscal year between 1994 and 2100.");
      return;
    }
    setFieldError("");
    setTicker(cleaned);
    setInlineDocument("");
    setActivity("analyze");
    setStatus("loading");
    setError("");
    try {
      const analysis = await analyzeCompany(cleaned, year);
      setResult(analysis);
      setStatus("ready");
      const rows = await listDocuments().catch(() => null);
      if (rows) {
        setDocuments(rows);
        setDocumentsError("");
      }
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Analysis failed.");
    }
  }

  function showSample() {
    setInlineDocument(SAMPLE_HTML);
    setResult(SAMPLE_ANALYSIS);
    setStatus("ready");
    setError("");
  }

  function showLanding() {
    setResult(null);
    setInlineDocument("");
    setStatus("idle");
    setError("");
    listDocuments()
      .then((rows) => {
        setDocuments(rows);
        setDocumentsError("");
        setSelectedId((current) => (rows.some((row) => row.id === current) ? current : null));
      })
      .catch((err) => {
        setDocumentsError(err instanceof Error ? err.message : "The document list could not be loaded.");
      });
  }

  async function openDocument(documentId) {
    const row = documents.find((document) => document.id === documentId);
    if (row) {
      setTicker(row.ticker);
      setFiscalYear(String(row.fiscal_year));
    }
    setSelectedId(documentId);
    setInlineDocument("");
    setResult(null);
    setActivity("open");
    setStatus("loading");
    setError("");
    try {
      const analysis = await fetchDocument(documentId);
      setResult(analysis);
      setStatus("ready");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "The saved document could not be opened.");
    }
  }

  async function sendQuestion(question) {
    const text = question.trim();
    if (!text || chatStatus === "loading") return;
    const history = messages
      .filter((message) => message.role === "user" || message.role === "assistant")
      .map((message) => ({ role: message.role, text: message.text }));
    setMessages((current) => [...current, { role: "user", text }]);
    setChatStatus("loading");
    try {
      const response = await askQuestion(text, selectedId, history);
      setMessages((current) => [...current, { role: "assistant", text: response.reply }]);
      const rows = await listDocuments().catch(() => null);
      if (rows) {
        setDocuments(rows);
        setDocumentsError("");
      }
      setChatStatus("idle");
    } catch (err) {
      setMessages((current) => [
        ...current,
        { role: "error", text: err instanceof Error ? err.message : "The question could not be answered." },
      ]);
      setChatStatus("idle");
    }
  }

  const showWorkspace = Boolean(result) && status !== "loading";
  const selected = documents.find((document) => document.id === selectedId) || null;
  const scopeLabel = selected ? `${selected.ticker} ${selected.fiscal_year}` : "all processed documents";

  return (
    <div className={showWorkspace ? "page page-workspace" : "page"}>
      <header className="masthead">
        <div className="brand">
          <span className="mark" aria-hidden="true">10-K</span>
          <div>
            <p className="eyebrow">Public filings desk</p>
            <strong>Financial Report Intelligence</strong>
          </div>
        </div>
        <p className="disclaimer">Educational prototype. This is not investment advice.</p>
      </header>

      <main className="shell" aria-busy={status === "loading"}>
        {apiReady === false && (
          <p className="banner" role="status">
            The analysis API is not responding. Start it with{" "}
            <code>uvicorn src.api:app --reload --port 8000</code>, then refresh.
          </p>
        )}

        <form className={showWorkspace ? "desk desk-compact" : "desk"} onSubmit={onSubmit}>
          <div className="desk-copy">
            <p className="eyebrow">Annual report analysis</p>
            <h1>Read a 10-K with the filing still attached.</h1>
            <p>
              The agent finds the SEC annual report, pulls XBRL facts, and searches the
              narrative for risks and management outlook. Every claim stays tied to a source.
            </p>
          </div>
          <div className="desk-panel">
            <div className="fields">
              <label>
                Ticker
                <input
                  value={ticker}
                  onChange={(event) => {
                    setTicker(event.target.value.toUpperCase());
                    setFieldError("");
                  }}
                  maxLength={12}
                  autoCapitalize="characters"
                  autoCorrect="off"
                  spellCheck="false"
                  placeholder="MSFT"
                  aria-invalid={Boolean(fieldError)}
                />
              </label>
              <label>
                Fiscal year
                <input
                  type="number"
                  min="1994"
                  max="2100"
                  step="1"
                  value={fiscalYear}
                  onChange={(event) => {
                    setFiscalYear(event.target.value);
                    setFieldError("");
                  }}
                />
              </label>
            </div>
            {fieldError && <p className="field-error">{fieldError}</p>}
            <button className="primary" type="submit" disabled={status === "loading"}>
              {status === "loading"
                ? activity === "open"
                  ? "Opening document…"
                  : "Analyzing filing…"
                : "Analyze annual report"}
            </button>
            {showWorkspace && (
              <button className="chip" type="button" onClick={showLanding}>
                Back to documents
              </button>
            )}
            <div className="examples">
              <span>Try</span>
              {EXAMPLES.map((example) => (
                <button
                  key={`${example.ticker}-${example.year}`}
                  type="button"
                  className="chip"
                  onClick={() => applyExample(example)}
                  disabled={status === "loading"}
                >
                  {example.ticker} · {example.year}
                </button>
              ))}
              <button
                type="button"
                className="chip"
                onClick={showSample}
                disabled={status === "loading"}
              >
                Sample filing
              </button>
            </div>
          </div>
        </form>

        {status === "loading" && (
          <section className="status-panel" role="status">
            <span className="pulse" aria-hidden="true" />
            <div>
              <h2>
                {activity === "open" ? "Opening" : "Reading"} {ticker} FY{fiscalYear}
              </h2>
              <p>
                {activity === "open"
                  ? "Loading the saved analysis and filing."
                  : "Locating the 10-K, retrieving XBRL facts, and searching the narrative. A full pass often takes a minute."}
              </p>
            </div>
          </section>
        )}

        {status === "error" && (
          <section className="error-panel" role="alert">
            <h2>Analysis failed</h2>
            <p>{error}</p>
            <p className="hint">
              Confirm the API key, SEC user agent, ticker, fiscal year, and that the API server is running.
            </p>
          </section>
        )}

        {showWorkspace && (
          <Workspace
            result={result}
            documentHtml={documentHtml}
            documentStatus={documentStatus}
            documentError={documentError}
          />
        )}

        {!showWorkspace && status !== "loading" && (
          <Landing
            documents={documents}
            documentsError={documentsError}
            selectedId={selectedId}
            onSelect={openDocument}
            onClear={() => setSelectedId(null)}
            messages={messages}
            chatStatus={chatStatus}
            onSend={sendQuestion}
            scopeLabel={scopeLabel}
          />
        )}
      </main>
    </div>
  );
}
