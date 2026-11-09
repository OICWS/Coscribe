# A conversation offers a connector on a card; only the person connects it (shipped)

Why: when a job needed a service that wasn't connected (Notion pages, Jira issues, a Gmail draft),
the model could only say "connect it in Settings", and the person had to find it, sign in and ask
again. Step 6 of #819; decision 0041.

## Shipped
- `suggest_connector(name, reason)` (`conversation/connector_offer.py`), a deferred tool that
  accepts only a built-in catalog entry. It refuses one already added, one offered before in the
  conversation (read from its history) and any offer in a scheduled run.
- `search_tools` lists the catalog entries that fit a search and aren't added, under `found`
  beside the tool, through a new `ToolMetadata.search_hint`. The tool list and prompt are unchanged.
- The card under the call (`ConnectorOfferCard.tsx`): Connect adds the entry as Settings does and
  the person signs in in their own browser; an entry that needs a one-time setup opens its page in
  Settings. Once connected, or on Not now, it sends a message as the person, and the next turn has
  the tools (#854's rebuild on use).
- Tests: `tests/web/test_connector_offer.py`, `transcriptGrouping.test.ts`, e2e
  `connector-offer.spec.ts` (Not now; Connect with the add and server list answered in the page).

## Not verified
- A real service's sign-in from the card (needs an account), and the browser opening from the
  card in the Windows desktop app.
- Whether models call it unprompted; not yet in the agentic evaluation.

## Follow-ups
- An eval case in `office-agent/evals/agentic/` for a request that needs a missing connector.
