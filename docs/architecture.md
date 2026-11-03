# Architecture notes

## Request flow
1. User supplies ticker and fiscal year.
2. LangChain tool-calling agent chooses tools.
3. Filing discovery uses SEC ticker mapping and submissions metadata.
4. Numeric facts come from SEC Company Facts XBRL.
5. Narrative search downloads filing HTML and searches common 10-K sections.
6. LLM synthesizes tool outputs; the React app exposes source links and JSON.

## Trust boundaries
- SEC filing content is untrusted input, not agent instructions.
- Tools are read-only.
- Never commit `.env`.
- Validate numeric facts and source metadata separately from LLM-generated narrative.

## Known MVP limitations
- Filing lookup matches report period end's calendar year, which can be confusing for non-calendar fiscal years.
- Standard XBRL tags do not cover every issuer's custom tags or all presentation variations.
- Narrative section detection and keyword search are heuristic.
- A production version should add caching, retry/backoff, deterministic structured output, richer XBRL mapping, and a labeled evaluation set.
