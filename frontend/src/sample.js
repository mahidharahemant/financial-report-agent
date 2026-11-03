export const SAMPLE_HTML = `
<h1>Example Company</h1>
<p>Form 10-K for the fiscal year ended June 30, 2025.</p>
<h2>Item 1A. Risk Factors</h2>
<p>Our cloud services depend on data centers that may be disrupted by outages, cyberattacks, or regulatory changes.</p>
<h2>Item 7. Management's Discussion and Analysis</h2>
<p>We expect continued growth in commercial cloud demand over the next fiscal year.</p>
<table>
  <tr><th>Year Ended June 30,</th><th>2025</th><th>2024</th></tr>
  <tr><td>Revenue</td><td>$ 281,724</td><td>$ 245,122</td></tr>
  <tr><td>Operating income</td><td>128,528</td><td>109,433</td></tr>
  <tr><td>Net income</td><td>101,832</td><td>88,136</td></tr>
</table>
<p>Amounts are in millions.</p>
`;

export const SAMPLE_ANALYSIS = {
  company_name: "Example Company",
  ticker: "EXMP",
  fiscal_year: 2025,
  financial_metrics: [
    { name: "revenue", value: 281724000000, unit: "USD", fiscal_year: 2025 },
    { name: "operating_income", value: 128528000000, unit: "USD", fiscal_year: 2025 },
    { name: "net_income", value: 101832000000, unit: "USD", fiscal_year: 2025 },
  ],
  risk_factors: [
    {
      category: "Operations",
      description: "Cloud services can be interrupted by outages and cyberattacks.",
      supporting_evidence: "Our cloud services depend on data centers that may be disrupted by outages, cyberattacks, or regulatory changes.",
      source_section: "Item 1A. Risk Factors",
    },
  ],
  management_outlook: [
    "We expect continued growth in commercial cloud demand over the next fiscal year.",
  ],
  key_observations: ["Revenue is presented in millions in the annual table."],
  limitations: ["Sample filing used to show how a selected value is located in the document."],
};
