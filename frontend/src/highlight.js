import { findBestMatch, normalizeForSearch } from "./locators.js";

function collectTextNodes(root) {
  const nodes = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (parent && ["SCRIPT", "STYLE", "NOSCRIPT"].includes(parent.tagName)) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  let current = walker.nextNode();
  while (current) {
    nodes.push(current);
    current = walker.nextNode();
  }
  return nodes;
}

function buildIndex(nodes) {
  let raw = "";
  const spans = [];
  nodes.forEach((node) => {
    const start = raw.length;
    raw += node.nodeValue;
    spans.push({ start, end: raw.length, node });
  });
  let normalized = "";
  const toRaw = [];
  let pendingSpace = false;
  for (let index = 0; index < raw.length; index += 1) {
    if (/\s/.test(raw[index])) {
      pendingSpace = normalized.length > 0;
      continue;
    }
    if (pendingSpace) {
      normalized += " ";
      toRaw.push(index);
      pendingSpace = false;
    }
    normalized += raw[index].toLowerCase();
    toRaw.push(index);
  }
  return { spans, normalized, toRaw };
}

function locate(spans, rawIndex) {
  for (const span of spans) {
    if (rawIndex < span.end) {
      return { node: span.node, offset: Math.max(0, rawIndex - span.start) };
    }
  }
  const last = spans[spans.length - 1];
  return { node: last.node, offset: last.node.nodeValue.length };
}

export function clearFilingHighlight() {
  if (typeof CSS !== "undefined" && CSS.highlights) {
    CSS.highlights.delete("filing-hit");
  }
}

function scrollRangeIntoView(range, scroller) {
  const rect = range.getBoundingClientRect();
  const bounds = scroller.getBoundingClientRect();
  const top = rect.top - bounds.top + scroller.scrollTop - scroller.clientHeight * 0.28;
  scroller.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

export function highlightInRoot(root, scroller, queries, keyword) {
  clearFilingHighlight();
  const nodes = collectTextNodes(root);
  if (!nodes.length) return false;
  const index = buildIndex(nodes);
  const match = findBestMatch(index.normalized, queries, keyword);
  if (!match) return false;
  const startRaw = index.toRaw[match.at];
  const endRaw = index.toRaw[match.at + match.length - 1] + 1;
  const range = document.createRange();
  range.setStart(locate(index.spans, startRaw).node, locate(index.spans, startRaw).offset);
  const end = locate(index.spans, endRaw);
  range.setEnd(end.node, end.offset);
  if (typeof CSS !== "undefined" && CSS.highlights && typeof Highlight !== "undefined") {
    CSS.highlights.set("filing-hit", new Highlight(range));
  }
  scrollRangeIntoView(range, scroller || root);
  return true;
}

export function normalizedDocumentText(text) {
  return normalizeForSearch(text);
}
