// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

// Each feature is entered through its index.ts, and the indexes import one another. A
// feature that reads another's export while its own module loads (a constant built at the
// top of a file) gets `undefined` when the two indexes form a cycle. Each case loads one
// index first, in a fresh module graph, as a lazy panel does in the app.
const indexes = import.meta.glob("./*/index.ts");

// jsdom has no matchMedia; the theme reads it when its module loads.
window.matchMedia ??= (query: string) =>
  ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList;

describe("feature indexes", () => {
  it("finds the features", () => {
    expect(Object.keys(indexes).length).toBeGreaterThan(5);
  });

  for (const [path, load] of Object.entries(indexes)) {
    it(`${path} loads on its own`, async () => {
      const { vi } = await import("vitest");
      vi.resetModules();
      await expect(load()).resolves.toBeTypeOf("object");
    });
  }
});

// On Windows, `./chatlog` finds `ChatLog.tsx` before the `chatlog/` folder. An import of a
// feature whose name a loose file shares (ignoring case) names its index file.
describe("feature imports on a case-insensitive disk", () => {
  it("name the index where a loose file shares the feature's name", async () => {
    const { readdirSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const here = join(process.cwd(), "src", "components");
    const loose = readdirSync(here).filter((name) => /\.tsx?$/.test(name));
    const clashing = Object.keys(indexes)
      .map((path) => path.split("/")[1])
      .filter((feature) => loose.some((name) => name.replace(/\.tsx?$/, "").toLowerCase() === feature));
    const sources = readdirSync(join(process.cwd(), "src"), { recursive: true, encoding: "utf8" })
      .filter((name) => /\.tsx?$/.test(name));
    const bad = sources.flatMap((name) => {
      const text = readFileSync(join(process.cwd(), "src", name), "utf8");
      return clashing.filter((feature) => text.includes(`/${feature}"`)).map((feature) => `${name}: ${feature}`);
    });
    expect(bad).toEqual([]);
  });
});
