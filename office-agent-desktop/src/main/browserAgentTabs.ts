import type { DownloadItem, WebContents } from "electron";
import type { Command } from "./browserAgent";
import { cdpFor } from "./browserCdp";
import { tabHasWork } from "./browserAgentSteps";
import { activeTab, allTabs, ensureActiveTab, createTab, closeTab, MAX_TABS, tabInfo, tabLimitReached, hiddenTabSize, tabShown, type Tab } from "./browserPanel";

export const popupDownloads = new Map<number, { pending: number; failed: boolean }>();
export function trackPopupDownload(tab: Tab, item: DownloadItem): void {
  let tracked = popupDownloads.get(tab.id);
  if (!tracked) {
    tracked = { pending: 0, failed: false };
    popupDownloads.set(tab.id, tracked);
    tab.view.webContents.once("destroyed", () => popupDownloads.delete(tab.id));
  }
  tracked.pending++;
  item.once("done", (_event, state) => {
    tracked.pending--;
    tracked.failed ||= state !== "completed";
  });
}

export const selectedTabs = new Map<string, number>();
export function commandTab(command: Command): Tab {
  const requested = command.args.tab_id;
  const tabs = allTabs(command.thread_id);
  const source = command.args.source_tab;
  const selected = source ? tabs.find(t => t.id === Number(source) || t.name === source)
    : tabs.find(t => t.id === selectedTabs.get(command.thread_id)) ?? activeTab(command.thread_id);
  if (source && !selected) throw new Error(`No source tab matches ${source}.`);
  let tab: Tab | undefined;
  if (command.tabId !== undefined) tab = tabs.find(t => t.id === command.tabId);
  else if (requested === "current") tab = activeTab(command.thread_id);
  else if (requested === "opener") tab = tabs.find(t => t.id === selected?.openerId);
  else if (requested === "last_opened") tab = [...tabs].reverse().find(t => t.openerId === selected?.id);
  else if (requested) tab = tabs.find(t => t.id === Number(requested) || t.name === requested);
  else tab = selected ?? ensureActiveTab(command.thread_id);
  if (!tab) throw new Error(`No browser tab matches ${requested ?? command.tabId}.`);
  return tab;
}

export function withTab(tab: Tab, extra: Record<string, unknown> = {}): Record<string, unknown> {
  const info = tabInfo(tab);
  return { ...extra, tab: { id: info.id, title: info.title, url: info.url, opener_id: tab.openerId, name: tab.name } };
}

export function listTabs(group: string): Record<string, unknown> {
  const current = activeTab(group)?.id;
  return {
    tabs: allTabs(group).map((t) => {
      const info = tabInfo(t);
      return { id: info.id, title: info.title, url: info.url, active: info.id === current, opener_id: t.openerId, name: t.name };
    }),
  };
}

export function pinCommand(command: Command): void {
  if (command.action === "wait_for" && command.args.download && typeof command.args.tab_id === "number" && command.args.tab_id > 0) command.tabId = command.args.tab_id;
  else if (command.action === "wait_for" && command.args.download && !command.args.tab_id && !allTabs(command.thread_id).length) command.tabId = undefined;
  else if (command.action !== "tabs" || !["list", "new", "close_downloads"].includes(String(command.args.op))) command.tabId = commandTab(command).id;
  if (command.tabId && !selectedTabs.has(command.thread_id)) selectedTabs.set(command.thread_id, command.tabId);
}

export async function runTabCommand(command: Command, load: (wc: WebContents, url: string) => Promise<void>): Promise<Record<string, unknown>> {
  const args = command.args;
  const op = String(args.op);
  if (op === "new") {
    if (tabLimitReached(command.thread_id)) {
      throw new Error(`All ${MAX_TABS} tabs are in use -- close one with browser_tabs("close") or reuse the current tab.`);
    }
    const name = String(args.name ?? "");
    if (name && allTabs(command.thread_id).some(t => t.name === name)) throw new Error(`Tab name ${name} is already in use.`);
    const tab = createTab(undefined, command.thread_id);
    if (name) tab.name = name;
    selectedTabs.set(command.thread_id, tab.id);
    if (args.url) {
      const cdp = cdpFor(tab.view.webContents);
      await cdp.drive(command.thread_id, args.download_dir, !tabShown(tab), hiddenTabSize());
      await load(tab.view.webContents, String(args.url));
      cdp.stepEnded = Date.now();
    }
  } else if (op === "select") {
    selectedTabs.set(command.thread_id, commandTab(command).id);
  } else if (op === "close") {
    const target = commandTab(command);
    if (target.userControlled || (target.userTouched && activeTab(command.thread_id)?.id === target.id)) throw new Error("This page is being used by the user.");
    if (selectedTabs.get(command.thread_id) === target.id) selectedTabs.set(command.thread_id, target.openerId ?? 0);
    closeTab(target.id);
  } else if (op === "close_downloads") {
    for (const target of [...allTabs(command.thread_id)]) {
      const tracked = popupDownloads.get(target.id);
      if (tracked && tracked.pending === 0 && !tracked.failed && target.openerId &&
          !target.userTouched && !target.userControlled && activeTab(command.thread_id)?.id !== target.id &&
          !tabHasWork(command.thread_id, target.id)) {
        closeTab(target.id);
        popupDownloads.delete(target.id);
      }
    }
  } else if (op === "info") {
    return { ...withTab(commandTab(command)), ...listTabs(command.thread_id) };
  }
  return listTabs(command.thread_id);
}
