/** A Word chart part (DrawingML chart xml) drawn as an SVG, for the places a browser cannot show it. */

type ChartSeries = { name: string; values: number[]; color: string | null; pointColors: (string | null)[] };
type ChartModel = {
  kind: "bar" | "column" | "line" | "area" | "pie";
  stacked: boolean;
  title: string;
  categories: string[];
  series: ChartSeries[];
  /** A single series drawn with one colour per point, as Word does unless the file says otherwise. */
  varyColors: boolean;
  /** The value axis range the file fixes, if it does. */
  axis: { min?: number; max?: number; step?: number };
};

const PALETTE = ["#4f81bd", "#c0504d", "#9bbb59", "#8064a2", "#4bacc6", "#f79646", "#2c4d75", "#772c2a"];
const INK = "#444";
const GRID = "#d0d0d0";

const kids = (el: Element | null | undefined, name: string): Element[] =>
  el ? [...el.children].filter((c) => c.localName === name) : [];
const first = (el: Element | null | undefined, name: string): Element | null => kids(el, name)[0] ?? null;
const within = (el: Element | null | undefined, name: string): Element | null =>
  el?.getElementsByTagNameNS("*", name)[0] ?? null;

function points(cache: Element | null): string[] {
  const out: string[] = [];
  for (const pt of kids(cache, "pt")) out[Number(pt.getAttribute("idx"))] = within(pt, "v")?.textContent ?? "";
  return Array.from(out, (v) => v ?? "");
}

function textOf(node: Element | null): string {
  return node ? [...node.getElementsByTagNameNS("*", "t")].map((t) => t.textContent ?? "").join("") : "";
}

function parseChart(xml: string): ChartModel | null {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const plot = within(doc.documentElement, "plotArea");
  const type = kids(plot, "barChart")[0] ?? kids(plot, "bar3DChart")[0] ?? kids(plot, "lineChart")[0] ?? kids(plot, "areaChart")[0] ?? kids(plot, "pieChart")[0] ?? kids(plot, "doughnutChart")[0] ?? kids(plot, "pie3DChart")[0];
  if (!plot || !type) return null;
  const name = type.localName;
  const horizontal = first(type, "barDir")?.getAttribute("val") === "bar";
  const grouping = first(type, "grouping")?.getAttribute("val") ?? "";
  const kind: ChartModel["kind"] = name.startsWith("bar") ? (horizontal ? "bar" : "column") : name.startsWith("line") ? "line" : name.startsWith("area") ? "area" : "pie";
  const series = kids(type, "ser").map((ser, i): ChartSeries => {
    const color = within(first(ser, "spPr"), "srgbClr")?.getAttribute("val");
    const pointColors: (string | null)[] = [];
    for (const point of kids(ser, "dPt")) {
      const own = within(first(point, "spPr"), "srgbClr")?.getAttribute("val");
      pointColors[Number(first(point, "idx")?.getAttribute("val"))] = own ? `#${own}` : null;
    }
    return {
      name: within(first(ser, "tx"), "v")?.textContent ?? `Series ${i + 1}`,
      values: points(within(first(ser, "val"), "numCache")).map((v) => Number(v) || 0),
      color: color ? `#${color}` : null,
      pointColors,
    };
  });
  const scaling = first(first(plot, "valAx"), "scaling");
  const number = (el: Element | null | undefined) => (el?.getAttribute("val") != null ? Number(el.getAttribute("val")) : undefined);
  const catRef = first(first(type, "ser"), "cat");
  const categories = points(within(catRef, "strCache") ?? within(catRef, "numCache"));
  const hasTitle = first(within(doc.documentElement, "chart"), "autoTitleDeleted")?.getAttribute("val") !== "1";
  return {
    kind,
    stacked: grouping === "stacked" || grouping === "percentStacked",
    title: hasTitle ? textOf(first(within(doc.documentElement, "chart"), "title")) : "",
    categories,
    series,
    varyColors: series.length === 1 && first(type, "varyColors")?.getAttribute("val") !== "0",
    axis: { min: number(first(scaling, "min")), max: number(first(scaling, "max")), step: number(first(first(plot, "valAx"), "majorUnit")) },
  };
}

