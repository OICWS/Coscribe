# 0046: A conversation offers a connector, and the person connects it

Status: proposed (2026-11-11, OICWS; the maintainer approved the plan in the project thread and
chose that the card opens the connector's page in Settings rather than connecting by itself). Adds to 0001 and 0004, which it does not change.
Part of #819 (step 6).

## Context
When a request needs a service the conversation can't reach (a Notion page, a Jira issue), the
model could only say so and leave the person to find Settings > Connectors, add the right
entry, sign in and ask again. The catalog already knows each hosted service and how to sign in
to it; what was missing is a way for the model to point at one, and for the person to connect
it without leaving the conversation.

## Decision
- **Two deferred tools** (`conversation/connector_offer.py`): `find_connector` searches the
  catalog by a few words and says each match's state; `offer_connector` puts a card in the
  chat for one catalog entry and returns at once. Both are read-only and changing data stays in
  their results, so the fixed tool list (0001) keeps its shape. The catalog stays in `web` and
  reaches the conversation as a `ConnectorDirectory`; the CLI has none and gets neither tool.
- **The card connects nothing itself.** Its button opens the connector's own page in Settings >
  Connectors, where the person reads what it is and does, and connects it as any connector is
  connected: in the person's own browser with OAuth 2.1 and PKCE (0004), with Sign in again for
  one whose sign-in stopped working and the guided setup for one that needs the person's own
  registered app (HubSpot, Google Workspace). There is one way to connect, so a new kind of
  connector changes Settings only. The model names a catalog entry and nothing else; a service
  outside the catalog gets no card, and the model says it can be added as a custom connector in
  Settings and never makes up an address.
- **A connection carries the conversation on, wherever it was made.** After any connector change
  hands the open conversations their new tools, each conversation with an open offer of a
  now-connected connector gets a note as a turn of its own, like a background task's report,
  within the same cap of turns without the person (`carry_on_offers` in
  `web/connector_directory.py`). Each offer wakes its conversation once; a connector nobody
  offered wakes nothing.
- **Not now holds for the conversation.** The model is told the person declined and is
  refused another offer of the same connector there; other conversations may still offer it.
- **No card in a workflow run**, where nobody is watching; the run names the connector in its
  result instead. A connector connected from the card gets the default permissions, as one
  added in Settings does.

## Consequences
- What each conversation was offered and declined is kept in `connector_offers.json` in the
  state directory, and dropped with the conversation.
- The card is drawn from `offer_connector`'s result, so a reload shows it again; it reads the
  connectors list to show a connection, and a Not now only until the tab reloads.
- A model may still do the work another way before the person connects (the tool's
  description asks it to stop); the note then lets it redo the work with the connector.
