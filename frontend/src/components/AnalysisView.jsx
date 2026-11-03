import {
  downloadJson,
  formatMetricValue,
  labelFor,
  safeUrl,
  textItems,
} from "../format.js";

function SourceLink({ href, children }) {
  const url = safeUrl(href);
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

function LocateButton({ id, activeId, onSelect, selectable, className, children }) {
  return (
    <button
      type="button"
      className={`${className || "locate-button"}${activeId === id ? " is-active" : ""}`}
      aria-pressed={activeId === id}
      disabled={!selectable}
      onClick={() => onSelect(id)}
    >
      {children}
    </button>
  );
}

export default function AnalysisView({ result, items, activeId, onSelect }) {
  const ticker = result.ticker || "Company";
  const year = result.fiscal_year ?? "";
  const company = result.company_name || ticker;
  const metrics = items.filter((item) => item.kind === "metric");
  const risks = items.filter((item) => item.kind === "risk");
  const outlook = items.filter((item) => item.kind === "outlook");
  const observations = items.filter((item) => item.kind === "observation");
  const limitations = textItems(result.limitations);

  return (
    <div className="results" aria-live="polite">
      <header className="panel-bar results-head">
        <div>
          <p className="eyebrow">Extracted</p>
          <h2>
            {company}
            <span>
              {ticker}
              {year !== "" ? ` · FY${year}` : ""}
            </span>
          </h2>
        </div>
        <button type="button" className="secondary" onClick={() => downloadJson(result)}>
          Download JSON
        </button>
      </header>
      <div className="extract-scroll">
        <p className="locate-note">Click a value to highlight its source in the filing.</p>

        {result.raw_analysis && (
          <section className="narrative-block">
            <h3>Narrative output</h3>
            <pre>{result.raw_analysis}</pre>
          </section>
        )}

        <section>
          <h3>Financial metrics</h3>
          {metrics.length === 0 ? (
            <p className="empty-copy">No structured financial metrics were returned.</p>
          ) : (
            <div className="metric-grid">
              {metrics.map((item) => {
                const display = formatMetricValue(item.metric);
                const unavailable = display === "Unavailable";
                return (
                  <article className="metric-card" key={item.id}>
                    <p className="metric-name">{labelFor(item.metric.name)}</p>
                    <LocateButton
                      id={item.id}
                      activeId={activeId}
                      onSelect={onSelect}
                      selectable={item.selectable && !unavailable}
                      className={unavailable ? "locate-button metric-value muted" : "locate-button metric-value"}
                    >
                      {display}
                    </LocateButton>
                    <p className="metric-meta">
                      {item.metric.fiscal_year ? `FY ${item.metric.fiscal_year}` : "Reported fact"}
                      {item.metric.unit && !unavailable ? ` · ${item.metric.unit}` : ""}
                    </p>
                    <SourceLink href={item.metric.source_url}>Source</SourceLink>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section>
          <h3>Risk factors</h3>
          {risks.length === 0 ? (
            <p className="empty-copy">No structured risk factors were returned.</p>
          ) : (
            <div className="risk-list">
              {risks.map((item, index) => (
                <details key={item.id} open={index === 0}>
                  <summary>{item.risk.category || "Risk"}</summary>
                  {item.risk.description && <p>{item.risk.description}</p>}
                  {item.risk.supporting_evidence && (
                    <LocateButton
                      id={item.id}
                      activeId={activeId}
                      onSelect={onSelect}
                      selectable={item.selectable}
                      className="locate-button quote-button"
                    >
                      {item.risk.supporting_evidence}
                    </LocateButton>
                  )}
                  <p className="metric-meta">{item.risk.source_section || "Filing section"}</p>
                </details>
              ))}
            </div>
          )}
        </section>

        <section>
          <h3>Management outlook</h3>
          {outlook.length === 0 ? (
            <p className="empty-copy">No management outlook items were returned.</p>
          ) : (
            <ul className="locate-list">
              {outlook.map((item) => (
                <li key={item.id}>
                  <LocateButton
                    id={item.id}
                    activeId={activeId}
                    onSelect={onSelect}
                    selectable={item.selectable}
                  >
                    {item.text}
                  </LocateButton>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3>Key observations</h3>
          {observations.length === 0 ? (
            <p className="empty-copy">No key observations were returned.</p>
          ) : (
            <ul className="locate-list">
              {observations.map((item) => (
                <li key={item.id}>
                  <LocateButton
                    id={item.id}
                    activeId={activeId}
                    onSelect={onSelect}
                    selectable={item.selectable}
                  >
                    {item.text}
                  </LocateButton>
                </li>
              ))}
            </ul>
          )}
        </section>

        {limitations.length > 0 && (
          <section className="limitations">
            <h3>Limitations</h3>
            <ul>
              {limitations.map((item, index) => (
                <li key={`${index}-${item}`}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        <details className="raw-json">
          <summary>Raw JSON output</summary>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </details>
      </div>
    </div>
  );
}
