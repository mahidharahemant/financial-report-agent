# Delta for Frontend

## ADDED Requirements

### Requirement: Processed-document list

The landing page MUST show processed documents in a left pane. Each row MUST show the company or ticker and the fiscal year, and MUST be selectable. The list MUST come from the document catalog, with the most recently processed document first. An empty catalog MUST say that no documents have been processed. Selecting a row MUST scope the next question to that document. The user MUST be able to clear the selection so the next question applies to every processed document.

#### Scenario: Documents are listed

- GIVEN the catalog returns MSFT 2025 and AAPL 2024, with MSFT processed later
- WHEN the landing page opens
- THEN both documents appear in the left pane and MSFT 2025 is first

#### Scenario: Empty catalog

- GIVEN the catalog returns no documents
- WHEN the landing page opens
- THEN the left pane says no documents have been processed and the chat composer stays usable

#### Scenario: Select and clear

- GIVEN the list shows MSFT 2025
- WHEN the user selects that row and then clears the selection
- THEN the chat first names MSFT 2025 and then names all processed documents

### Requirement: Chat

The right pane MUST show the conversation and a composer for a natural-language question. Sending a question MUST show the user's message and then the reply. A blank question MUST NOT be sent. While a reply is in progress, the composer MUST be disabled. A failed reply MUST show the error and MUST keep the question and earlier messages. The pane MUST say whether the question applies to the selected document or to all processed documents.

#### Scenario: Ask about the selection

- GIVEN MSFT 2025 is selected
- WHEN the user asks "What was revenue?"
- THEN the thread shows that question and the reply for MSFT 2025

#### Scenario: Blank composer

- GIVEN the composer is blank
- WHEN the user tries to send
- THEN no chat request is made and the thread is unchanged

#### Scenario: Chat failure

- GIVEN the chat request fails
- WHEN the response arrives
- THEN the thread shows the error and the question remains visible

## MODIFIED Requirements

### Requirement: Empty start

Before a filing workspace is open, the page MUST show the processed-document list on the left and the chat on the right. The page MUST still offer the ticker and fiscal-year form. It MUST state that the prototype is educational and is not investment advice. The user MUST be able to return from the filing workspace to this landing page.

(Previously: the first screen showed the form and three capability descriptions, and neither panel was shown.)

#### Scenario: First visit

- GIVEN no filing workspace is open
- WHEN the page is shown
- THEN the document list and the chat composer are visible

#### Scenario: Return from an analysis

- GIVEN the filing workspace is open
- WHEN the user returns to the landing page
- THEN the document list and the chat are shown again

## REMOVED Requirements

None.
