import { parseStyle, setStyle, styleText } from "./slideSource";

/** A table in a section: rows of `th` and `td`, and optionally a `colgroup` of column widths. */

export const tableRows = (table: Element) => Array.from(table.querySelectorAll("tr"));
const cellsOf = (row: Element) => Array.from(row.children).filter((c) => c.localName === "th" || c.localName === "td");

export const columnCount = (table: Element) => Math.max(1, ...tableRows(table).map((row) => cellsOf(row).length));

/** A copy of `cell` with no text, keeping its own style (a header's fill, an alignment). */
function blankLike(cell: Element): Element {
  const copy = cell.cloneNode(false) as Element;
  copy.removeAttribute("colspan");
  copy.removeAttribute("rowspan");
  return copy;
}

/** The table with `count` rows: new ones are copies of the last, blank; surplus ones go. At least one stays. */
export function setRowCount(table: Element, count: number) {
  const rows = tableRows(table);
  const want = Math.max(1, Math.round(count));
  for (let i = rows.length; i < want; i++) {
    const last = tableRows(table).at(-1)!;
    const row = last.cloneNode(false) as Element;
    for (const cell of cellsOf(last)) row.append(blankLike(cell));
    // A header row is not repeated: the new row is body.
    if (rows.length === 1 && hasHeader(table)) for (const cell of Array.from(row.children)) bodyCell(cell);
    last.after(row);
  }
  for (let i = rows.length; i > want; i--) tableRows(table).at(-1)!.remove();
}

/** A header cell as a body cell: `td`, without the header's own colours. */
function bodyCell(cell: Element): Element {
  const next = cell.ownerDocument.createElement("td");
  const style = parseStyle(cell.getAttribute("style") ?? "");
  style.delete("background");
  style.delete("color");
  if (style.size) next.setAttribute("style", styleText(style));
  cell.replaceWith(next);
  return next;
}

/** The table with `count` columns: a new one copies the last column's cells, blank. At least one stays. */
export function setColumnCount(table: Element, count: number) {
  const want = Math.max(1, Math.round(count));
  const have = columnCount(table);
  const group = table.querySelector("colgroup");
  for (const row of tableRows(table)) {
    const cells = cellsOf(row);
    for (let i = have; i < want; i++) row.append(blankLike(cells.at(-1) ?? cells[0]));
    for (let i = have; i > want; i--) cellsOf(row).at(-1)?.remove();
  }
  if (!group) return;
  const widths = Array.from(group.children).map(widthOf);
  const share = widths.length ? widths.reduce((a, b) => a + b, 0) / widths.length : 0;
  for (let i = have; i < want; i++) group.append(colElement(table, share));
  for (let i = have; i > want; i--) group.lastElementChild?.remove();
}

export function hasHeader(table: Element) {
  const first = tableRows(table)[0];
  return !!first && cellsOf(first).every((c) => c.localName === "th");
}

/** The first row as header cells (`th`, filled in `fill` with white text) or as body cells. */
export function setHeader(table: Element, on: boolean, fill: string) {
  const first = tableRows(table)[0];
  if (!first) return;
  for (const cell of cellsOf(first)) {
    if (on && cell.localName === "td") {
      const next = cell.ownerDocument.createElement("th");
      for (const attr of Array.from(cell.attributes)) next.setAttribute(attr.name, attr.value);
      next.append(...Array.from(cell.childNodes));
      cell.replaceWith(next);
      setStyle(next, "background", fill);
      setStyle(next, "color", "#FFFFFF");
    } else if (!on && cell.localName === "th") {
      const next = bodyCell(cell);
      next.append(...Array.from(cell.childNodes));
    }
  }
}

const widthOf = (col: Element) => Number.parseFloat(parseStyle(col.getAttribute("style") ?? "").get("width") ?? "") || 0;

function colElement(table: Element, width: number): Element {
  const col = table.ownerDocument.createElement("col");
  col.setAttribute("style", `width:${Math.round(width)}px`);
  return col;
}

/** Each column's width in px: the colgroup's, or an even share of `tableWidth`. */
export function columnWidths(table: Element, tableWidth: number): { widths: number[]; set: boolean } {
  const group = table.querySelector("colgroup");
  const cols = columnCount(table);
  const set = Array.from(group?.children ?? []).map(widthOf);
  if (set.length === cols && set.every((w) => w > 0)) return { widths: set, set: true };
  return { widths: Array.from({ length: cols }, () => tableWidth / cols), set: false };
}

/** Sets column `at` to `width` px; the other columns keep what they have, written out in full. */
export function setColumnWidth(table: Element, at: number, width: number, tableWidth: number) {
  const widths = columnWidths(table, tableWidth).widths.map((w, i) => (i === at ? Math.max(20, Math.round(width)) : Math.round(w)));
  table.querySelector("colgroup")?.remove();
  const group = table.ownerDocument.createElement("colgroup");
  for (const w of widths) group.append(colElement(table, w));
  table.insertBefore(group, table.firstChild);
}

/** The columns share the width evenly again. */
export const clearColumnWidths = (table: Element) => table.querySelector("colgroup")?.remove();
