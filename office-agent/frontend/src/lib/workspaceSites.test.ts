import { describe, expect, it } from "vitest";
import { normalizeSite, reachesPattern } from "./workspaceSites";

describe("normalizeSite", () => {
  it("keeps a bare domain the way the server keeps it", () => {
    expect(normalizeSite("https://www.Example.com/page")).toBe("example.com");
    expect(normalizeSite("*.cdn.example.com")).toBe("cdn.example.com");
    expect(normalizeSite("docs.python.org")).toBe("docs.python.org");
  });
  it("refuses what isn't a domain", () => {
    expect(normalizeSite("not a domain")).toBeNull();
    expect(normalizeSite("localhost")).toBeNull();
  });
});

describe("a secret's host and the listed sites", () => {
  it("is covered by its own domain or a parent one", () => {
    expect(reachesPattern(["openai.com"], "api.openai.com")).toBe(true);
    expect(reachesPattern(["api.openai.com"], "api.openai.com")).toBe(true);
    expect(reachesPattern(["*"], "anything.org")).toBe(true);
  });
  it("is not covered by a sibling or a subdomain of it", () => {
    expect(reachesPattern(["hubspot.com"], "api.hubapi.com")).toBe(false);
    expect(reachesPattern(["api.openai.com"], "openai.com")).toBe(false);
  });
  it("reaches a listed subdomain through a wildcard", () => {
    expect(reachesPattern(["cdn.example.com"], "*.example.com")).toBe(true);
    expect(reachesPattern(["example.com"], "*.example.com")).toBe(true);
    expect(reachesPattern(["other.com"], "*.example.com")).toBe(false);
  });
});
