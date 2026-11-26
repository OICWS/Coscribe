import { type CSSProperties, type KeyboardEvent, type ReactNode, useLayoutEffect, useMemo, useRef, useState } from "react";
import { SpreadsheetDrawing } from "./SpreadsheetDrawing";
import { address, axis, cellKey, columnName, drawingBox, edge, indexAt, type Axis, type Cell, type CellFormat, type Merge, type Position, type Sheet, visible } from "./spreadsheetModel";

const HEADER_HEIGHT = 26;
const HEADER_WIDTH = 45;
// Rows and columns drawn past each edge, so a fast scroll shows cells, not white, before React catches up.
const OVERSCAN_ROWS = 12;
const OVERSCAN_COLUMNS = 4;

function formatCell(format: CellFormat | undefined, cell: Cell | undefined): CSSProperties {
  const horizontal = format?.align === "center" || format?.align === "centerContinuous" ? "center" :
    format?.align === "right" || (!format?.align && cell?.[5]) ? "right" : "left";
  const vertical = format?.vertical === "center" ? "center" : format?.vertical === "top" ? "start" : "end";
  const border = format?.border.map((defined) => defined ? "#596474" : "var(--sheet-grid)").join(" ");
  return {
    textAlign: horizontal, alignItems: vertical, borderColor: border,
    backgroundColor: format?.background ?? undefined,
    color: format?.color ?? undefined,
    fontSize: format?.fontSize ?? undefined,
    fontWeight: format?.bold ? 700 : undefined,
    fontStyle: format?.italic ? "italic" : undefined,
    textDecoration: format?.underline ? "underline" : undefined,
    whiteSpace: format?.wrap ? "pre-wrap" : "pre",
  };
}

function mergeAt(merges: Merge[], row: number, column: number) {
  return merges.find(([r, c, rEnd, cEnd]) => row >= r && row <= rEnd && column >= c && column <= cEnd);
}

function step(data: Axis, start: number, delta: number): number {
  if (delta === 0) return start;
  for (let i = start + delta; i > 0 && i < data.sizes.length; i += delta) {
    if (data.sizes[i]) return i;
  }
  return start;
}

function reveal(data: Axis, index: number, scroll: number, viewport: number): number {
  if (index <= data.frozen) return scroll;
  const start = edge(data, index);
  const frozen = edge(data, data.frozen + 1);
  const end = start + data.sizes[index];
  if (start < scroll + frozen) return start - frozen;
  if (end > scroll + viewport) return end - viewport;
  return scroll;
}

// Frozen panes and headers sit in sticky layers, so the browser keeps them in place on the same
// frame it scrolls the sheet. Positioning them from the scroll event lags a frame behind while the
// scrollbar is dragged, and they visibly shake.
type Layer = "body" | "top" | "left" | "corner";

function layerOf(row: number, column: number, rows: Axis, columns: Axis): Layer {
  const top = row <= rows.frozen;
  const left = column <= columns.frozen;
  return top && left ? "corner" : top ? "top" : left ? "left" : "body";
}

function cellBox(row: number, column: number, endRow: number, endColumn: number, rows: Axis, columns: Axis) {
  return {
    top: HEADER_HEIGHT + edge(rows, row),
    left: HEADER_WIDTH + edge(columns, column),
    width: edge(columns, endColumn + 1) - edge(columns, column),
    height: edge(rows, endRow + 1) - edge(rows, row),
  };
}

function Sticky({ top, left, z, children }: { top?: boolean; left?: boolean; z: number; children: ReactNode }) {
  return <div className="spreadsheet-layer" style={{ top: top ? 0 : undefined, left: left ? 0 : undefined, zIndex: z }}>{children}</div>;
}

