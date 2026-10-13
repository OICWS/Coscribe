# ConnectorsTab split into settings/connectors/ (shipped)

Why: `office-agent/frontend/src/components/settings/ConnectorsTab.tsx` was 1,369 lines holding eight sub-views and the helpers they share, so any change to one connector screen meant reading and diffing the whole file (#167, part 1 of 3).

## Shipped
- `components/settings/ConnectorsTab.tsx` (now 405 lines) keeps its name and export and is the composition: state, the connector actions, and the list.
- `components/settings/connectors/` holds one file per sub-view (`ConnectorDetail`, `CatalogConnectorPage`, `DiscoverCard`, `AddCustomConnectorDialog`, `ConnectorMenu`, `ToolPolicies`, `NoticeText`, `SecretPicker`, `StatusCell`) and the pieces without JSX: `helpers.ts`, `types.ts`, `pending.ts`.
- Moves only. A check of the sorted multiset of lines before and after shows only imports and `export` keywords added. The one edit that is not a cut and paste: the pending-add listener list was reassigned from the component, which an importing module cannot do, so `pending.ts` exposes `subscribePendingChanged` and the component calls it.
- `helpers.test.ts` (16 tests, vitest) for the pure helpers that had none: pinned npm package detection, env and header line parsing, host patterns, secret problems, caret insertion, row building. Each assertion was checked by breaking the line it protects.
- Seven views (list, a connector's page, the Add menu, both Add dialogs, Discover, a catalog page) rendered before and after at 1280x860 are pixel-identical (image difference empty).
- Playwright specs `connectors`, `connector-setup`, `settings` and `secrets` pass against the stub model on the branch.

## Not verified
- The desktop app on Windows (the maintainer looks).

## Follow-ups
- `SkillsTab` and `ChatLog` are parts 2 and 3 of #167.
- `hostAllowed` has a guard (`lower !== pattern.slice(2)`) that no input can reach, because `"b.com".endsWith(".b.com")` is already false. Left as is in a pure move.
