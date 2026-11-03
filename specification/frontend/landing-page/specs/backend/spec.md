# Delta for Backend

## ADDED Requirements

### Requirement: Processed-document catalog

When an analysis completes, the system MUST record the company name, ticker, fiscal year, filing URL, local filing file, and processed time. A later analysis of the same ticker and fiscal year MUST update that record rather than add a second one. The system SHOULD add a record for a filing already stored when the ticker and fiscal year can be determined.

#### Scenario: Analysis is recorded

- GIVEN no catalog record exists for MSFT 2025
- WHEN analysis of MSFT for 2025 completes
- THEN the catalog contains MSFT, fiscal year 2025, the filing URL, and a processed time

#### Scenario: Repeat analysis updates one record

- GIVEN a catalog record exists for MSFT 2025
- WHEN that analysis completes again
- THEN one MSFT 2025 record remains and its processed time is the later completion

### Requirement: Document list

The system MUST return the catalog with an identifier, company name, ticker, fiscal year, and filing URL for each document. The most recently processed document MUST come first. An empty catalog MUST return an empty list.

#### Scenario: Two processed documents

- GIVEN AAPL 2024 and MSFT 2025 are catalogued and MSFT was processed later
- WHEN the client requests the document list
- THEN MSFT 2025 is first and both identifiers are present

#### Scenario: Nothing processed

- GIVEN the catalog has no records
- WHEN the client requests the document list
- THEN the result is an empty list

### Requirement: Document chat

The system MUST accept a natural-language question and an optional document identifier. With an identifier, the answer MUST use only that document's saved analysis and filing. Without an identifier, the question MUST apply to every catalogued document. The system MUST look up the exact question prompt before calling the model. A stored prompt MUST return the stored reply and MUST NOT call the model. An unknown identifier MUST be rejected. The reply MUST NOT give investment advice.

#### Scenario: Question about one document

- GIVEN MSFT 2025 is catalogued
- WHEN the client asks for its main risk and includes that document identifier
- THEN the reply uses that document's saved analysis and does not download the filing again

#### Scenario: Repeated question

- GIVEN the same question and document were answered before
- WHEN the client sends that question again
- THEN the stored reply is returned and the model is not called

#### Scenario: Unknown document

- GIVEN the document identifier is not in the catalog
- WHEN the client asks a question with that identifier
- THEN the request is rejected and the model is not called

#### Scenario: Question across documents

- GIVEN two catalogued documents and no identifier is sent
- WHEN the client asks which company reported higher revenue
- THEN the reply uses the saved analyses of both documents

## MODIFIED Requirements

None.

## REMOVED Requirements

None.
