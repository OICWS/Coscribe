import { afterEach, describe, expect, it, vi } from "vitest";
import { buildFileTree, connectorTitle, extension, matches, PREVIEWABLE, shortDate, withoutFrontmatter } from "./helpers";

describe("extension", () => {
  it("returns the lower-cased extension of the last path segment", () => {
    expect(extension("scripts/Run.PY")).toBe("py");
    expect(extension("a.b/archive.tar.gz")).toBe("gz");
  });

  it("returns an empty string when the file name has no dot, even if a folder does", () => {
    expect(extension("README")).toBe("");
    expect(extension("my.dir/README")).toBe("");
    expect(extension("")).toBe("");
  });

  it("agrees with what the viewer can preview", () => {
    expect(PREVIEWABLE.has(extension("SKILL.md"))).toBe(true);
    expect(PREVIEWABLE.has(extension("logo.png"))).toBe(false);
  });
});

describe("shortDate", () => {
  afterEach(() => vi.useRealTimers());

  it("omits the year in the current year and shows it otherwise", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 5, 15));
    expect(shortDate(new Date(2026, 0, 5).toISOString())).not.toMatch(/2026/);
    expect(shortDate(new Date(2024, 0, 5).toISOString())).toMatch(/2024/);
  });
});

describe("matches", () => {
  it("is true for an empty or blank query", () => {
    expect(matches("", "anything")).toBe(true);
    expect(matches("   ", "anything")).toBe(true);
  });

  it("matches any text case-insensitively, after trimming the query", () => {
    expect(matches(" pdf ", "name", "Fills a PDF form")).toBe(true);
    expect(matches("zzz", "name", "description")).toBe(false);
  });
});

describe("buildFileTree", () => {
  it("nests folders and keeps files in order", () => {
    const tree = buildFileTree(["SKILL.md", "scripts/run.py", "scripts/lib/util.py", "scripts/b.sh"]);
    expect(tree.files).toEqual(["SKILL.md"]);
    const scripts = tree.dirs.get("scripts")!;
    expect(scripts.files).toEqual(["run.py", "b.sh"]);
    expect(scripts.dirs.get("lib")!.files).toEqual(["util.py"]);
  });

  it("is empty for no paths", () => {
    const tree = buildFileTree([]);
    expect(tree.files).toEqual([]);
    expect(tree.dirs.size).toBe(0);
  });
});

describe("withoutFrontmatter", () => {
  it("drops the leading YAML header", () => {
    expect(withoutFrontmatter("---\nname: x\ndescription: y\n---\n# Title\nbody")).toBe("# Title\nbody");
  });

  it("stops at the first closing line, keeping a later --- rule in the body", () => {
    expect(withoutFrontmatter("---\na: 1\n---\nbody\n---\nmore")).toBe("body\n---\nmore");
  });

  it("leaves text without a leading header, and a later --- rule, alone", () => {
    expect(withoutFrontmatter("# Title\n---\nbody\n---\n")).toBe("# Title\n---\nbody\n---\n");
  });
});

describe("connectorTitle", () => {
  it("uses the known brand spelling", () => {
    expect(connectorTitle("hubspot")).toBe("HubSpot");
    expect(connectorTitle("microsoft-365")).toBe("Microsoft 365");
  });

  it("title-cases an unknown name, turning - and _ into spaces", () => {
    expect(connectorTitle("google-drive")).toBe("Google Drive");
    expect(connectorTitle("my_tool")).toBe("My Tool");
  });
});
