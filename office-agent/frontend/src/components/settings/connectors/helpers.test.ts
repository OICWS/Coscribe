import { describe, expect, it } from "vitest";
import type { McpCatalogEntry, McpServerInfo, SecretInfo } from "../../../types/settings";
import {
  buildRows,
  findPinnedNpmPackage,
  hostAllowed,
  insertAtCaret,
  parseEnvLines,
  parseHeaderLines,
  secretProblems,
} from "./helpers";

const secret = (name: string, hosts: string[]): SecretInfo => ({ name, hosts, created_at: null });
const entry = (name: string, title?: string): McpCatalogEntry => ({ name, title, description: "" });
const info = (partial: Partial<McpServerInfo> = {}) => partial as McpServerInfo;

describe("findPinnedNpmPackage", () => {
  it("finds a name@version argument, scoped or not", () => {
    expect(findPinnedNpmPackage(["-y", "left-pad@1.3.0"])).toEqual({ name: "left-pad", version: "1.3.0" });
    expect(findPinnedNpmPackage(["-y", "@scope/pkg@2.0.1-beta.1"])).toEqual({ name: "@scope/pkg", version: "2.0.1-beta.1" });
  });

  it("ignores unpinned or non-version arguments", () => {
    expect(findPinnedNpmPackage(["-y", "left-pad", "--flag=a@b", "pkg@latest"])).toBeNull();
    expect(findPinnedNpmPackage([])).toBeNull();
  });
});

describe("parseEnvLines", () => {
  it("splits on the first =, trims, and keeps = inside the value", () => {
    expect(parseEnvLines("A = 1\nTOKEN=x=y=\n")).toEqual({ A: "1", TOKEN: "x=y=" });
  });

  it("skips lines with no key or no =", () => {
    expect(parseEnvLines("=novalue\njust text\n\nK=v")).toEqual({ K: "v" });
  });
});

describe("parseHeaderLines", () => {
  it("splits on the first colon and keeps colons in the value", () => {
    expect(parseHeaderLines("Authorization: Bearer abc\nX-Url: http://h:80")).toEqual({
      Authorization: "Bearer abc",
      "X-Url": "http://h:80",
    });
  });

  it("skips lines with no header name or no colon", () => {
    expect(parseHeaderLines(": v\nnothing\nK:v")).toEqual({ K: "v" });
  });
});

describe("hostAllowed", () => {
  it("matches an exact host case-insensitively", () => {
    expect(hostAllowed("api.example.com", "API.Example.com")).toBe(true);
    expect(hostAllowed("api.example.com", "other.example.com")).toBe(false);
  });

  it("lets *.b.com cover subdomains but not b.com itself", () => {
    expect(hostAllowed("*.b.com", "a.b.com")).toBe(true);
    expect(hostAllowed("*.b.com", "x.a.b.com")).toBe(true);
    expect(hostAllowed("*.b.com", "b.com")).toBe(false);
    expect(hostAllowed("*.b.com", "evilb.com")).toBe(false);
  });
});

describe("secretProblems", () => {
  const secrets = [secret("TOKEN", ["api.example.com"])];

  it("reports a secret that does not exist", () => {
    expect(secretProblems("Bearer {{secret:MISSING}}", secrets, "api.example.com")).toEqual([
      "There is no secret named MISSING.",
    ]);
  });

  it("reports a secret not allowed for the host", () => {
    expect(secretProblems("{{secret:TOKEN}}", secrets, "evil.com")).toEqual([
      "TOKEN may only be sent to api.example.com, not evil.com.",
    ]);
  });

  it("accepts an allowed host, and skips the host check when there is none", () => {
    expect(secretProblems("{{secret:TOKEN}}", secrets, "api.example.com")).toEqual([]);
    expect(secretProblems("{{secret:TOKEN}}", secrets, null)).toEqual([]);
  });

  it("reports each placeholder and ignores text without one", () => {
    expect(secretProblems("plain", secrets, null)).toEqual([]);
    expect(secretProblems("{{secret:A}} {{secret:B}}", [], null)).toHaveLength(2);
  });
});

describe("insertAtCaret", () => {
  const field = (selectionStart: number | null, selectionEnd: number | null) =>
    ({ selectionStart, selectionEnd }) as HTMLTextAreaElement;

  it("inserts at the caret and replaces a selection", () => {
    expect(insertAtCaret(field(2, 2), "abcd", "X")).toBe("abXcd");
    expect(insertAtCaret(field(1, 3), "abcd", "X")).toBe("aXd");
  });

  it("appends when there is no field, and when the field has no selection", () => {
    expect(insertAtCaret(null, "abcd", "X")).toBe("abcdX");
    expect(insertAtCaret(field(null, null), "abcd", "X")).toBe("abcdX");
  });
});

describe("buildRows", () => {
  it("joins a catalog entry with its added server, using the title when there is one", () => {
    const server = info({ connected: true });
    const rows = buildRows([entry("gmail", "Gmail"), entry("notion")], { gmail: server });
    expect(rows).toEqual([
      { name: "gmail", title: "Gmail", catalogEntry: entry("gmail", "Gmail"), serverInfo: server },
      { name: "notion", title: "notion", catalogEntry: entry("notion"), serverInfo: null },
    ]);
  });

  it("appends a custom server that is not in the catalog", () => {
    const custom = info();
    const rows = buildRows([entry("gmail")], { mine: custom });
    expect(rows[1]).toEqual({ name: "mine", title: "mine", catalogEntry: null, serverInfo: custom });
  });
});
