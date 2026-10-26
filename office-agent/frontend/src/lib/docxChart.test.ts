// @vitest-environment jsdom
// jsdom for this file only: the chart xml is read with DOMParser.
import { describe, expect, it } from "vitest";
import { chartSvg } from "./docxChart";

const C = 'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"';
const series = (name: string, values: number[]) =>
  `<c:ser><c:tx><c:strRef><c:strCache><c:pt idx="0"><c:v>${name}</c:v></c:pt></c:strCache></c:strRef></c:tx>` +
  `<c:cat><c:strRef><c:strCache>${["Q1", "Q2", "Q3"].map((q, i) => `<c:pt idx="${i}"><c:v>${q}</c:v></c:pt>`).join("")}</c:strCache></c:strRef></c:cat>` +
  `<c:val><c:numRef><c:numCache>${values.map((v, i) => `<c:pt idx="${i}"><c:v>${v}</c:v></c:pt>`).join("")}</c:numCache></c:numRef></c:val></c:ser>`;
const chart = (plot: string, title = "") =>
  `<c:chartSpace ${C}><c:chart>${title ? `<c:title><c:tx><c:rich><a:p><a:r><a:t>${title}</a:t></a:r></a:p></c:rich></c:tx></c:title>` : ""}<c:plotArea>${plot}</c:plotArea></c:chart></c:chartSpace>`;

describe("a Word chart as svg", () => {
  it("draws one bar per value, and the title", () => {
    const svg = chartSvg(chart(`<c:barChart><c:barDir val="col"/>${series("R", [1, 2, 3])}</c:barChart>`, "Totals"), 400, 200) ?? "";
    expect(svg).toContain("Totals");
    expect(svg).toContain("Q2");
    expect(svg.match(/<rect x=/g)?.length).toBe(3);
  });

  it("draws a line chart as a polyline and a pie as slices", () => {
    expect(chartSvg(chart(`<c:lineChart>${series("L", [1, 3, 2])}</c:lineChart>`), 400, 200)).toContain("<polyline");
    expect((chartSvg(chart(`<c:pieChart>${series("P", [1, 1, 2])}</c:pieChart>`), 400, 200) ?? "").match(/<path /g)?.length).toBe(3);
  });

  it("gives nothing for a chart it cannot draw", () => {
    expect(chartSvg(chart(`<c:radarChart>${series("R", [1])}</c:radarChart>`), 400, 200)).toBeNull();
  });

  it("gives each bar of a single series its own colour unless the file turns that off", () => {
    const fills = (plot: string) => [...(chartSvg(chart(plot), 400, 200) ?? "").matchAll(/<rect x="[^"]+" y="[^"]+" width="[^"]+" height="[^"]+" fill="(#[0-9a-f]{6})"\/>/g)].map((m) => m[1]);
    const varied = fills(`<c:barChart><c:barDir val="col"/>${series("R", [1, 2, 3])}</c:barChart>`);
    expect(new Set(varied).size).toBe(3);
    const single = fills(`<c:barChart><c:barDir val="col"/><c:varyColors val="0"/>${series("R", [1, 2, 3])}</c:barChart>`);
    expect(new Set(single).size).toBe(1);
  });

  it("stops the value axis at the first round step past the data, as Word does", () => {
    const svg = chartSvg(chart(`<c:barChart><c:barDir val="col"/>${series("R", [28, 33, 41])}</c:barChart>`), 400, 200) ?? "";
    expect(svg).toContain(">45</text>");
    expect(svg).not.toContain(">50</text>");
  });
});
