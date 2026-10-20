// @vitest-environment jsdom
// jsdom for this file only: these functions change DOM nodes.
import { describe, expect, it } from "vitest";
import { parseSection, elementsOf } from "./slideSource";
import { clearColumnWidths, columnCount, columnWidths, hasHeader, setColumnCount, setColumnWidth, setHeader, setRowCount, tableRows } from "./slideTable";

const table = () =>
  elementsOf(
    parseSection(
      '<section><table style="left:0px;top:0px;width:900px;height:200px">' +
        '<tr><th style="background:#123456;color:#FFFFFF">A</th><th style="background:#123456;color:#FFFFFF">B</th></tr>' +
        "<tr><td>1</td><td>2</td></tr></table></section>",
    ),
  )[0];

describe("a section's table", () => {
  it("adds rows as blank copies of the last, and takes surplus ones off", () => {
    const t = table();
    setRowCount(t, 4);
    expect(tableRows(t).length).toBe(4);
    expect(tableRows(t)[3].children.length).toBe(2);
    expect(tableRows(t)[3].textContent).toBe("");
    setRowCount(t, 1);
    expect(tableRows(t).length).toBe(1);
    setRowCount(t, 0);
    expect(tableRows(t).length).toBe(1); // one row stays
  });

  it("adds columns to every row, and keeps a header's fill on a new header cell", () => {
    const t = table();
    setColumnCount(t, 3);
    expect(columnCount(t)).toBe(3);
    const header = tableRows(t)[0].children[2];
    expect(header.localName).toBe("th");
    expect(header.getAttribute("style")).toContain("#123456");
    setColumnCount(t, 1);
    expect(tableRows(t).every((row) => row.children.length === 1)).toBe(true);
  });

  it("turns the header row on and off", () => {
    const t = table();
    expect(hasHeader(t)).toBe(true);
    setHeader(t, false, "#111111");
    expect(hasHeader(t)).toBe(false);
    expect(tableRows(t)[0].children[0].getAttribute("style") ?? "").not.toContain("#123456");
    setHeader(t, true, "#111111");
    expect(hasHeader(t)).toBe(true);
    expect(tableRows(t)[0].children[0].getAttribute("style")).toContain("#111111");
  });

  it("writes every column's width when one is set, and shares the width evenly again", () => {
    const t = table();
    expect(columnWidths(t, 900)).toEqual({ widths: [450, 450], set: false });
    setColumnWidth(t, 0, 300, 900);
    expect(columnWidths(t, 900)).toEqual({ widths: [300, 450], set: true });
    clearColumnWidths(t);
    expect(columnWidths(t, 900).set).toBe(false);
  });
});
