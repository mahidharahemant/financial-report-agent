import { useEffect, useRef, useState } from "react";
import { clearFilingHighlight, highlightInRoot } from "../highlight.js";
import { safeUrl } from "../format.js";

export default function DocumentPanel({
  html,
  status,
  error,
  selection,
  filingUrl,
}) {
  const scrollRef = useRef(null);
  const sheetRef = useRef(null);
  const [found, setFound] = useState(null);
  const originalUrl = safeUrl(filingUrl);

  useEffect(() => {
    const sheet = sheetRef.current;
    if (!sheet) return;
    sheet.innerHTML = html || "";
    clearFilingHighlight();
    setFound(null);
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [html]);

  useEffect(() => {
    const sheet = sheetRef.current;
    const scroller = scrollRef.current;
    if (!sheet || !selection) {
      clearFilingHighlight();
      setFound(null);
      return;
    }
    const match = highlightInRoot(sheet, scroller, selection.queries, selection.keyword);
    setFound(match);
  }, [html, selection]);

  let note = "Select a value on the right to locate it in the filing.";
  if (status === "loading") note = "Loading the filing…";
  else if (status === "error") note = error || "The filing could not be loaded.";
  else if (status === "missing") note = "This analysis did not include a filing URL.";
  else if (!html) note = "The filing will appear here.";
  else if (selection && found === true) note = "Highlighted in the filing.";
  else if (selection && found === false) note = "That passage was not found verbatim in the filing text.";

  return (
    <section className="document-panel" aria-label="Financial document">
      <header className="panel-bar">
        <div>
          <p className="eyebrow">Document</p>
          <h2>Filing</h2>
        </div>
        {originalUrl && (
          <a className="text-link" href={originalUrl} target="_blank" rel="noreferrer">
            Open original
          </a>
        )}
      </header>
      <p className="locate-note" role="status">{note}</p>
      <div className="document-scroll" ref={scrollRef}>
        {status === "loading" && <p className="empty-copy document-message">Fetching the 10-K from EDGAR.</p>}
        {status === "error" && <p className="empty-copy document-message">{error}</p>}
        <div className="filing-sheet" ref={sheetRef} />
      </div>
    </section>
  );
}
