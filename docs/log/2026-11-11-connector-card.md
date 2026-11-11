# A conversation offers a connector on a card, and carries on once it is connected (shipped)

Why: a request that needed a service the conversation could not reach (a Notion page, a Jira
issue) ended with the model telling the person to go and set something up. Step 6 of the
agentic plan (#819). Decision 0046.

## Shipped
- Two deferred tools, `find_connector` and `offer_connector` (`conversation/connector_offer.py`):
  the first searches the Discover catalog by a few words and says each match's state, the second
  shows a card for one catalog entry. A workflow run gets no card; a connector declined in a
  conversation is not offered there again. The catalog reaches the conversation as a
  `ConnectorDirectory` (`web/connector_directory.py`); the CLI has none and no such tools.
- The card (`frontend/src/components/chatlog/ConnectorOfferCard.tsx`) is drawn from the tool's
  result. Connect, or Sign in again for a connector whose sign-in stopped working, opens that
  connector's own page in Settings > Connectors, where it is connected as any connector is; the
  card connects nothing itself. Not now is remembered for the conversation
  (`POST /api/threads/{id}/connector-offers/{name}/decline`).
- After any connector change hands the open conversations their tools, each conversation with an
  open offer of a now-connected connector gets "[Connector connected] ..." as a turn of its own,
  once (`carry_on_offers`), shown as one line in the chat; the model then uses the new tools.
- The deferred-tools note in the instructions names `find_connector` for a service no tool reaches.
- Eval task `12-offers-a-connector` (`evals/agentic/tasks.py`): on deepseek-flash it looked for a
  connector and offered Notion in 2 tool calls, $0.007.
- Checked live on deepseek-flash: Notion offered and its sign-in page opened from Settings; a
  signed-out Notion offered with Sign in again; Microsoft Learn connected in Settings, the card
  showed it, and the conversation carried on with `mslearn_microsoft_docs_search`.

## Not verified
- A finished OAuth sign-in from the card's flow (no Notion account here); the wake runs on the same
  refresh a finished sign-in calls, which the tests cover with a connector that needs none.
- The desktop app on Windows.

## Follow-ups
- Not now shows on the card only until the tab reloads; the server keeps it.