function gridTiles({ sheet, selected, cells, rows, columns, visibleRows, visibleColumns, onSelect }: {
  sheet: Sheet;
  selected: Position;
  cells: Map<number, Cell>;
  rows: Axis;
  columns: Axis;
  visibleRows: number[];
  visibleColumns: number[];
  onSelect: (p: Position) => void;
}): Record<Layer, ReactNode[]> {
  const tiles: Record<Layer, ReactNode[]> = { body: [], top: [], left: [], corner: [] };
  const drawn = new Set<number>();
  for (const row of visibleRows) {
    const merges = sheet.merges.filter(([a, , b]) => row >= a && row <= b);
    for (const column of visibleColumns) {
      const [r, c, rEnd, cEnd] = mergeAt(merges, row, column) ?? [row, column, row, column];
      const key = cellKey(r, c);
      if (drawn.has(key)) continue;
      drawn.add(key);
      const cell = cells.get(key);
      const active = selected.row === r && selected.column === c;
      tiles[layerOf(r, c, rows, columns)].push(<div
        key={key} role="gridcell"
        aria-rowindex={r} aria-colindex={c} aria-selected={active}
        aria-rowspan={rEnd - r + 1} aria-colspan={cEnd - c + 1}
        aria-label={address({ row: r, column: c })} title={cell?.[2]}
        className={`spreadsheet-cell${active ? " spreadsheet-selected" : ""}`}
        onClick={() => onSelect({ row: r, column: c })}
        style={{ ...cellBox(r, c, rEnd, cEnd, rows, columns), ...formatCell(cell ? sheet.styles[cell[4]] : undefined, cell) }}
      ><span>{cell?.[2]}</span></div>);
    }
  }
  return tiles;
}

