import { useMemo, useState } from "react";
import AnalysisView from "./AnalysisView.jsx";
import DocumentPanel from "./DocumentPanel.jsx";
import { extractItems } from "../locators.js";

export default function Workspace({ result, documentHtml, documentStatus, documentError }) {
  const [activeId, setActiveId] = useState(null);
  const items = useMemo(() => extractItems(result), [result]);
  const selection = items.find((item) => item.id === activeId) || null;

  return (
    <div className="workspace">
      <DocumentPanel
        html={documentHtml}
        status={documentStatus}
        error={documentError}
        selection={selection}
        filingUrl={result.filing_url}
      />
      <section className="extract-panel" aria-label="Extracted data">
        <AnalysisView
          result={result}
          items={items}
          activeId={activeId}
          onSelect={setActiveId}
        />
      </section>
    </div>
  );
}
