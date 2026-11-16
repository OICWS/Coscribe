import { createContext } from "react";

/** What the folder cards can do (a refused script write, a folder the model asked for): the
 * folders the conversation has, and how to change them. Unset outside a chat, where no card is
 * shown. */
export interface FolderActions {
  folders: string[];
  /** A reply is being generated; folders can't change meanwhile. */
  busy: boolean;
  onAddFolder: (folder: string) => void;
  onTryAgain: () => void;
  /** Answers a folder access card: "allow:<access>", "chat:<access>", "workspace" or "deny". */
  onAnswerFolderAccess: (id: string, answer: string) => void;
  onOpenFolderSettings?: () => void;
}

export const FolderActionsContext = createContext<FolderActions | null>(null);
