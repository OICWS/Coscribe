import { createContext, type Dispatch } from "react";
import type { ChatAction } from "../state/reducer";
import type { WsClientMessage } from "../types/wire";

/** What the folder and package cards can do (a refused script write, a folder or a package the
 * model asked for): the folders the conversation has, and how to change them. Unset outside a
 * chat, where no card is shown. */
export interface FolderActions {
  folders: string[];
  /** A reply is being generated; folders can't change meanwhile. */
  busy: boolean;
  onAddFolder: (folder: string) => void;
  onTryAgain: () => void;
  /** Answers a folder access card: "allow:<access>", "chat:<access>", "workspace" or "deny". */
  onAnswerFolderAccess: (id: string, answer: string) => void;
  onOpenFolderSettings?: () => void;
  /** Answers a package install card: "install" or "decline". */
  onAnswerPackageInstall: (id: string, answer: string) => void;
}

export const FolderActionsContext = createContext<FolderActions | null>(null);

/** The folder and package cards' answers: shown answered at once, then sent to the server. */
export function cardAnswers(dispatch: Dispatch<ChatAction>, send: (message: WsClientMessage) => void) {
  const answer = (type: "local_folder_access_answered" | "local_package_install_answered") => (id: string, value: string) => {
    dispatch({ type, id, answer: value });
    send({ type: "question_response", id, answer: value });
  };
  return { onAnswerFolderAccess: answer("local_folder_access_answered"), onAnswerPackageInstall: answer("local_package_install_answered") };
}
