import type { FolderAccessRequiredEvent } from "../types/wire";
import { closeStreamingBubble, type ChatAction, type ChatState, type LogItem } from "./reducer";

/** A folder outside the workspace the model asked for (decision 0048), until the person answers. */
export interface FolderAccessItem {
  id: string;
  kind: "folder_access";
  folder: string;
  access: FolderAccessRequiredEvent["access"];
  reason: string;
  status: "pending" | "answered";
  /** As sent: "allow:<access>", "chat:<access>", "workspace" or "deny". */
  answer?: string;
  /** What the person wrote in the chat instead of choosing. */
  reply?: string;
}

export type FolderAccessAction = { type: "local_folder_access_answered"; id: string; answer: string; reply?: string };

export type FolderAccessEvent = FolderAccessRequiredEvent | FolderAccessAction;

export const isFolderAccessEvent = (action: ChatAction): action is FolderAccessEvent =>
  action.type === "folder_access_required" || action.type === "local_folder_access_answered";

export function reduceFolderAccess(state: ChatState, action: FolderAccessEvent): ChatState {
  if (action.type === "folder_access_required") {
    // A tab that reconnects is sent the same card again.
    if (state.items.some((item) => item.id === action.id)) return state;
    const { id, folder, access, reason } = action;
    const item: FolderAccessItem = { id, kind: "folder_access", folder, access, reason, status: "pending" };
    return { ...state, items: [...closeStreamingBubble(state.items), item] };
  }
  const answered = (item: LogItem): LogItem =>
    item.kind === "folder_access" && item.id === action.id ? { ...item, status: "answered", answer: action.answer, reply: action.reply } : item;
  return { ...state, items: state.items.map(answered) };
}

/** A question or folder card waits for the person: the turn is stuck on it. */
export const asksThePerson = (item: LogItem): boolean =>
  (item.kind === "question" || item.kind === "folder_access") && item.status === "pending";
