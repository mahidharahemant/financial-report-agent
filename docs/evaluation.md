# Evaluation plan

Create a manually verified set of questions for at least two companies.

| Test case | Expected behavior | Measure |
|---|---|---|
| Revenue for a fiscal year | SEC-backed value, unit, period, source | Exact numeric match |
| Revenue growth | Calculate from two annual facts | Percentage-point error |
| Free cash flow | Operating cash flow less absolute capex | Exact numeric match |
| Risk question | Relevant filing passages with source | Human evidence review |
| Outlook question | Summarize management statements | Human factuality review |
| Unsupported ticker | Explain not found | Correct error handling |
| Missing XBRL tag | Return unavailable rather than guessing | Null handling |
| Prompt injection in filing text | Ignore document instructions | Adversarial test |

Do not report scores until the evaluation has actually been run.
