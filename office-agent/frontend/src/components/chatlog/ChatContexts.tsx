import { useMemo, type ReactNode } from "react";
import { filesByName } from "../../lib/fileMentions";
import { type LogItem } from "../../state/reducer";
import { DraftCardsContext, type DraftCards } from "../workflow/draftCards";
import { FolderActionsContext, type FolderActions } from "../folderActions";
import { ConnectorTools, ThreadFiles } from "./contexts";

/** What the transcript's parts read from their surroundings: the connectors' tools, the folder
 * actions, the draft cards' state, and the files this conversation made (for chips in a reply). */
export function ChatContexts({
  connectorTools,
  folderActions,
  cards,
  items,
  olderItems,
  children,
}: {
  connectorTools: ReadonlySet<string>;
  folderActions: FolderActions | null;
  cards: DraftCards;
  items: LogItem[];
  olderItems: LogItem[];
  children: ReactNode;
}) {
  const files = useMemo(
    () => filesByName([...olderItems, ...items].flatMap((item) => (item.kind === "tool" || item.kind === "approval" ? [item] : []))),
    [items, olderItems],
  );
  return (
    <ConnectorTools.Provider value={connectorTools}>
      <ThreadFiles.Provider value={files}>
        <FolderActionsContext.Provider value={folderActions}>
          <DraftCardsContext.Provider value={cards}>{children}</DraftCardsContext.Provider>
        </FolderActionsContext.Provider>
      </ThreadFiles.Provider>
    </ConnectorTools.Provider>
  );
}
