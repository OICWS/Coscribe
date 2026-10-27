/** A Doc's chart block drawn as SVG: a fenced `chart` block whose first line is the kind (`bar`, `line` or `pie`)
 * and an optional title, and whose other lines are a pipe table (category column, then one column per series).
 * The server parses the same text (`tools/office/doc/chart.py`); a block this cannot draw is shown as its source. */

export interface Chart {
  kind: "bar" | "line" | "pie";
  title: string;
  categories: string[];
  series: { name: string; values: number[] }[];
}

const cells = (line: string) =>
  line
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((cell) => cell.trim());

const isSeparator = (row: string[]) => row.every((cell) => /^:?-{3,}:?$/.test(cell));

/** The chart a block holds, or a short sentence that says why it is not one. */
export function parseChart(block: string): Chart | string {
  const lines = block.trim().split("\n");
  const body = /^(```|~~~)/.test(lines[lines.length - 1].trim()) ? lines.slice(1, -1) : lines.slice(1);
  const [first = "", ...data] = body.filter((line) => line.trim());
  const kind = first.trim().split(/\s+/)[0]?.toLowerCase();
  if (kind !== "bar" && kind !== "line" && kind !== "pie") return "The first line of a chart is bar, line or pie, then a title.";
  const rows = data.map(cells).filter((row) => !isSeparator(row));
  if (rows.length < 2 || rows[0].length < 2) return "A chart needs a header row and a data row, with a category column and a data column.";
  const [header, ...rest] = rows;
  const series = header.slice(1).map((name, i) => ({ name, values: rest.map((row) => Number((row[i + 1] ?? "").replace(/,/g, ""))) }));
  if (series.some((s) => s.values.some((v) => Number.isNaN(v)))) return "A chart's data cells must be numbers.";
  if (kind === "pie" && series.length > 1) return "A pie chart has one data column besides the category column.";
  return { kind, title: first.trim().slice(kind.length).trim(), categories: rest.map((row) => row[0]), series };
}

const COLORS = ["#4f6ef7", "#12a88a", "#f59f00", "#e0508a", "#8a63e8", "#6b7280"];
const W = 640;
const H = 300;
const esc = (text: string) => text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);
const num = (value: number) => (Math.abs(value) >= 1000 ? value.toLocaleString("en-US", { maximumFractionDigits: 1 }) : String(Math.round(value * 100) / 100));

function legend(names: string[]): string {
  if (names.length < 2) return "";
  return names.map((name, i) => `<g transform="translate(${70 + i * 130},${H - 10})"><rect width="10" height="10" y="-9" rx="2" fill="${COLORS[i % COLORS.length]}"/><text x="16" fill="currentColor" font-size="12">${esc(name)}</text></g>`).join("");
}

function axes(chart: Chart): { top: number; bottom: number; max: number; y: (v: number) => number; grid: string } {
  const values = chart.series.flatMap((s) => s.values);
  const max = Math.max(0, ...values) || 1;
  const min = Math.min(0, ...values);
  const top = 34;
  const bottom = H - 44;
  const y = (v: number) => bottom - ((v - min) / (max - min || 1)) * (bottom - top);
  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map((f) => {
      const v = min + (max - min) * f;
      return `<line x1="60" x2="${W - 10}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" stroke-opacity="0.12"/><text x="54" y="${y(v) + 4}" text-anchor="end" fill="currentColor" fill-opacity="0.6" font-size="11">${num(v)}</text>`;
    })
    .join("");
  return { top, bottom, max, y, grid };
}

function bars(chart: Chart): string {
  const { y, grid } = axes(chart);
  const slot = (W - 80) / chart.categories.length;
  const bar = Math.min(40, (slot * 0.7) / chart.series.length);
  const marks = chart.categories
    .map((category, c) => {
      const left = 60 + slot * c + (slot - bar * chart.series.length) / 2;
      const rects = chart.series.map((s, i) => `<rect x="${left + bar * i}" y="${Math.min(y(s.values[c]), y(0))}" width="${bar - 2}" height="${Math.abs(y(s.values[c]) - y(0))}" rx="2" fill="${COLORS[i % COLORS.length]}"><title>${esc(s.name)}: ${num(s.values[c])}</title></rect>`).join("");
      return `${rects}<text x="${60 + slot * c + slot / 2}" y="${H - 28}" text-anchor="middle" fill="currentColor" font-size="12">${esc(category)}</text>`;
    })
    .join("");
  return grid + marks;
}

function lines(chart: Chart): string {
  const { y, grid } = axes(chart);
  const step = (W - 80) / chart.categories.length;
  const x = (c: number) => 60 + step * c + step / 2;
  const paths = chart.series
    .map((s, i) => {
      const color = COLORS[i % COLORS.length];
      const points = s.values.map((v, c) => `${x(c)},${y(v)}`).join(" ");
      return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>${s.values.map((v, c) => `<circle cx="${x(c)}" cy="${y(v)}" r="3.5" fill="${color}"><title>${esc(s.name)}: ${num(v)}</title></circle>`).join("")}`;
    })
    .join("");
  const labels = chart.categories.map((category, c) => `<text x="${x(c)}" y="${H - 28}" text-anchor="middle" fill="currentColor" font-size="12">${esc(category)}</text>`).join("");
  return grid + paths + labels;
}

function pie(chart: Chart): string {
  const values = chart.series[0].values.map((v) => Math.max(0, v));
  const total = values.reduce((a, b) => a + b, 0) || 1;
  const cx = 150;
  const cy = 160;
  const r = 100;
  let angle = -Math.PI / 2;
  const slices = values
    .map((v, i) => {
      const next = angle + (v / total) * Math.PI * 2;
      const large = next - angle > Math.PI ? 1 : 0;
      const d = values.length === 1 ? `M${cx - r},${cy}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0` : `M${cx},${cy}L${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(next)},${cy + r * Math.sin(next)}Z`;
      angle = next;
      return `<path d="${d}" fill="${COLORS[i % COLORS.length]}" stroke="var(--bg)" stroke-width="2"><title>${esc(chart.categories[i])}: ${num(v)}</title></path>`;
    })
    .join("");
  const key = chart.categories.map((category, i) => `<g transform="translate(300,${70 + i * 24})"><rect width="12" height="12" y="-10" rx="2" fill="${COLORS[i % COLORS.length]}"/><text x="20" fill="currentColor" font-size="13">${esc(category)} · ${num(values[i])}</text></g>`).join("");
  return slices + key;
}

/** The chart as an SVG string; every text in it is escaped. */
export function chartSvg(chart: Chart): string {
  const body = chart.kind === "bar" ? bars(chart) : chart.kind === "line" ? lines(chart) : pie(chart);
  const title = chart.title ? `<text x="${W / 2}" y="20" text-anchor="middle" fill="currentColor" font-size="14" font-weight="600">${esc(chart.title)}</text>` : "";
  const key = chart.kind === "pie" ? "" : legend(chart.series.map((s) => s.name));
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(chart.title || `${chart.kind} chart`)}" xmlns="http://www.w3.org/2000/svg">${title}${body}${key}</svg>`;
}
