# The connector Connect button shows only a spinner while connecting (shipped)

Why: clicking Connect on a Discover connector turned the button white with a blue focus ring and
printed "Connecting -- a first install can take a minute or more." under it. The dark button with
a turning spinner is calmer and matches the other pending states.

## Shipped
- `CatalogConnectorPage.tsx`: while pending, the Connect button keeps its dark fill and shows a
  spinner only (no wave ring, no label; `aria-label="Connecting"`).
- `ConnectorsTab.tsx`: starting an add no longer sets the "first install can take a minute" notice.

## Not verified
- Light and dark screenshots of the pending state; only `npm run build` ran here.
