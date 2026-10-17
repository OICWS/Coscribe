import { afterEach, describe, expect, it, vi } from "vitest";
import { sendTokenWithWrites, socketUrl } from "./launchToken";

function pageWithToken(content: string | null) {
  vi.stubGlobal("document", {
    querySelector: () => (content === null ? null : { content }),
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("socketUrl", () => {
  it("adds the token the server put in the page", () => {
    pageWithToken("a b");
    expect(socketUrl("ws://x/ws/1")).toBe("ws://x/ws/1?token=a%20b");
    expect(socketUrl("ws://x/ws/1?y=2")).toBe("ws://x/ws/1?y=2&token=a%20b");
  });

  it("leaves the url alone when the page has none (the dev server adds it)", () => {
    pageWithToken(null);
    expect(socketUrl("ws://x/ws/1")).toBe("ws://x/ws/1");
  });
});

describe("sendTokenWithWrites", () => {
  function install(content: string | null) {
    pageWithToken(content);
    const seen: Request[] = [];
    const location = { origin: "http://127.0.0.1:8000", href: "http://127.0.0.1:8000/" };
    const fake = { fetch: (r: Request) => (seen.push(r), Promise.resolve(new Response())), location };
    vi.stubGlobal("window", { ...fake, fetch: Object.assign(fake.fetch, { bind: () => fake.fetch }) });
    sendTokenWithWrites();
    return { seen, run: (url: string, init?: RequestInit) => (window.fetch as typeof fetch)(url, init) };
  }

  it("sends the token on a write to the same origin, not on a read or another origin", async () => {
    const { seen, run } = install("tok");
    await run("http://127.0.0.1:8000/api/x", { method: "POST", body: "{}" });
    await run("http://127.0.0.1:8000/api/x");
    await run("https://elsewhere.example/api/x", { method: "POST", body: "{}" });
    expect(seen.map((r) => r.headers.get("x-coscribe-token"))).toEqual(["tok", null, null]);
  });

  it("does nothing without a token", () => {
    const { seen } = install(null);
    expect(seen).toEqual([]);
  });
});
