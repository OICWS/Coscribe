type Span = [start: number, end: number, size: number];
export type Cell = [row: number, column: number, display: string, raw: string, style: number, numeric: boolean];
export type Merge = [firstRow: number, firstColumn: number, lastRow: number, lastColumn: number];
export type CellFormat = {
  background: string | null;
  color: string | null;
  fontSize: number | null;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  wrap: boolean;
  align: string | null;
  vertical: string | null;
  border: [boolean, boolean, boolean, boolean];
};
type Anchor = [row: number, column: number, rowOffset: number, columnOffset: number];
export type Drawing = { origin: Anchor; end?: Anchor; size?: [number, number] } & (
  | { kind: "image"; src: string }
  | { kind: "chart"; plot: "col" | "bar" | "line" | null; title: string; min: number | null; max: number | null; series: (number | null)[][]; labels: string[] }
);
export type Sheet = {
  name: string;
  rowCount: number;
  columnCount: number;
  rowsClipped: boolean;
  freeze: [number, number];
  rowHeight: number;
  columnWidth: number;
  rows: Span[];
  columns: Span[];
  merges: Merge[];
  cells: Cell[];
  styles: Record<number, CellFormat>;
  drawings: Drawing[];
};
export type WorkbookPreview = { sheets: string[]; sheet: Sheet | null; error?: string };

export type Position = { row: number; column: number };
export type Axis = { offsets: Float64Array; sizes: Uint16Array; frozen: number; total: number };

const MAX_SCROLL_SIZE = 28_000_000;

export function axis(count: number, size: number, spans: Span[], freeze: number): Axis {
  const sizes = new Uint16Array(count + 1);
  sizes.fill(size, 1);
  for (const [from, to, width] of spans) {
    sizes.fill(width, Math.max(1, from), Math.min(count, to) + 1);
  }
  const offsets = new Float64Array(count + 1);
  let total = 0;
  for (let i = 1; i <= count; i++) {
    offsets[i] = total;
    total += sizes[i];
    if (total > MAX_SCROLL_SIZE) return axis(i - 1, size, spans, freeze);
  }
  return { offsets, sizes, frozen: Math.min(freeze, count), total };
}

export function indexAt(data: Axis, pixel: number): number {
  let low = 1;
  let high = data.sizes.length - 1;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (data.offsets[mid] + data.sizes[mid] <= pixel) low = mid + 1;
    else high = mid;
  }
  return low;
}

export function edge(data: Axis, index: number): number {
  return data.offsets[index] ?? data.total;
}

export function visible(data: Axis, scroll: number, size: number): number[] {
  const indexes = [];
  const start = Math.max(data.frozen + 1, indexAt(data, scroll + edge(data, data.frozen + 1)));
  const end = Math.min(data.sizes.length - 1, indexAt(data, scroll + size) + 1);
  for (let i = 1; i <= data.frozen && edge(data, i) < size; i++) {
    if (data.sizes[i]) indexes.push(i);
  }
  for (let i = start; i <= end; i++) {
    if (data.sizes[i]) indexes.push(i);
  }
  return indexes;
}

export function columnName(column: number): string {
  let name = "";
  for (let value = column; value > 0; value = Math.floor((value - 1) / 26)) {
    name = String.fromCharCode(65 + (value - 1) % 26) + name;
  }
  return name;
}

export const address = ({ row, column }: Position) => `${columnName(column)}${row}`;
export const cellKey = (row: number, column: number) => row * 16_385 + column;

export function drawingBox(drawing: Drawing, rows: Axis, columns: Axis) {
  const point = ([row, column, y, x]: Anchor) => [edge(columns, column) + x, edge(rows, row) + y];
  const [left, top] = point(drawing.origin);
  const end = drawing.end && point(drawing.end);
  const [width, height] = drawing.size ?? (end ? [end[0] - left, end[1] - top] : [0, 0]);
  return { left, top, width, height };
}
