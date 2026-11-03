export function safeUrl(url) {
  if (typeof url !== "string") return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") return parsed.href;
  } catch {
    return null;
  }
  return null;
}

export function labelFor(name) {
  if (!name) return "Metric";
  return String(name)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function textItems(value) {
  const list = Array.isArray(value) ? value : value == null ? [] : [value];
  return list
    .map((item) => {
      if (typeof item === "string") return item.trim();
      if (item && typeof item === "object") {
        const text = item.summary || item.text || item.description || item.statement;
        return String(text || "").trim() || JSON.stringify(item);
      }
      if (item == null) return "";
      return String(item);
    })
    .filter(Boolean);
}

export function normalizeMetrics(metrics) {
  if (!metrics) return [];
  if (Array.isArray(metrics)) {
    return metrics.map((item, index) => {
      if (item && typeof item === "object") {
        return { ...item, name: item.name || `Metric ${index + 1}` };
      }
      return { name: `Metric ${index + 1}`, value: item };
    });
  }
  if (typeof metrics === "object") {
    return Object.entries(metrics).map(([name, value]) => {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        return { ...value, name: value.name || name };
      }
      return { name, value };
    });
  }
  return [];
}

export function normalizeRisks(risks) {
  if (!Array.isArray(risks)) return [];
  return risks.map((risk) => {
    if (typeof risk === "string") return { category: "Risk", description: risk };
    if (risk && typeof risk === "object") return risk;
    return { category: "Risk", description: String(risk) };
  });
}

export function formatMetricValue(metric) {
  const value = metric?.value;
  if (value === null || value === undefined || value === "") return "Unavailable";
  const numeric = typeof value === "number" ? value : Number(String(value).replace(/,/g, ""));
  if (!Number.isFinite(numeric)) return String(value);

  const unit = String(metric.unit || "").toLowerCase();
  const name = String(metric.name || "").toLowerCase();
  const percent =
    unit.includes("percent") || unit === "pct" || unit === "%" || name.includes("growth");
  if (percent) {
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(numeric)}%`;
  }
  if (unit === "usd" || unit === "dollars" || unit.includes("usd")) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(numeric);
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(numeric);
}

export function downloadJson(result) {
  const ticker = result?.ticker || "company";
  const year = result?.fiscal_year || "year";
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `analysis_${ticker}_${year}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
