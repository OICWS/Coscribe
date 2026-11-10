import { describe, expect, it } from "vitest";
import { appPath, closeTab, fileKind, hasSource, keepTab, NO_TABS, openTab, splitCsv } from "./workspaceFiles";

const a = { root: 0, path: "a.md" };
const b = { root: 0, path: "src/b.py" };
const c = { root: 1, path: "c.txt" };

describe("tabs", () => {
  it("replaces the preview tab with the next file, and keeps a pinned one", () => {
    let tabs = openTab(NO_TABS, a);
    tabs = openTab(tabs, b);
    expect(tabs.open.map((t) => t.ref.path)).toEqual(["src/b.py"]);
    tabs = keepTab(tabs, b);
    tabs = openTab(tabs, a);
    expect(tabs.open.map((t) => [t.ref.path, t.kept])).toEqual([["src/b.py", true], ["a.md", false]]);
    expect(tabs.active).toEqual(a);
  });

  it("opens a file kept from the start beside the preview, and closing the active tab picks its neighbour", () => {
    let tabs = openTab(openTab(NO_TABS, a), b, true);
    tabs = openTab(tabs, c, true);
    expect(tabs.open.length).toBe(3);
    tabs = openTab(tabs, b);
    tabs = closeTab(tabs, b);
    expect(tabs.active).toEqual(c);
    expect(closeTab(closeTab(tabs, c), a)).toEqual({ open: [], active: null });
  });
});

describe("file kinds", () => {
  it("draws markdown, pages, SVG and tables with their source a click away, and shows code as code", () => {
    expect(["README.md", "page.HTML", "logo.svg", "data.tsv"].map(fileKind).every(hasSource)).toBe(true);
    expect(fileKind("app.py")).toBe("text");
    expect(fileKind("tsconfig.json")).toBe("text");
    expect(fileKind("photo.JPG")).toBe("image");
    expect(fileKind("deck.pptx")).toBe("office");
    expect(fileKind("tool.exe")).toBe("binary");
    expect(hasSource("text")).toBe(false);
  });
});

describe("splitCsv", () => {
  it("keeps quoted separators, doubled quotes and line breaks inside a field", () => {
    expect(splitCsv('name,note\r\n"Smith, J","said ""hi""\nthen"\nlast,', ",")).toEqual([
      ["name", "note"],
      ["Smith, J", 'said "hi"\nthen'],
      ["last", ""],
    ]);
  });
});

describe("appPath", () => {
  it("names a file in the main folder relative to it and one elsewhere by its whole path", () => {
    const roots = [{ name: "w", path: "C:\\w" }, { name: "x", path: "D:\\x\\" }];
    expect(appPath(roots, b)).toBe("src/b.py");
    expect(appPath(roots, { root: 1, path: "d/e.md" })).toBe("D:\\x\\d\\e.md");
  });
});
