import type { PackageInstallFinishedEvent, PackageInstallRequiredEvent } from "../types/wire";
import type { ChatAction, ChatState, LogItem } from "./reducer";
import { closeStreamingBubble } from "./streamingBubble";

/** A package a script needs, asked for from the chat (decision 0056), from the card to the install's end. */
export interface PackageInstallItem {
  id: string;
  kind: "package_install";
  runtime: PackageInstallRequiredEvent["runtime"];
  package: string;
  name: string;
  reason: string;
  installedVersion: string | null;
  status: "pending" | "installing" | "installed" | "failed" | "declined";
  version?: string | null;
  error?: string;
  /** What the person wrote in the chat instead of choosing. */
  reply?: string;
}

export const PACKAGE_INSTALL = "install";
export const PACKAGE_DECLINE = "decline";

export type PackageInstallAction = { type: "local_package_install_answered"; id: string; answer: string; reply?: string };

type PackageInstallEvent = PackageInstallRequiredEvent | PackageInstallFinishedEvent | PackageInstallAction;

export const isPackageInstallEvent = (action: ChatAction): action is PackageInstallEvent =>
  action.type === "package_install_required" || action.type === "package_install_finished" || action.type === "local_package_install_answered";

export function reducePackageInstall(state: ChatState, action: PackageInstallEvent): ChatState {
  if (action.type === "package_install_required") {
    // A tab that reconnects is sent the same card again.
    if (state.items.some((item) => item.id === action.id)) return state;
    const item: PackageInstallItem = {
      id: action.id,
      kind: "package_install",
      runtime: action.runtime,
      package: action.package,
      name: action.name,
      reason: action.reason,
      installedVersion: action.installed_version,
      status: "pending",
    };
    return { ...state, items: [...closeStreamingBubble(state.items), item] };
  }
  const update = (change: (item: PackageInstallItem) => PackageInstallItem) => (item: LogItem): LogItem =>
    item.kind === "package_install" && item.id === action.id ? change(item) : item;
  if (action.type === "package_install_finished") {
    const finished = update((item) =>
      action.installed ? { ...item, status: "installed", version: action.version } : { ...item, status: "failed", error: action.error },
    );
    return { ...state, items: state.items.map(finished) };
  }
  const answered = update((item) =>
    item.status !== "pending" ? item : { ...item, status: action.answer === PACKAGE_INSTALL ? "installing" : "declined", reply: action.reply },
  );
  return { ...state, items: state.items.map(answered) };
}
