import { describe, expect, it } from "vitest";
import { canvasOfPage, FILE_LINK, fileLinkPath, filesByName, madeFiles, remarkFileChips, touchedFiles } from "./fileMentions";

const call = (toolName: string, path: string, extra: object = {}) => ({ toolName, arguments: { path }, result: "ok", ...extra });

describe("touchedFiles", () => {
  it("lists the documents and decks a finished call made or changed, once each, and not reads or failures", () => {
    const calls = [
      call("write_docx", "a.docx"),
      call("read_docx", "b.docx"),
      call("edit_docx", "a.docx"),
      call("write_docx", "c.docx", { isError: true }),
      call("write_docx", "d.docx", { result: undefined }),
      call("write_xlsx", "e.xlsx"),
      call("build_pptx", "deck.pptx"),
    ];
    expect(touchedFiles(calls)).toEqual(["a.docx", "deck.pptx"]);
  });

  it("does not count a call that only looks at a file, and counts what a script wrote", () => {
    const calls = [
      call("list_pptx_shapes", "deck.pptx"),
      call("inspect_docx", "a.docx"),
      { toolName: "run_python_script", arguments: { script: "x" }, result: JSON.stringify({ files_written: ["out/deck.pptx", "notes.txt"] }) },
      { toolName: "run_python_script", arguments: { script: "x" }, result: JSON.stringify({ stdout: "hi" }) },
    ];
    expect(touchedFiles(calls)).toEqual(["out/deck.pptx"]);
  });

  it("maps a file name to its path", () => {
    expect([...filesByName([call("write_docx", "reports/SDD.docx")])]).toEqual([["SDD.docx", "reports/SDD.docx"]]);
  });
});

describe("madeFiles", () => {
  it("gives a design's artboards as its one canvas, and a page of its own as itself", () => {
    const calls = [
      call("write_file", "plants.design/home.html"),
      call("write_file", "plants.design/discover.html"),
      call("write_file", "landing.html"),
      call("write_file", "plants.design.json"),
      call("write_file", "out\\shop.design\\cart.html"),
    ];
    expect(madeFiles(calls)).toEqual(["plants.design.json", "landing.html", "out\\shop.design.json"]);
  });

  it("knows a board's page only by the folder it sits in", () => {
    expect(canvasOfPage("a/plants.design/home.htm")).toBe("a/plants.design.json");
    expect(canvasOfPage("plants.design.html")).toBeNull();
    expect(canvasOfPage("plants.design/sub/home.html")).toBeNull();
  });
});

describe("remarkFileChips", () => {
  const files = new Map([["SDD.docx", "reports/SDD.docx"], ["SDD.docx.bak.docx", "x/SDD.docx.bak.docx"]]);
  const run = (tree: object) => {
    remarkFileChips(files)()(tree as never);
    return tree;
  };
  const paragraph = (...children: object[]) => ({ type: "root", children: [{ type: "paragraph", children }] });

  it("turns a name in running text and in backticks into a link, and keeps the words around it", () => {
    const tree = run(paragraph({ type: "text", value: "I wrote SDD.docx, see " }, { type: "inlineCode", value: "SDD.docx" }, { type: "text", value: "." })) as {
      children: { children: { type: string; value?: string; url?: string }[] }[];
    };
    const kinds = tree.children[0].children.map((n) => `${n.type}:${n.value ?? n.url}`);
    expect(kinds).toEqual(["text:I wrote ", `link:${FILE_LINK}reports/SDD.docx`, "text:, see ", `link:${FILE_LINK}reports/SDD.docx`, "text:."]);
  });

  it("leaves a name that is part of a longer word or path, one inside a link and one in a code block", () => {
    const tree = run({
      type: "root",
      children: [
        { type: "paragraph", children: [{ type: "text", value: "MySDD.docx and old/SDD.docx and SDD.docxx" }] },
        { type: "paragraph", children: [{ type: "link", url: "https://x.test", children: [{ type: "text", value: "SDD.docx" }] }] },
        { type: "code", value: "SDD.docx" },
      ],
    }) as { children: { children?: { type: string }[] }[] };
    expect(tree.children[0].children?.map((n) => n.type)).toEqual(["text"]);
    expect(tree.children[1].children?.[0].type).toBe("link");
  });
});

describe("fileLinkPath", () => {
  it("gives back a path the markdown pipeline percent-encoded, and leaves a plain or odd one alone", () => {
    expect(fileLinkPath(`${FILE_LINK}docs/AI%E6%96%B0%E9%97%BB.pptx`)).toBe("docs/AI新闻.pptx");
    expect(fileLinkPath(`${FILE_LINK}made.docx`)).toBe("made.docx");
    expect(fileLinkPath(`${FILE_LINK}100%.docx`)).toBe("100%.docx");
  });
});
