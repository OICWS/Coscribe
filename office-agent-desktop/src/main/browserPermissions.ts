/**
 * The built-in browser's own settings (kept by the desktop app, not the
 * sidecar: they only mean anything where the browser lives), and the
 * per-site permission the AI needs before its browser tools touch a site.
 *
 * The conversation's workspace sets each site's level (decision 0050): Use without asking goes
 * ahead, Not in the browser is refused, and any other site goes ahead when it is on the app's own
 * allowed list or was allowed for this conversation, else it gets a prompt in the Browser panel.
 * The app's own list is what the UI moves into the workspaces once; until then it still counts.
 */

import { app, ipcMain, type BrowserWindow, type WebContents } from "electron";
import { readFileSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { enqueue } from "./browserAgentSteps";

export const BROWSER_PERMISSION_EVENT = "browser-panel:permission";
const PERMISSION_ANSWER_CHANNEL = "browser-panel:permission-answer";
const PENDING_PERMISSION_CHANNEL = "browser-panel:pending-permission";
const GET_ALLOWED_SITES_CHANNEL = "browser-panel:get-allowed-sites";
const SET_ALLOWED_SITES_CHANNEL = "browser-panel:set-allowed-sites";

const PROMPT_TIMEOUT_MS = 3 * 60_000;

export type PermissionAnswer = "once" | "always" | "deny";

interface BrowserSettings {
  openLinksInBuiltIn: boolean;
  allowedSites: string[];
}

interface PendingPrompt {
  requestId: number;
  host: string;
  threadId: string;
  resolve: (answer: PermissionAnswer) => void;
}

const DEFAULTS: BrowserSettings = { openLinksInBuiltIn: true, allowedSites: [] };
let cached: BrowserSettings | undefined;
let pending: PendingPrompt | null = null;
let nextRequestId = 1;
const allowedForThread = new Map<string, Set<string>>();

function settingsPath(): string {
  return join(app.getPath("userData"), "browser-settings.json");
}

export function browserSettings(): BrowserSettings {
  if (cached) return cached;
  try {
    const raw = JSON.parse(readFileSync(settingsPath(), "utf-8")) as Partial<BrowserSettings>;
    cached = {
      openLinksInBuiltIn: typeof raw.openLinksInBuiltIn === "boolean" ? raw.openLinksInBuiltIn : DEFAULTS.openLinksInBuiltIn,
      allowedSites: Array.isArray(raw.allowedSites) ? raw.allowedSites.flatMap((s) => normalizeSite(String(s)) ?? []) : [],
    };
  } catch {
    cached = { ...DEFAULTS };
  }
  return cached;
}

export async function updateBrowserSettings(patch: Partial<BrowserSettings>): Promise<BrowserSettings> {
  cached = { ...browserSettings(), ...patch };
  await writeFile(settingsPath(), JSON.stringify(cached, null, 2), "utf-8");
  return cached;
}

/** "https://www.Example.com/a?b" -> "example.com": a site is a host, and
 * "www." adds nothing (the bare domain already covers its subdomains). */
export function normalizeSite(input: string): string | null {
  const text = input.trim().toLowerCase();
  if (!text) return null;
  let host: string;
  try {
    host = new URL(/^[a-z][a-z0-9+.-]*:\/\//.test(text) ? text : `https://${text}`).hostname;
  } catch {
    return null;
  }
  host = host.replace(/^www\./, "").replace(/\.$/, "");
  return /^[a-z0-9.-]+$|^\[[0-9a-f:]+\]$/.test(host) && host.length > 0 ? host : null;
}

function covers(site: string, host: string): boolean {
  return host === site || host.endsWith(`.${site}`);
}

/** Whether `host` falls under one of `sites`, each a site as normalizeSite
 * names it. */
export function inSites(host: string, sites: string[]): boolean {
  const site = normalizeSite(host);
  if (!site) return false;
  return sites.some((allowed) => {
    const normalized = normalizeSite(allowed);
    return normalized !== null && covers(normalized, site);
  });
}

/** The conversation's network setting (Edit workspace > Sites), sent with each step when it
 * limits the domains: no site permission widens it. */
export function checkNetworkSites(host: string, networkSites: unknown): void {
  if (!Array.isArray(networkSites) || inSites(host, networkSites.map(String))) return;
  throw new Error(
    `${normalizeSite(host) ?? host} is outside the domains this conversation may reach. The user can add it under Edit workspace > Sites.`,
  );
}

/** Where a step ended up: a redirect or a clicked link can leave the list. The page is left for
 * a blank one, and the step fails, so its result never reaches the model. */
export function checkNetworkLanding(page: WebContents | undefined, networkSites: unknown): void {
  let host: string;
  try {
    const url = new URL(page?.getURL() ?? "");
    if (url.protocol !== "http:" && url.protocol !== "https:") return;
    host = url.hostname;
  } catch {
    return;
  }
  try {
    checkNetworkSites(host, networkSites);
  } catch (err) {
    void page?.loadURL("about:blank").catch(() => undefined);
    throw err;
  }
}

export type SiteLevel = "allow" | "ask" | "off";

/** A site's level in the conversation's workspace: the most specific site that covers `host`,
 * "ask" when none does. */
export function siteLevel(host: string, browserSites: unknown): SiteLevel {
  const site = normalizeSite(host);
  if (!site || !browserSites || typeof browserSites !== "object") return "ask";
  let best: [string, SiteLevel] | null = null;
  for (const [key, level] of Object.entries(browserSites as Record<string, unknown>)) {
    const listed = normalizeSite(key);
    if (!listed || !covers(listed, site) || (level !== "allow" && level !== "off")) continue;
    if (!best || listed.length > best[0].length) best = [listed, level];
  }
  return best ? best[1] : "ask";
}

/** Refuses a site outside the workspace's sites, or one it keeps out of the browser (its other
 * tools may still reach that one). */
export function checkSite(host: string, networkSites: unknown, browserSites: unknown): void {
  checkNetworkSites(host, networkSites);
  checkBrowserLevel(host, browserSites);
}

function checkBrowserLevel(host: string, browserSites: unknown): void {
  if (siteLevel(host, browserSites) !== "off") return;
  throw new Error(
    `${normalizeSite(host) ?? host} isn't used in the browser in this workspace. Use a web request instead, or ` +
      "the user can change it under Edit workspace > Sites.",
  );
}

export function isAllowed(host: string, threadId: string, browserSites?: unknown): boolean {
  const site = normalizeSite(host);
  if (!site) return false;
  if (siteLevel(site, browserSites) === "allow") return true;
  if (browserSettings().allowedSites.some((allowed) => covers(allowed, site))) return true;
  return [...(allowedForThread.get(threadId) ?? [])].some((allowed) => covers(allowed, site));
}

function sendPending(win: BrowserWindow | undefined): void {
  if (!pending || !win || win.isDestroyed()) return;
  win.webContents.send(BROWSER_PERMISSION_EVENT, { requestId: pending.requestId, host: pending.host, threadId: pending.threadId });
}

/** Native permission prompts share one foreground answer UI. */
export function requestPermission(host: string, threadId: string, win: BrowserWindow | undefined, browserSites?: unknown): Promise<void> {
  return new Promise((resolve, reject) => enqueue("permissions", async () => {
    try {
      if (!isAllowed(host, threadId, browserSites)) await askPermission(host, threadId, win);
      resolve();
    } catch (error) { reject(error); }
  }));
}

async function askPermission(host: string, threadId: string, win: BrowserWindow | undefined): Promise<void> {
  const site = normalizeSite(host) ?? host;
  const answer = await new Promise<PermissionAnswer>((resolve) => {
    const requestId = nextRequestId++;
    const timer = setTimeout(() => settle("deny"), PROMPT_TIMEOUT_MS);
    function settle(value: PermissionAnswer) {
      clearTimeout(timer);
      if (pending?.requestId === requestId) pending = null;
      resolve(value);
    }
    pending = { requestId, host: site, threadId, resolve: settle };
    sendPending(win);
  });
  if (answer === "once") {
    const sites = allowedForThread.get(threadId) ?? new Set<string>();
    sites.add(site);
    allowedForThread.set(threadId, sites);
  } else if (answer === "always") {
    const sites = browserSettings().allowedSites;
    if (!sites.includes(site)) await updateBrowserSettings({ allowedSites: [...sites, site] });
  } else {
    throw new Error(
      `The user didn't allow Coscribe's browser to use ${site}. Don't use it again unless they ask; ` +
        "they can allow it from the Browser panel.",
    );
  }
}

export function registerBrowserPermissionHandlers(win: BrowserWindow): void {
  ipcMain.handle(PERMISSION_ANSWER_CHANNEL, (_event, requestId: number, answer: PermissionAnswer) => {
    if (pending?.requestId === Number(requestId) && ["once", "always", "deny"].includes(answer)) pending.resolve(answer);
  });
  ipcMain.handle(PENDING_PERMISSION_CHANNEL, () => {
    sendPending(win);
  });
  ipcMain.handle(GET_ALLOWED_SITES_CHANNEL, () => browserSettings().allowedSites);
  ipcMain.handle(SET_ALLOWED_SITES_CHANNEL, async (_event, sites: unknown) => {
    const list = Array.isArray(sites) ? [...new Set(sites.flatMap((s) => normalizeSite(String(s)) ?? []))] : [];
    return (await updateBrowserSettings({ allowedSites: list })).allowedSites;
  });
}
