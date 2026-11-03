# Frontend Specification

## Purpose

The React page collects a ticker and fiscal year, shows the 10-K on the left, and shows the extracted analysis on the right. A selected value is located in the filing when the filing contains that amount or a verbatim passage.

## Requirements

### Requirement: Analysis request

The page MUST offer a ticker, a fiscal year, and an action to analyze the annual report. The ticker MUST be a letter followed by at most 11 letters, digits, dots, or hyphens. The fiscal year MUST be an integer from 1994 through 2100. Invalid input MUST be explained on the form and MUST NOT be submitted. A valid request MUST post the ticker and fiscal year to the analysis API. Example chips MUST fill the form and MUST NOT start analysis by themselves.

#### Scenario: Valid submission

- GIVEN the ticker is MSFT and the year is 2025
- WHEN the user analyzes the annual report
- THEN the page sends that ticker and year and shows a busy state until the API returns

#### Scenario: Invalid ticker

- GIVEN the ticker is 123
- WHEN the user submits
- THEN the page asks for a ticker such as MSFT or BRK.B and does not call the API

### Requirement: API status and failures

On load, the page MUST check API health. If the API is down, it MUST say how to start it and still let the user submit. A failed analysis MUST show the server message and MUST keep the form usable. While a request is running, the analyze action and example chips MUST be disabled.

#### Scenario: API not running

- GIVEN `/api/health` cannot be reached
- WHEN the page loads
- THEN a banner tells the user to start the API on port 8000

#### Scenario: Analysis error

- GIVEN the API rejects the analysis
- WHEN the response arrives
- THEN the page shows the error and leaves the previous result hidden until the next success

### Requirement: Two-panel result

After a successful analysis, the page MUST show the financial document on the left and the extracted data on the right. The request form MUST remain available in a compact bar. The extracted panel MUST show company, ticker, fiscal year, metrics, risk factors, management outlook, key observations, limitations, and raw JSON. A download action MUST save the analysis JSON. On a viewport at or below 800 pixels, the panels MUST stack.

#### Scenario: Completed analysis

- GIVEN the API returns a company analysis with a filing URL
- WHEN the result is shown
- THEN the left panel loads that filing and the right panel lists the returned metrics and narrative items

#### Scenario: Narrow viewport

- GIVEN the result is visible and the viewport width is 800 pixels or less
- WHEN the page lays out
- THEN the filing panel is above the extracted-data panel

### Requirement: Filing display

The left panel MUST render the sanitized filing HTML from `/api/filing` when `filing_url` is present. It MUST show a loading state while the document is fetched and the server error if the fetch fails. If the analysis has no filing URL, it MUST say the filing URL is missing. The panel MUST link to the original SEC URL when that URL is http or https.

#### Scenario: Filing loads

- GIVEN the analysis includes an SEC filing URL
- WHEN the workspace opens
- THEN the left panel shows the filing text and tables returned by the filing API

#### Scenario: Filing request fails

- GIVEN the filing API returns an error
- WHEN the document load finishes
- THEN the left panel shows that error and does not invent filing text

### Requirement: Locate a value in the filing

Clicking an extracted metric, risk quotation, outlook item, or observation MUST search the filing. Metric search MUST try the exact amount and whole-number forms in thousands, millions, and billions, and SHOULD prefer a match near the metric name. Quote search MUST use the passage, its first sentence, and a shorter prefix when the passage is long. A match MUST be highlighted and scrolled into view inside the left panel. Only one highlight is active. If no match of at least four characters is found, the page MUST clear any highlight and say the passage was not found verbatim.

#### Scenario: Revenue printed in millions

- GIVEN the filing table prints Revenue as 281,724 and the metric value is 281724000000 dollars
- WHEN the user clicks the revenue value
- THEN 281,724 is highlighted in the revenue row and scrolled into view

#### Scenario: Verbatim risk evidence

- GIVEN the risk's supporting evidence appears in the filing
- WHEN the user clicks that quotation
- THEN the same sentence is highlighted

#### Scenario: Paraphrased observation

- GIVEN the observation text does not appear in the filing
- WHEN the user clicks it
- THEN no filing text stays highlighted and the left panel says the passage was not found

### Requirement: Sample filing

The page MUST offer a sample filing that shows the two panels and working highlights without calling the analysis or filing APIs.

#### Scenario: Open the sample

- GIVEN the user has not run an analysis
- WHEN the user chooses Sample filing
- THEN the example company document and extracted values appear, and no analysis request is sent

### Requirement: Empty start

Before the first result, the page MUST explain that the agent finds the 10-K, reads XBRL facts, and searches the narrative. It MUST state that the prototype is educational and is not investment advice.

#### Scenario: First visit

- GIVEN no analysis has completed
- WHEN the page is shown
- THEN the form and the three capability descriptions are visible and neither panel is shown
