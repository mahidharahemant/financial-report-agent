function errorMessage(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item?.msg === "string" ? item.msg : ""))
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  return fallback;
}

export async function checkHealth() {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error("Analysis API is unavailable.");
  return response.json();
}

export async function analyzeCompany(ticker, fiscalYear) {
  let response;
  try {
    response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker,
        fiscal_year: Number(fiscalYear),
      }),
    });
  } catch {
    throw new Error("Could not reach the analysis API. Start it on port 8000 and try again.");
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(payload, "Analysis failed."));
  }
  return payload;
}

export async function listDocuments() {
  let response;
  try {
    response = await fetch("/api/documents");
  } catch {
    throw new Error("Could not reach the analysis API. Start it on port 8000 and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(payload, "The document list could not be loaded."));
  }
  return Array.isArray(payload.documents) ? payload.documents : [];
}

export async function fetchDocument(documentId) {
  let response;
  try {
    response = await fetch(`/api/documents/${documentId}`);
  } catch {
    throw new Error("Could not reach the analysis API. Start it on port 8000 and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(payload, "The saved document could not be opened."));
  }
  return payload;
}

export async function askQuestion(question, documentId, history = []) {
  let response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        document_id: documentId,
        history,
      }),
    });
  } catch {
    throw new Error("Could not reach the analysis API. Start it on port 8000 and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(payload, "The question could not be answered."));
  }
  return payload;
}

export async function fetchFiling(url) {
  let response;
  try {
    response = await fetch(`/api/filing?url=${encodeURIComponent(url)}`);
  } catch {
    throw new Error("Could not reach the analysis API to load the filing.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(errorMessage(payload, "The filing could not be loaded."));
  }
  return payload.html || "";
}