export function SpreadsheetGrid({ sheet }: { sheet: Sheet }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [viewport, setViewport] = useState({ width: 0, height: 0, x: 0, y: 0 });
  const [selection, setSelection] = useState<Position | null>(null);
  const rows = useMemo(() => axis(Math.max(sheet.rowCount + 12, sheet.freeze[0] + 12, 50, ...sheet.drawings.map((d) => d.end?.[0] ?? d.origin[0] + 24)), sheet.rowHeight, sheet.rows, sheet.freeze[0]), [sheet]);
  const columns = useMemo(() => axis(Math.max(sheet.columnCount + 8, sheet.freeze[1] + 8, 26, ...sheet.drawings.map((d) => d.end?.[1] ?? d.origin[1] + 12)), sheet.columnWidth, sheet.columns, sheet.freeze[1]), [sheet]);
  const cells = useMemo(() => new Map(sheet.cells.map((cell) => [cellKey(cell[0], cell[1]), cell])), [sheet]);
  const { width, height, x, y } = viewport;
  const visibleRows = visible(rows, y, Math.max(height - HEADER_HEIGHT, 0), OVERSCAN_ROWS);
  const visibleColumns = visible(columns, x, Math.max(width - HEADER_WIDTH, 0), OVERSCAN_COLUMNS);
  const first = selection ?? { row: indexAt(rows, 0), column: indexAt(columns, 0) };
  const firstMerge = mergeAt(sheet.merges, first.row, first.column);
  const selected = firstMerge ? { row: firstMerge[0], column: firstMerge[1] } : first;
  const selectedCell = cells.get(cellKey(selected.row, selected.column));
  const tiles = gridTiles({ sheet, selected, cells, rows, columns, visibleRows, visibleColumns, onSelect: setSelection });

  useLayoutEffect(() => {
    const node = scroller.current;
    if (!node) return;
    const update = () => setViewport({ width: node.clientWidth, height: node.clientHeight, x: node.scrollLeft, y: node.scrollTop });
    const resize = new ResizeObserver(update);
    resize.observe(node);
    node.addEventListener("scroll", update, { passive: true });
    update();
    return () => {
      resize.disconnect();
      node.removeEventListener("scroll", update);
    };
  }, []);

  function navigate(event: KeyboardEvent) {
    const directions: Record<string, [number, number]> = {
      ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1],
    };
    const direction = directions[event.key];
    const node = scroller.current;
    if (!direction || !node) return;
    event.preventDefault();
    const [dy, dx] = direction;
    const rawRow = step(rows, dy > 0 ? firstMerge?.[2] ?? selected.row : selected.row, dy);
    const rawColumn = step(columns, dx > 0 ? firstMerge?.[3] ?? selected.column : selected.column, dx);
    const merge = mergeAt(sheet.merges, rawRow, rawColumn);
    const row = merge?.[0] ?? rawRow;
    const column = merge?.[1] ?? rawColumn;
    setSelection({ row, column });
    node.scrollTop = reveal(rows, row, y, height - HEADER_HEIGHT);
    node.scrollLeft = reveal(columns, column, x, width - HEADER_WIDTH);
  }

  const tail = sheet.rowsClipped || rows.sizes.length <= sheet.rowCount || columns.sizes.length <= sheet.columnCount;
  return <>
    <div className="spreadsheet-formula">
      <span aria-label="Selected cell">{address(selected)}</span>
      <span aria-hidden="true">ƒx</span>
      <input readOnly aria-label="Cell formula or value" value={selectedCell?.[3] ?? ""} />
    </div>
    <div ref={scroller} className="spreadsheet-scroll" role="grid" aria-label={sheet.name}
      aria-rowcount={rows.sizes.length - 1} aria-colcount={columns.sizes.length - 1}
      tabIndex={0} onKeyDown={navigate}>
      <div className="spreadsheet-canvas" style={{ width: columns.total + HEADER_WIDTH, height: rows.total + HEADER_HEIGHT }}>
        {tiles.body}
        {sheet.drawings.map((drawing, i) => {
          const { top, left, width: w, height: h } = drawingBox(drawing, rows, columns);
          if (w <= 0 || h <= 0 || left >= columns.total || top >= rows.total) return null;
          return <div className="spreadsheet-drawing" key={i} style={{
            top: top + HEADER_HEIGHT, left: left + HEADER_WIDTH, width: w, height: h,
          }}><SpreadsheetDrawing drawing={drawing} /></div>;
        })}
        <Sticky top z={5}>
          {tiles.top}
          {rows.frozen > 0 && <div aria-hidden="true" className="spreadsheet-freeze-row"
            style={{ top: HEADER_HEIGHT + edge(rows, rows.frozen + 1), left: 0, width: columns.total + HEADER_WIDTH }} />}
        </Sticky>
        <Sticky left z={6}>
          {tiles.left}
          {columns.frozen > 0 && <div aria-hidden="true" className="spreadsheet-freeze-col"
            style={{ top: 0, left: HEADER_WIDTH + edge(columns, columns.frozen + 1), height: rows.total + HEADER_HEIGHT }} />}
        </Sticky>
        <Sticky top left z={7}>{tiles.corner}</Sticky>
        <Sticky top z={8}>
          {visibleColumns.filter((column) => column > columns.frozen).map((column) => <div key={column} role="columnheader"
            className="spreadsheet-header" data-selected={column === selected.column} style={{
              top: 0, left: HEADER_WIDTH + edge(columns, column), width: columns.sizes[column], height: HEADER_HEIGHT,
            }}>{columnName(column)}</div>)}
        </Sticky>
        <Sticky left z={9}>
          {visibleRows.filter((row) => row > rows.frozen).map((row) => <div key={row} role="rowheader"
            className="spreadsheet-header" data-selected={row === selected.row} style={{
              top: HEADER_HEIGHT + edge(rows, row), left: 0, width: HEADER_WIDTH, height: rows.sizes[row],
            }}>{row}</div>)}
        </Sticky>
        <Sticky top left z={10}>
          {visibleColumns.filter((column) => column <= columns.frozen).map((column) => <div key={column} role="columnheader"
            className="spreadsheet-header" data-selected={column === selected.column} style={{
              top: 0, left: HEADER_WIDTH + edge(columns, column), width: columns.sizes[column], height: HEADER_HEIGHT,
            }}>{columnName(column)}</div>)}
          {visibleRows.filter((row) => row <= rows.frozen).map((row) => <div key={row} role="rowheader"
            className="spreadsheet-header" data-selected={row === selected.row} style={{
              top: HEADER_HEIGHT + edge(rows, row), left: 0, width: HEADER_WIDTH, height: rows.sizes[row],
            }}>{row}</div>)}
          <div aria-hidden="true" className="spreadsheet-header spreadsheet-corner" style={{ top: 0, left: 0, width: HEADER_WIDTH, height: HEADER_HEIGHT }} />
        </Sticky>
      </div>
    </div>
    {tail && <div className="spreadsheet-note">This workbook has more rows or columns than the preview can show.</div>}
  </>;
}
