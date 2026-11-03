import { normalizeMetrics, normalizeRisks, textItems } from "./format.js";

const KEYWORDS = [
  ["revenue growth", "revenue"],
  ["free cash", "cash"],
  ["operating cash", "cash"],
  ["capital expenditure", "property"],
  ["operating income", "operating income"],
  ["net income", "net income"],
  ["total assets", "total assets"],
  ["total liabilities", "total liabilities"],
  ["revenue", "revenue"],
  ["assets", "assets"],
  ["liabilities", "liabilities"],
];

export function normalizeForSearch(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

export function keywordFor(name) {
  const label = String(name || "").replace(/_/g, " ").toLowerCase();
  for (const [needle, keyword] of KEYWORDS) {
    if (label.includes(needle)) return keyword;
  }
  return label;
}

export function metricLocators(metric) {
  const numeric = typeof metric?.value === "number"
    ? metric.value
    : Number(String(metric?.value ?? "").replace(/,/g, ""));
  if (!Number.isFinite(numeric)) {
    const text = String(metric?.value ?? "").trim();
    return text.length >= 4 ? [text] : [];
  }
  const formats = new Set();
  for (const scale of [1, 1_000, 1_000_000, 1_000_000_000]) {
    const scaled = numeric / scale;
    const nearest = Math.round(scaled);
    if (Math.abs(scaled - nearest) > 0.01) continue;
    if (scale !== 1 && Math.abs(nearest) < 10) continue;
    formats.add(nearest.toLocaleString("en-US"));
    formats.add(String(nearest));
    if (nearest < 0) formats.add(`(${Math.abs(nearest).toLocaleString("en-US")})`);
  }
  return [...formats].filter((item) => item.replace(/[(),-]/g, "").length >= 3);
}

export function quoteQueries(text) {
  const cleaned = String(text || "").replace(/\s+/g, " ").trim();
  if (cleaned.length < 12) return [];
  const queries = [cleaned];
  const sentence = cleaned.split(/(?<=[.!?])\s/)[0];
  if (sentence && sentence.length >= 24 && sentence !== cleaned) queries.push(sentence);
  if (cleaned.length > 180) queries.push(cleaned.slice(0, 180));
  return queries;
}

export function findBestMatch(normalizedDoc, queries, keyword) {
  const keywordNorm = keyword ? normalizeForSearch(keyword) : "";
  const ordered = [...new Set(queries.map((query) => normalizeForSearch(query)))]
    .filter((query) => query.length >= 4)
    .sort((left, right) => right.length - left.length);
  let fallback = null;
  for (const query of ordered) {
    let from = 0;
    while (from < normalizedDoc.length) {
      const at = normalizedDoc.indexOf(query, from);
      if (at === -1) break;
      const before = normalizedDoc.slice(Math.max(0, at - 240), at);
      if (keywordNorm && before.includes(keywordNorm)) {
        return { at, length: query.length };
      }
      if (!fallback) fallback = { at, length: query.length };
      if (!keywordNorm) return fallback;
      from = at + query.length;
    }
  }
  return fallback;
}

export function extractItems(result) {
  const items = [];
  normalizeMetrics(result?.financial_metrics).forEach((metric, index) => {
    const queries = metricLocators(metric);
    items.push({
      id: `metric-${index}`,
      kind: "metric",
      metric,
      queries,
      keyword: keywordFor(metric.name),
      selectable: queries.length > 0,
    });
  });
  normalizeRisks(result?.risk_factors).forEach((risk, index) => {
    const evidence = risk.supporting_evidence || risk.description || "";
    const queries = quoteQueries(evidence);
    items.push({
      id: `risk-${index}`,
      kind: "risk",
      risk,
      queries,
      keyword: "",
      selectable: queries.length > 0,
    });
  });
  textItems(result?.management_outlook).forEach((text, index) => {
    const queries = quoteQueries(text);
    items.push({
      id: `outlook-${index}`,
      kind: "outlook",
      text,
      queries,
      keyword: "",
      selectable: queries.length > 0,
    });
  });
  textItems(result?.key_observations).forEach((text, index) => {
    const queries = quoteQueries(text);
    items.push({
      id: `observation-${index}`,
      kind: "observation",
      text,
      queries,
      keyword: "",
      selectable: queries.length > 0,
    });
  });
  return items;
}
