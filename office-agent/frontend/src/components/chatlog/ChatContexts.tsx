import { useMemo, type ReactNode } from "react";
import { filesByName } from "../../lib/fileMentions";
import { type LogItem } from "../../state/reducer";
import { DraftCardsContext, type DraftCards } from "../workflow/draftCards";
import { FolderActionsContext, type FolderActions } from "../folderActions";
import { ConnectorOfferContext, type ConnectorOfferActions } from "../connectorOffers";
import { openConnectorOfferId } from "../../lib/transcriptGrouping";
import { ConnectorTools, ThreadFiles } from "./contexts";

/** What the transcript's parts read from their surroundings: the connectors' tools, the folder
 * and connector-card actions, the draft cards' state, and the files this conversation made (for
 * chips in a reply). */
export function ChatContexts({
  connectorTools,
  folderActions,
  connectorOffers,
  cards,
  items,
  olderItems,
  children,
}: {
  connectorTools: ReadonlySet<string>;
  folderActions: FolderActions | null;
  connectorOffers: Omit<ConnectorOfferActions, "openId"> | null;
  cards: DraftCards;
  items: LogItem[];
  olderItems: LogItem[];
  children: ReactNode;
}) {
  const files = useMemo(
    () => filesByName([...olderItems, ...items].flatMap((item) => (item.kind === "tool" || item.kind === "approval" ? [item] : []))),
    [items, olderItems],
  );
  const openId = useMemo(() => openConnectorOfferId(items), [items]);
  const offers = useMemo(() => (connectorOffers ? { ...connectorOffers, openId } : null), [connectorOffers, openId]);
  return (
    <ConnectorTools.Provider value={connectorTools}>
      <ThreadFiles.Provider value={files}>
        <FolderActionsContext.Provider value={folderActions}>
          <ConnectorOfferContext.Provider value={offers}>
            <DraftCardsContext.Provider value={cards}>{children}</DraftCardsContext.Provider>
          </ConnectorOfferContext.Provider>
        </FolderActionsContext.Provider>
      </ThreadFiles.Provider>
    </ConnectorTools.Provider>
  );
}
