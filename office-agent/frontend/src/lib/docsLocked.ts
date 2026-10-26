import { Node } from "@tiptap/core";
import type { DOMOutputSpec } from "@tiptap/pm/model";
import { cellStyle, lookStyle, runStyle, type CellLook, type Look, type RunLook, type TableLook } from "./docsLook";
import { chartSvg } from "./docxChart";

const LOCKED_LABELS: Record<string, string> = {
  comment: "Comment",
  "tracked change": "Tracked change",
  field: "Contents or field",
  "image or drawing": "Picture or drawing",
  note: "Footnote",
  "page break": "Page break",
  "section break": "Section break",
  "internal link": "Link inside the document",
  table: "Table",
  "deep list": "List",
};

interface GridCell {
  look?: CellLook;
  span?: number;
  down?: number;
  paras: { look?: Look; runs: RunLook[] }[];
}
export interface Grid extends Omit<TableLook, "rows"> {
  rows: { h?: number; cells: GridCell[] }[];
}

const PX_PER_PT = 96 / 72;

function runs(items: RunLook[]): DOMOutputSpec[] {
  return items.map((run) => ["span", { style: runStyle(run) }, run.t] as DOMOutputSpec);
}

/** A table the editor does not change, drawn the way the file lays it out. */
function gridTable(grid: Grid): DOMOutputSpec {
  const width = (grid.widths ?? []).reduce((a, b) => a + b, 0);
  const columns = Math.max(...grid.rows.map((row) => row.cells.reduce((n, cell) => n + (cell.span ?? 1), 0)), 1);
  const rows = grid.rows.map((row, r): DOMOutputSpec => {
    let column = 0;
    const cells = row.cells.map((cell): DOMOutputSpec => {
      const style = cellStyle(cell.look, { ...grid, rows: [] }, { r, c: column, rows: grid.rows.length, cols: columns });
      column += cell.span ?? 1;
      const content = cell.paras.map((p): DOMOutputSpec => ["p", { style: lookStyle(p.look) }, ...(p.runs.length ? runs(p.runs) : [["br"] as DOMOutputSpec])]);
      return ["td", { style, ...(cell.span ? { colspan: String(cell.span) } : {}), ...(cell.down ? { rowspan: String(cell.down) } : {}) }, ...content];
    });
    return ["tr", row.h ? { style: `height:${row.h}pt` } : {}, ...cells];
  });
  const cols = (grid.widths ?? []).map((w): DOMOutputSpec => ["col", { style: `width:${w}pt` }]);
  return ["table", { style: `border-collapse:collapse;table-layout:fixed;${width ? `width:${width}pt` : "width:100%"}` }, ["colgroup", {}, ...cols], ["tbody", {}, ...rows]];
}

/** A block the editor cannot change: drawn as the file has it where it can be, else a grey line; kept as it is, deleted only by the person. */
export const LockedBlock = Node.create({
  name: "lockedBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,
  addAttributes() {
    return { what: { default: "" }, text: { default: "" }, images: { default: [] as string[] }, grid: { default: null }, chart: { default: null }, look: { default: null }, upload: { default: "" }, picture: { default: null } };
  },
  parseHTML: () => [{ tag: "div.docs-locked" }],
  renderHTML: ({ node }) => {
    const images = node.attrs.images as string[];
    const width = (node.attrs.picture as { width: number } | null)?.width;
    const grid = node.attrs.grid as Grid | null;
    const chart = node.attrs.chart as { xml: string; w: number; h: number } | null;
    const look = node.attrs.look as Look | null;
    const drawn = chart ? chartSvg(chart.xml, Math.round(chart.w * PX_PER_PT), Math.round(chart.h * PX_PER_PT)) : null;
    if (drawn) {
      return ["div", { class: "docs-locked docs-locked-pictured", contenteditable: "false", style: lookStyle({ align: look?.align }) }, ["img", { class: "docs-locked-image", src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(drawn)}`, alt: "Chart" }]];
    }
    if (grid?.rows.length) return ["div", { class: "docs-locked docs-locked-grid", contenteditable: "false", title: "This table is kept as it is" }, gridTable(grid)];
    const text = String(node.attrs.text);
    const line = String(node.attrs.what) === "field" && text ? " docs-locked-line" : "";
    if (String(node.attrs.what) === "field" && !text) return ["div", { class: "docs-locked-empty", contenteditable: "false" }];
    if (line && text.includes("\t")) {
      const at = text.lastIndexOf("\t");
      return ["div", { class: `docs-locked${line} docs-locked-leader`, contenteditable: "false", style: lookStyle(look) }, ["span", {}, text.slice(0, at).replace(/\t/g, " ")], ["span", { class: "docs-leader" }], ["span", {}, text.slice(at + 1)]];
    }
    return [
      "div",
      { class: (images.length ? "docs-locked docs-locked-pictured" : "docs-locked") + line, contenteditable: "false", ...(line ? { style: lookStyle(look) } : {}) },
      ["span", { class: "docs-locked-what" }, LOCKED_LABELS[String(node.attrs.what)] ?? "Kept as it is"],
      ...images.map((src) => ["img", { class: "docs-locked-image", src, alt: String((node.attrs.picture as { alt?: string } | null)?.alt ?? ""), ...(width ? { style: `width:${width}%` } : {}) }] as const),
      ["span", { class: "docs-locked-text" }, String(node.attrs.text)],
    ];
  },
});

/** A rule across the page, drawn with the colour, weight and indent the file gives it. */
export const Divider = Node.create({
  name: "divider",
  group: "block",
  atom: true,
  selectable: true,
  addAttributes() {
    return { look: { default: null } };
  },
  parseHTML: () => [{ tag: "hr.docs-divider" }],
  renderHTML: ({ node }) => {
    const look = node.attrs.look as Look | null;
    const edge = look?.border?.bottom;
    const style = edge ? `border-top:${Math.max(edge.w, 0.5)}pt solid #${edge.c};margin:${look?.before ?? 14}pt ${look?.right ?? 0}pt ${look?.after ?? 14}pt ${look?.left ?? 0}pt` : "";
    return ["hr", { class: "docs-divider", ...(style ? { style } : {}) }];
  },
});
