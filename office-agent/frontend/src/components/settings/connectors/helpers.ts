import type { McpCatalogEntry, McpServersResponse, SecretInfo } from "../../../types/settings";
import type { ConnectorRow } from "./types";

const PINNED_NPM_PACKAGE_RE = /^((?:@[^/@]+\/)?[^@]+)@(\d[\w.-]*)$/;
export function findPinnedNpmPackage(args: string[]): { name: string; version: string } | null {
  for (const arg of args) {
    const match = PINNED_NPM_PACKAGE_RE.exec(arg);
    if (match) return { name: match[1], version: match[2] };
  }
  return null;
}

export function parseEnvLines(text: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const idx = line.indexOf("=");
    if (idx <= 0) continue;
    env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return env;
}

export function parseHeaderLines(text: string): Record<string, string> {
  const headers: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const idx = line.indexOf(":");
    if (idx > 0) headers[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return headers;
}

const SECRET_PLACEHOLDER = /\{\{secret:([A-Za-z_][A-Za-z0-9_]{0,63})\}\}/g;

// Mirrors runtime/secret_store.py's host_allowed: "*.b.com" covers subdomains, not b.com.
export function hostAllowed(pattern: string, host: string): boolean {
  const lower = host.toLowerCase();
  return pattern.startsWith("*.") ? lower.endsWith(pattern.slice(1)) && lower !== pattern.slice(2) : lower === pattern;
}

/** What is wrong with the secrets `text` refers to, in the server's own terms:
 * one that doesn't exist, or (for a header, which goes to `host`) one not allowed
 * for that host. The server checks again when the connector is added. */
export function secretProblems(text: string, secrets: SecretInfo[], host: string | null): string[] {
  const problems: string[] = [];
  for (const match of text.matchAll(SECRET_PLACEHOLDER)) {
    const secret = secrets.find((s) => s.name === match[1]);
    if (!secret) problems.push(`There is no secret named ${match[1]}.`);
    else if (host && !secret.hosts.some((pattern) => hostAllowed(pattern, host))) {
      problems.push(`${match[1]} may only be sent to ${secret.hosts.join(", ")}, not ${host}.`);
    }
  }
  return problems;
}

export function insertAtCaret(field: HTMLTextAreaElement | null, text: string, insert: string): string {
  if (!field) return text + insert;
  const start = field.selectionStart ?? text.length;
  const end = field.selectionEnd ?? text.length;
  return text.slice(0, start) + insert + text.slice(end);
}

export function buildRows(catalog: McpCatalogEntry[], servers: McpServersResponse): ConnectorRow[] {
  const rows: ConnectorRow[] = catalog.map((entry) => ({
    name: entry.name,
    title: entry.title ?? entry.name,
    catalogEntry: entry,
    serverInfo: servers[entry.name] ?? null,
  }));
  for (const [name, info] of Object.entries(servers)) {
    if (!catalog.some((entry) => entry.name === name)) {
      rows.push({ name, title: name, catalogEntry: null, serverInfo: info });
    }
  }
  return rows;
}
