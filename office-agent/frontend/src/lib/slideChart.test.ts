// @vitest-environment jsdom
// jsdom for this file only: these functions change DOM nodes.
import { describe, expect, it } from "vitest";
import { chartTitle, chartType, isStacked, readSpec, seriesOf, setChartTitle, setChartType, setLabels, setLegend, setSeriesColour, setAxisTitle, setStacked, setValueAxisSetting, showsLabels, showsLegend, valueAxisSetting } from "./slideChart";
import { elementsOf, parseSection } from "./slideSource";

const SPEC = { type: "column", categories: ["A", "B"], series: [{ name: "Q2", values: [1, 2] }, { name: "Q3", values: [3, 4] }], font_size: 27 };

const chart = (spec: object = SPEC) =>
  elementsOf(parseSection(`<section><x-chart id="c" style="left:0px;top:0px;width:900px;height:600px">${JSON.stringify(spec)}</x-chart></section>`))[0];

describe("a section's chart", () => {
  it("reads and changes the type, and drops stacking where it does not apply", () => {
    const c = chart();
    expect(chartType(c)).toBe("column");
    setStacked(c, true);
    expect(isStacked(c)).toBe(true);
    setChartType(c, "line");
    expect(chartType(c)).toBe("line");
    expect(isStacked(c)).toBe(false);
  });

  it("offers no type for one the panel cannot swap safely", () => {
    expect(chartType(chart({ ...SPEC, type: "pie" }))).toBeNull();
  });

  it("sets and clears the title, the legend and the data labels", () => {
    const c = chart();
    setChartTitle(c, "Revenue");
    expect(chartTitle(c)).toBe("Revenue");
    setChartTitle(c, "  ");
    expect(readSpec(c)).not.toHaveProperty("title");
    expect(showsLegend(c)).toBe(false);
    setLegend(c, true);
    expect(showsLegend(c)).toBe(true);
    setLabels(c, true);
    expect(showsLabels(c)).toBe(true);
    setLabels(c, false);
    expect(readSpec(c)).not.toHaveProperty("data_labels");
  });

  it("keeps a label setting the model wrote when labels are turned on again", () => {
    const c = chart({ ...SPEC, data_labels: { number_format: "#,##0" } });
    setLabels(c, true);
    expect(readSpec(c)?.data_labels).toEqual({ number_format: "#,##0" });
  });

  it("shows each series in its colour, PowerPoint's own until one is set", () => {
    const c = chart();
    expect(seriesOf(c)).toEqual([{ name: "Q2", colour: "#4472C4" }, { name: "Q3", colour: "#ED7D31" }]);
    setSeriesColour(c, 1, "#0e3a66");
    expect(seriesOf(c).map((s) => s.colour)).toEqual(["#4472C4", "#0E3A66"]);
    expect(readSpec(c)?.style).toEqual({ colors: ["#4472C4", "#0E3A66"] });
  });

  it("leaves a body that is not a JSON object alone", () => {
    const c = elementsOf(parseSection('<section><x-chart style="left:0px;top:0px;width:9px;height:9px">not json</x-chart></section>'))[0];
    setChartTitle(c, "x");
    expect(c.textContent).toBe("not json");
  });
});

describe("axes", () => {
  const chart = () => {
    const el = document.createElement("x-chart");
    el.textContent = JSON.stringify({ type: "column", categories: ["A"], series: [{ name: "S", values: [1] }] });
    return el;
  };

  it("keeps the axis titles in the chart's own JSON and drops an emptied one", () => {
    const el = chart();
    setAxisTitle(el, "category", "Region");
    setAxisTitle(el, "value", "Revenue");
    expect(readSpec(el)?.axis_titles).toEqual({ category: "Region", value: "Revenue" });
    setAxisTitle(el, "category", " ");
    setAxisTitle(el, "value", "");
    expect(readSpec(el)).not.toHaveProperty("axis_titles");
  });

  it("sets the value axis range and format, and clears them back to automatic", () => {
    const el = chart();
    setValueAxisSetting(el, "minimum", 0);
    setValueAxisSetting(el, "number_format", "0%");
    expect(readSpec(el)?.axes).toEqual({ value: { minimum: 0, number_format: "0%" } });
    expect(valueAxisSetting(el, "minimum")).toBe(0);
    setValueAxisSetting(el, "minimum", null);
    setValueAxisSetting(el, "number_format", null);
    expect(readSpec(el)).not.toHaveProperty("axes");
  });
});
