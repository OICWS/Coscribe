/** A section's `<x-chart>` holds one JSON object; these read and change the keys the engine writes
 * into the native PowerPoint chart (title, legend, data labels, series colours, type). */

export type ChartType = "column" | "bar" | "line" | "area";
export const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "column", label: "Column" },
  { value: "bar", label: "Bar" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
];

/** PowerPoint's own series colours, which the chart takes when the JSON names none. */
const DEFAULT_SERIES_COLOURS = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"];

type Spec = Record<string, unknown>;

export function readSpec(el: Element): Spec | null {
  try {
    const spec: unknown = JSON.parse(el.textContent ?? "");
    return spec && typeof spec === "object" && !Array.isArray(spec) ? (spec as Spec) : null;
  } catch {
    return null;
  }
}

/** Applies `change` to the chart's JSON and writes it back; a body that is not one JSON object is
 * left alone. */
function update(el: Element, change: (spec: Spec) => void) {
  const spec = readSpec(el);
  if (!spec) return;
  change(spec);
  el.textContent = JSON.stringify(spec);
}

export function chartType(el: Element): ChartType | null {
  const type = readSpec(el)?.type;
  return CHART_TYPES.some((t) => t.value === type) ? (type as ChartType) : null;
}

export const setChartType = (el: Element, type: ChartType) =>
  update(el, (spec) => {
    spec.type = type;
    // Stacking is for columns and bars only.
    if (type !== "column" && type !== "bar") delete spec.grouping;
  });

export const isStacked = (el: Element) => readSpec(el)?.grouping === "stacked";

export const setStacked = (el: Element, stacked: boolean) =>
  update(el, (spec) => {
    if (stacked) spec.grouping = "stacked";
    else delete spec.grouping;
  });

export const chartTitle = (el: Element) => {
  const title = readSpec(el)?.title;
  return typeof title === "string" ? title : "";
};

export const setChartTitle = (el: Element, title: string) =>
  update(el, (spec) => {
    if (title.trim()) spec.title = title;
    else delete spec.title;
  });

export const showsLegend = (el: Element) => readSpec(el)?.show_legend === true;
export const setLegend = (el: Element, on: boolean) => update(el, (spec) => void (spec.show_legend = on));

export const showsLabels = (el: Element) => {
  const labels = readSpec(el)?.data_labels;
  return labels === true || (typeof labels === "object" && labels !== null);
};

/** Turning labels off drops the key, so a label setting the model wrote (a number format) goes with
 * it; turning them on keeps one that is there. */
export const setLabels = (el: Element, on: boolean) =>
  update(el, (spec) => {
    if (!on) delete spec.data_labels;
    else if (!showsLabels(el)) spec.data_labels = true;
  });

export interface SeriesInfo {
  name: string;
  colour: string;
}

/** Each series with the colour it is drawn in: the chart's own list, else PowerPoint's. */
export function seriesOf(el: Element): SeriesInfo[] {
  const spec = readSpec(el);
  const series = Array.isArray(spec?.series) ? (spec.series as Spec[]) : [];
  const style = spec?.style as Spec | undefined;
  const colours = Array.isArray(style?.colors) ? (style.colors as unknown[]) : [];
  return series.map((s, i) => {
    const colour = colours[i];
    return {
      name: typeof s.name === "string" && s.name ? s.name : `Series ${i + 1}`,
      colour: typeof colour === "string" ? colour.toUpperCase() : DEFAULT_SERIES_COLOURS[i % DEFAULT_SERIES_COLOURS.length],
    };
  });
}

export const setSeriesColour = (el: Element, index: number, colour: string) => {
  const current = seriesOf(el).map((s) => s.colour);
  update(el, (spec) => {
    const style = (spec.style && typeof spec.style === "object" ? spec.style : {}) as Spec;
    current[index] = colour.toUpperCase();
    style.colors = current;
    spec.style = style;
  });
};
