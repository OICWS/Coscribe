import { describe, expect, it } from "vitest";
import { chartSvg, parseChart } from "./docChart";

const block = (kind: string, rows = "| q | n |\n| --- | --- |\n| Q1 | 3 |\n| Q2 | 5 |") => `\`\`\`chart\n${kind}\n${rows}\n\`\`\``;

describe("parseChart", () => {
  it("reads the kind, the title, the categories and each series", () => {
    expect(parseChart(block("bar Sales", "| q | a | b |\n| --- | --- | --- |\n| Q1 | 3 | 1,000 |"))).toEqual({
      kind: "bar",
      title: "Sales",
      categories: ["Q1"],
      series: [
        { name: "a", values: [3] },
        { name: "b", values: [1000] },
      ],
    });
  });

  it("says why a block is not a chart", () => {
    expect(parseChart(block("radar"))).toMatch(/bar, line or pie/);
    expect(parseChart(block("bar", "| q | n |\n| --- | --- |"))).toMatch(/header row and a data row/);
    expect(parseChart(block("bar", "| q | n |\n| --- | --- |\n| Q1 | lots |"))).toMatch(/numbers/);
    expect(parseChart(block("pie", "| q | a | b |\n| --- | --- | --- |\n| Q1 | 1 | 2 |"))).toMatch(/one data column/);
  });
});

describe("chartSvg", () => {
  it.each(["bar", "line", "pie"])("draws a %s chart and escapes what the text says", (kind) => {
    const chart = parseChart(block(`${kind} <b>x</b>`, "| q | n |\n| --- | --- |\n| A&B | 3 |\n| C | 5 |"));
    expect(typeof chart).toBe("object");
    const svg = chartSvg(chart as Exclude<typeof chart, string>);
    expect(svg.startsWith("<svg")).toBe(true);
    expect(svg).toContain("A&amp;B");
    expect(svg).not.toContain("<b>");
  });

  it("fits a line chart's axis to its values in round steps, and stands bars on zero", () => {
    const rows = "| w | n |\n| --- | --- |\n| W1 | 2480 |\n| W2 | 2710 |";
    const ticks = (kind: string) => [...chartSvg(parseChart(block(kind, rows)) as Exclude<ReturnType<typeof parseChart>, string>).matchAll(/font-size="11">([^<]+)</g)].map((m) => m[1]);
    expect(ticks("line")).toEqual(["2,400", "2,500", "2,600", "2,700", "2,800"]);
    expect(ticks("bar")[0]).toBe("0");
  });
});
