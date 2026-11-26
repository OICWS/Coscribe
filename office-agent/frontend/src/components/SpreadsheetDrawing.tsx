import type { Drawing } from "./spreadsheetModel";

type Chart = Extract<Drawing, { kind: "chart" }>;

const COLOURS = ["#396d9b", "#bf683a", "#43857c", "#79569b", "#aa8a35", "#5982a9"];

function range(values: number[], includeZero: boolean): [number, number] {
  const low = Math.min(...values, ...(includeZero ? [0] : []));
  const high = Math.max(...values, ...(includeZero ? [0] : []));
  return low === high ? [low - 1, high + 1] : [low, high];
}

function Plot({ chart }: { chart: Chart }) {
  const { series, labels, plot } = chart;
  const values = series.flat().filter((value): value is number => value !== null);
  if (!plot || !values.length) {
    return <div className="grid h-full place-content-center px-3 text-center text-xs text-slate-500">Open in Excel to view this chart.</div>;
  }
  const horizontal = plot === "bar";
  const natural = range(values, plot !== "line");
  const bounded = [chart.min ?? natural[0], chart.max ?? natural[1]];
  const [low, high] = bounded[0] < bounded[1] ? bounded : natural;
  const left = horizontal ? 78 : 55;
  const top = 12;
  const width = 485 - left;
  const height = 182;
  const count = Math.max(labels.length, ...series.map((line) => line.length));
  const step = (horizontal ? height : width) / count;
  const scale = (n: number) => Math.min(1, Math.max(0, (n - low) / (high - low)));
  const axis = (n: number) => horizontal ? left + scale(n) * width : top + (1 - scale(n)) * height;
  const text = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 });

  return <svg viewBox="0 0 500 230" className="min-h-0 flex-1" aria-hidden="true">
    {Array.from({ length: 5 }, (_, i) => {
      const value = low + (high - low) * i / 4;
      const point = axis(value);
      return horizontal ? <g key={i}>
        <line x1={point} x2={point} y1={top} y2={top + height} stroke="#d9dfe6" />
        <text x={point} y={213} textAnchor="middle">{text.format(value)}</text>
      </g> : <g key={i}>
        <line x1={left} x2={left + width} y1={point} y2={point} stroke="#d9dfe6" />
        <text x={left - 6} y={point + 4} textAnchor="end">{text.format(value)}</text>
      </g>;
    })}
    {series.map((line, index) => {
      const fill = COLOURS[index % COLOURS.length];
      if (plot === "line") {
        const path = line.map((value, i) => value === null ? "" :
          `${i === 0 || line[i - 1] === null ? "M" : "L"} ${left + (i + 0.5) * step} ${axis(value)}`).join(" ");
        return <path key={index} d={path} stroke={fill} fill="none" strokeWidth={2.5} />;
      }
      const thickness = step * 0.76 / series.length;
      return <g key={index} fill={fill}>
        {line.map((value, i) => {
          if (value === null) return null;
          const category = (i + 0.12) * step + thickness * index;
          const start = Math.min(axis(0), axis(value));
          const length = Math.abs(axis(0) - axis(value));
          return horizontal
            ? <rect key={i} x={start} y={top + category} width={length} height={thickness} />
            : <rect key={i} x={left + category} y={start} width={thickness} height={length} />;
        })}
      </g>;
    })}
    {Array.from({ length: count }, (_, i) => {
      if (i % Math.ceil(count / (horizontal ? 10 : 7))) return null;
      const label = labels[i] || String(i + 1);
      return horizontal
        ? <text key={i} x={left - 6} y={top + (i + 0.5) * step + 4} textAnchor="end">{label.slice(0, 10)}</text>
        : <text key={i} x={left + (i + 0.5) * step} y={213} textAnchor="middle">{label.slice(0, 12)}</text>;
    })}
  </svg>;
}

export function SpreadsheetDrawing({ drawing }: { drawing: Drawing }) {
  if (drawing.kind === "image") {
    return <img src={drawing.src} alt="Image embedded in workbook" draggable={false} className="h-full w-full" />;
  }
  return <figure aria-label={drawing.title || "Worksheet chart"} className="spreadsheet-chart">
    {drawing.title && <figcaption title={drawing.title}>{drawing.title}</figcaption>}
    <Plot chart={drawing} />
  </figure>;
}
