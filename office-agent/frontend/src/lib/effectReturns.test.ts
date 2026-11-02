import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// React calls whatever an effect returns as its cleanup. Newer Chromium returns a promise from
// scrollIntoView, so an effect written as `() => el.scrollIntoView()` crashes the app there
// ("destroy is not a function") while passing on an older browser.
const RETURNS_A_DOM_CALL = /use(?:Layout)?Effect\(\(\)\s*=>\s*[\w.?]*\.(?:scrollIntoView|scrollTo|scrollBy|animate|requestFullscreen|focus|blur|play)\(/;

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !name.endsWith(".test.ts") ? [path] : [];
  });
}

describe("effects", () => {
  it("return no DOM call's value, which React would call as the cleanup", () => {
    const found = sources(join(__dirname, "..")).flatMap((path) =>
      readFileSync(path, "utf8")
        .split("\n")
        .flatMap((line, i) => (RETURNS_A_DOM_CALL.test(line) ? [`${path}:${i + 1}`] : [])),
    );
    expect(found).toEqual([]);
  });

  it("would catch the line that crashed", () => {
    expect(RETURNS_A_DOM_CALL.test('  useEffect(() => activeItem.current?.scrollIntoView({ block: "nearest" }), [active]);')).toBe(true);
    expect(RETURNS_A_DOM_CALL.test("  useEffect(() => {")).toBe(false);
  });
});
