/** How the Word file draws its text, as the server resolved it (`look`): turned into the css the editor
 * puts on a block, so a document keeps its fonts, colours, spacing, rules and shading while it is edited. */

interface Edge {
  c: string;
  w: number;
}
type Edges = Partial<Record<"top" | "left" | "bottom" | "right", Edge>>;

export interface Look {
  font?: string;
  size?: number;
  color?: string;
  b?: boolean;
  i?: boolean;
  align?: string;
  before?: number;
  after?: number;
  line?: { m?: number; pt?: number };
  left?: number;
  right?: number;
  first?: number;
  border?: Edges;
  fill?: string;
}

export interface CellLook {
  fill?: string;
  border?: Edges;
  pad?: Partial<Record<"top" | "left" | "bottom" | "right", number>>;
  valign?: string;
}

export interface TableLook {
  widths?: number[];
  edges?: Partial<Record<"top" | "left" | "bottom" | "right" | "insideH" | "insideV", Edge>>;
  rows: { h?: number; cells: { look?: CellLook; p?: Look }[] }[];
}

export interface Page {
  w: number;
  h: number;
  l: number;
  r: number;
  t: number;
  b: number;
  base: Look;
}

/** Word's "multiple" line spacing, as the Review view draws it too. */
const LINE_FACTOR = 1;

const rule = (edge: Edge) => `${Math.max(edge.w, 0.5)}pt solid #${edge.c}`;
const family = (font: string) => `"${font.replace(/"/g, "")}", "Microsoft YaHei", "PingFang SC", sans-serif`;

/** The inline style of a paragraph or heading. */
export function lookStyle(look: Look | null | undefined): string {
  if (!look) return "";
  const css: string[] = [];
  if (look.font) css.push(`font-family:${family(look.font)}`);
  if (look.size) css.push(`font-size:${look.size}pt`);
  if (look.color) css.push(`color:#${look.color}`);
  if (look.b !== undefined) css.push(`font-weight:${look.b ? 700 : 400}`);
  if (look.i !== undefined) css.push(`font-style:${look.i ? "italic" : "normal"}`);
  if (look.align) css.push(`text-align:${look.align}`);
  if (look.before !== undefined) css.push(`margin-top:${look.before}pt`);
  if (look.after !== undefined) css.push(`margin-bottom:${look.after}pt`);
  if (look.line) css.push(`line-height:${look.line.pt ? `${look.line.pt}pt` : Number(((look.line.m ?? 1) * LINE_FACTOR).toFixed(3))}`);
  if (look.left) css.push(`margin-left:${look.left}pt`);
  if (look.right) css.push(`margin-right:${look.right}pt`);
  if (look.first) css.push(`text-indent:${look.first}pt`);
  if (look.fill) css.push(`background:#${look.fill}`);
  for (const [side, edge] of Object.entries(look.border ?? {})) {
    css.push(`border-${side}:${rule(edge)}`);
    css.push(`padding-${side}:${side === "left" || side === "right" ? 6 : 3}pt`);
  }
  return css.join(";");
}

/** The inline style of a table cell: its fill, its borders (its own, else the table's), its padding. */
export function cellStyle(cell: CellLook | undefined, table: TableLook | undefined, at: { r: number; c: number; rows: number; cols: number }): string {
  const edges = table?.edges ?? {};
  const own = cell?.border ?? {};
  const sides = {
    top: own.top ?? (at.r === 0 ? edges.top : edges.insideH),
    bottom: own.bottom ?? (at.r === at.rows - 1 ? edges.bottom : edges.insideH),
    left: own.left ?? (at.c === 0 ? edges.left : edges.insideV),
    right: own.right ?? (at.c === at.cols - 1 ? edges.right : edges.insideV),
  };
  const css: string[] = [];
  for (const [side, edge] of Object.entries(sides)) css.push(edge ? `border-${side}:${rule(edge)}` : `border-${side}:none`);
  if (cell?.fill) css.push(`background:#${cell.fill}`);
  if (cell?.valign) css.push(`vertical-align:${cell.valign}`);
  for (const [side, points] of Object.entries(cell?.pad ?? {})) css.push(`padding-${side}:${points}pt`);
  return css.join(";");
}

/** What the document's ordinary text looks like, as the editor's base style. */
export function baseStyle(page: Page): string {
  const base = page.base;
  return [
    `font-family:${family(base.font ?? "sans-serif")}`,
    `font-size:${base.size ?? 11}pt`,
    `color:#${base.color ?? "000000"}`,
    `line-height:${Number(((base.line?.m ?? 1) * LINE_FACTOR).toFixed(3))}`,
    `--p-after:${base.after ?? 0}pt`,
  ].join(";");
}

/** The sheet the document is drawn on: the page's size and margins. */
export const sheetStyle = (page: Page): Record<string, string> => ({
  width: `${page.w}pt`,
  minHeight: `${page.h}pt`,
  padding: `${page.t}pt ${page.r}pt ${page.b}pt ${page.l}pt`,
});

export interface RunLook {
  t: string;
  b?: true;
  i?: true;
  u?: true;
  c?: string;
  sz?: number;
  f?: string;
}

/** The inline style of a run of a block the editor only draws. */
export function runStyle(run: RunLook): string {
  const css: string[] = [];
  if (run.f) css.push(`font-family:${family(run.f)}`);
  if (run.sz) css.push(`font-size:${run.sz}pt`);
  if (run.c) css.push(`color:#${run.c}`);
  if (run.b) css.push("font-weight:700");
  if (run.i) css.push("font-style:italic");
  if (run.u) css.push("text-decoration:underline");
  return css.join(";");
}
