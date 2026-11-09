# 0041: The model offers a connector in the chat; only the person connects it

Status: proposed (2026-11-09, OICWS; agreed with the maintainer in the project thread). Keeps
0004 (sign-in once, in the person's own browser) as it is. Part of #819.

## Context
When a job needs a service that isn't connected (Notion pages, Jira issues, a Gmail draft), the
model could only write "connect it in Settings": the person had to find the connector, sign in,
and ask again.

## Decision
- **One fixed tool, `suggest_connector(name, reason)`**, deferred like the others. `name` must be
  an entry of the built-in catalog, so the model can't point the person at any other server or
  page. It never connects anything and takes no address.
- **`search_tools` names the catalog entries that match the search and aren't added yet**, beside
  its usual matches, as part of its result; where every tool is bound and there is no
  `search_tools`, a need given as the name ("jira") gets the entries that fit. The tool list and
  the prompt stay the same for every conversation.
- **The offer is a card under the call**, from the call's own result, so it stays after a reload:
  the service, the model's reason as plain text, Connect and Not now. Connect does what Settings >
  Connectors does: it adds the entry and the person signs in in their own browser. An entry that
  needs a one-time app setup opens its page in Settings instead.
- **The turn ends at the card**: a conversation's tools are bound when its agent is built, so the
  model is told to stop there. Once the connector is connected, or the person says Not now, the
  card sends a message as the person, and the next turn has the new tools (its agent is rebuilt
  on use).
- **Once per connector per conversation**: a second offer of the same entry is refused from the
  conversation's own history (an offer compaction summarized away can come again). In a scheduled
  run's own conversation, where nobody can click, the tool says so and nothing is shown; a wake-up
  in a person's conversation shows the card for when they come back.

## Consequences
- The model can bring the person to the right connector in one click; what it may reach is still
  only what the person connected and signed in to.
- The offer is not in the audit log (it changes nothing); adding the connector is the same
  request as in Settings.
- Out of scope: custom connectors, connecting from a run's notification.