function niceMax(max: number, fixed: ChartModel["axis"]): { top: number; step: number } {
  if (fixed.max !== undefined && fixed.step) return { top: fixed.max, step: fixed.step };
  if (max <= 0) return { top: 1, step: 0.2 };
  const power = 10 ** Math.floor(Math.log10(max / 10));
  const step = ([1, 2, 5, 10].map((m) => m * power).find((candidate) => Math.ceil(max / candidate) <= 10) ?? max) * 1;
  return { top: fixed.max ?? Math.ceil(max / step) * step, step };
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const fmt = (n: number) => (Math.abs(n) >= 1000 ? n.toLocaleString("en-US") : String(Math.round(n * 100) / 100));
const colorOf = (s: ChartSeries, i: number) => s.color ?? PALETTE[i % PALETTE.length]!;
/** The colour of one bar or slice: its own, else the series' (or the palette's, a colour per point). */
const pointColor = (model: ChartModel, s: ChartSeries, series: number, point: number) =>
  s.pointColors[point] ?? (model.varyColors ? PALETTE[point % PALETTE.length]! : colorOf(s, series));

function pie(model: ChartModel, w: number, h: number, top: number): string {
  const values = model.series[0]?.values ?? [];
  const total = values.reduce((a, b) => a + Math.max(0, b), 0) || 1;
  const r = Math.min(w * 0.3, (h - top) / 2 - 8);
  const cx = w * 0.4;
  const cy = top + (h - top) / 2;
  let angle = -Math.PI / 2;
  const slices = values.map((v, i) => {
    const sweep = (Math.max(0, v) / total) * Math.PI * 2;
    const a1 = angle + sweep;
    const large = sweep > Math.PI ? 1 : 0;
    const d = `M${cx},${cy} L${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)} A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(a1)},${cy + r * Math.sin(a1)} Z`;
    angle = a1;
    return `<path d="${d}" fill="${model.series[0] ? pointColor(model, model.series[0], 0, i) : PALETTE[0]}" stroke="#fff"/>`;
  });
  const legend = (model.categories.length ? model.categories : values.map((_, i) => `${i + 1}`)).map(
    (c, i) => `<rect x="${w * 0.72}" y="${top + 12 + i * 20}" width="10" height="10" fill="${PALETTE[i % PALETTE.length]}"/><text x="${w * 0.72 + 16}" y="${top + 21 + i * 20}" font-size="11" fill="${INK}">${esc(c)}</text>`,
  );
  return slices.join("") + legend.join("");
}

function axes(model: ChartModel, w: number, h: number, top: number): string {
  const horizontal = model.kind === "bar";
  const count = Math.max(model.categories.length, ...model.series.map((s) => s.values.length), 1);
  const sums = Array.from({ length: count }, (_, i) =>
    model.stacked ? model.series.reduce((a, s) => a + Math.max(0, s.values[i] ?? 0), 0) : Math.max(0, ...model.series.map((s) => s.values[i] ?? 0)),
  );
  const { top: max, step } = niceMax(Math.max(...sums), model.axis);
  const left = 52;
  const right = 12;
  const legendH = model.series.length > 1 ? 24 : 0;
  const bottom = 26 + legendH;
  const px = left;
  const py = top + 6;
  const pw = w - left - right;
  const ph = h - top - 6 - bottom;
  const out: string[] = [];
  const ticks = Math.round(max / step);
  for (let t = 0; t <= ticks; t++) {
    const v = t * step;
    if (horizontal) {
      const x = px + (v / max) * pw;
      out.push(`<line x1="${x}" y1="${py}" x2="${x}" y2="${py + ph}" stroke="${GRID}"/><text x="${x}" y="${py + ph + 14}" font-size="11" text-anchor="middle" fill="${INK}">${fmt(v)}</text>`);
    } else {
      const y = py + ph - (v / max) * ph;
      out.push(`<line x1="${px}" y1="${y}" x2="${px + pw}" y2="${y}" stroke="${GRID}"/><text x="${px - 6}" y="${y + 4}" font-size="11" text-anchor="end" fill="${INK}">${fmt(v)}</text>`);
    }
  }
  const slot = (horizontal ? ph : pw) / count;
  const group = slot * 0.7;
  model.categories.slice(0, count).forEach((c, i) => {
    const mid = (i + 0.5) * slot;
    out.push(horizontal
      ? `<text x="${px - 6}" y="${py + mid + 4}" font-size="11" text-anchor="end" fill="${INK}">${esc(c)}</text>`
      : `<text x="${px + mid}" y="${py + ph + 14}" font-size="11" text-anchor="middle" fill="${INK}">${esc(c)}</text>`);
  });
  const along = (v: number) => (v / max) * (horizontal ? pw : ph);
  const place = (centre: number, from: number, to: number, size: number, color: string) =>
    horizontal
      ? `<rect x="${px + from}" y="${py + centre - size / 2}" width="${Math.max(0, to - from)}" height="${size}" fill="${color}"/>`
      : `<rect x="${px + centre - size / 2}" y="${py + ph - to}" width="${size}" height="${Math.max(0, to - from)}" fill="${color}"/>`;
  if (model.kind === "bar" || model.kind === "column") {
    const bar = model.stacked ? group : group / model.series.length;
    for (let i = 0; i < count; i++) {
      let base = 0;
      model.series.forEach((s, j) => {
        const v = Math.max(0, s.values[i] ?? 0);
        const centre = (i + 0.5) * slot + (model.stacked ? 0 : (j - (model.series.length - 1) / 2) * bar);
        const from = model.stacked ? base : 0;
        const to = model.stacked ? base + along(v) : along(v);
        out.push(place(centre, from, to, bar, pointColor(model, s, j, i)));
        base = to;
      });
    }
  } else {
    model.series.forEach((s, j) => {
      const color = colorOf(s, j);
      const pts = s.values.map((v, i) => [px + (i + 0.5) * slot, py + ph - along(v)] as const);
      const line = pts.map(([x, y]) => `${x},${y}`).join(" ");
      if (model.kind === "area" && pts.length) {
        out.push(`<polygon points="${px + 0.5 * slot},${py + ph} ${line} ${px + (pts.length - 0.5) * slot},${py + ph}" fill="${color}" fill-opacity="0.6"/>`);
      } else {
        out.push(`<polyline points="${line}" fill="none" stroke="${color}" stroke-width="2.25"/>`);
        pts.forEach(([x, y]) => out.push(`<circle cx="${x}" cy="${y}" r="3" fill="${color}"/>`));
      }
    });
  }
  out.push(`<line x1="${px}" y1="${py}" x2="${px}" y2="${py + ph}" stroke="#888"/><line x1="${px}" y1="${py + ph}" x2="${px + pw}" y2="${py + ph}" stroke="#888"/>`);
  if (legendH) {
    let x = px;
    model.series.forEach((s, j) => {
      out.push(`<rect x="${x}" y="${h - 16}" width="10" height="10" fill="${colorOf(s, j)}"/><text x="${x + 14}" y="${h - 7}" font-size="11" fill="${INK}">${esc(s.name)}</text>`);
      x += 30 + s.name.length * 8;
    });
  }
  return out.join("");
}

/** The chart as an <svg> string of the given pixel size; null when the xml is not a chart this draws. */
export function chartSvg(xml: string, width: number, height: number): string | null {
  const model = parseChart(xml);
  if (!model || !model.series.length) return null;
  const top = model.title ? 28 : 6;
  const title = model.title ? `<text x="${width / 2}" y="20" font-size="14" font-weight="bold" text-anchor="middle" fill="#222">${esc(model.title)}</text>` : "";
  const body = model.kind === "pie" ? pie(model, width, height, top) : axes(model, width, height, top);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" font-family="sans-serif"><rect width="${width}" height="${height}" fill="#fff" stroke="#d9d9d9"/>${title}${body}</svg>`;
}
