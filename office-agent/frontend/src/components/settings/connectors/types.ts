import type { McpCatalogEntry, McpServerInfo } from "../../../types/settings";

export type LocalServerArgs = { command: string; args: string[]; env?: Record<string, string> };
export type RemoteServerArgs = { server_url: string; headers?: Record<string, string>; auth?: "oauth"; oauth_app?: string };

/** A catalog entry, a connector someone added, or both. */
export interface ConnectorRow {
  name: string;
  title: string;
  catalogEntry: McpCatalogEntry | null;
  serverInfo: McpServerInfo | null;
}

export interface Notice {
  text: string;
  error: boolean;
  update?: { pkg: string; version: string };
  /** A sign-in waiting in the user's browser; the notice goes away once it connects. */
  signin?: { name: string; url: string };
}

export const SIGN_IN_TEXT = "Finish signing in in your browser, a page was opened.";
