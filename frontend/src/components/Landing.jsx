import { useState } from "react";

export default function Landing({
  documents,
  documentsError,
  selectedId,
  onSelect,
  onClear,
  messages,
  chatStatus,
  onSend,
  scopeLabel,
}) {
  const [draft, setDraft] = useState("");
  const busy = chatStatus === "loading";

  function send(event) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || busy) return;
    setDraft("");
    onSend(question);
  }

  return (
    <div className="landing">
      <section className="landing-pane" aria-label="Processed documents">
        <div className="landing-head">
          <h2>Processed documents</h2>
          {selectedId != null && (
            <button type="button" className="chip" onClick={onClear}>
              All documents
            </button>
          )}
        </div>
        {documentsError && <p className="field-error">{documentsError}</p>}
        {documents.length === 0 && !documentsError && (
          <p className="empty-copy">No documents have been processed.</p>
        )}
        <div className="document-list">
          {documents.map((document) => (
            <button
              key={document.id}
              type="button"
              className="document-row"
              aria-pressed={document.id === selectedId}
              onClick={() => onSelect(document.id)}
            >
              <strong>{document.company_name || document.ticker}</strong>
              <span>
                {document.ticker} · FY{document.fiscal_year}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="landing-pane chat-pane" aria-label="Document chat">
        <div className="landing-head">
          <h2>Ask about the filings</h2>
          <p>Asking about {scopeLabel}</p>
        </div>
        <div className="chat-log" aria-live="polite">
          {messages.length === 0 && (
            <p className="empty-copy">Ask a question about the selected filing, or about every processed filing.</p>
          )}
          {messages.map((message, index) => (
            <p key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
              {message.text}
            </p>
          ))}
        </div>
        <form className="chat-form" onSubmit={send}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="What was revenue?"
            disabled={busy}
            rows={2}
          />
          <button className="primary" type="submit" disabled={busy || !draft.trim()}>
            {busy ? "Answering…" : "Send"}
          </button>
        </form>
      </section>
    </div>
  );
}
