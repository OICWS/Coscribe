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
