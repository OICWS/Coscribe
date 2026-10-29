import { Extension } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

// The Word export's own rules (tools/office/table_layout.py, docx/_style.py), so a table looks the
// same in the panel and in the file.
const NUMBER = /^[+\-−]?[¥$€£]?\d[\d,]*(?:\.\d+)?\s*[%‰]?$/;
const TOTAL = /^\s*(grand total|totals?|sum|合计|总计|小计|总额|共计)(?![\w])/i;

function rows(table: PMNode): { cells: { pos: number; node: PMNode }[]; header: boolean }[] {
  const found: { cells: { pos: number; node: PMNode }[]; header: boolean }[] = [];
  table.forEach((row, rowOffset) => {
    const cells: { pos: number; node: PMNode }[] = [];
    row.forEach((cell, cellOffset) => cells.push({ pos: rowOffset + 1 + cellOffset, node: cell }));
    found.push({ cells, header: cells.some((c) => c.node.type.name === "tableHeader") });
  });
  return found;
}

/** Decorations for one table at `start`: number columns right-aligned, a total row in bold. */
export function tableLook(table: PMNode, start: number): Decoration[] {
  const all = rows(table);
  const body = all.filter((row) => !row.header);
  const width = Math.max(0, ...all.map((row) => row.cells.length));
  const numeric = Array.from({ length: width }, (_, column) => {
    const filled = body.map((row) => row.cells[column]?.node.textContent.trim() ?? "").filter(Boolean);
    return filled.length > 0 && filled.every((text) => NUMBER.test(text));
  });
  const found: Decoration[] = [];
  const last = body.length > 1 ? body[body.length - 1] : null;
  for (const row of all) {
    const total = row === last && TOTAL.test(row.cells[0]?.node.textContent ?? "");
    row.cells.forEach((cell, column) => {
      const classes = [numeric[column] ? "doc-num" : "", total ? "doc-total" : ""].filter(Boolean).join(" ");
      const at = start + 1 + cell.pos;
      if (classes) found.push(Decoration.node(at, at + cell.node.nodeSize, { class: classes }));
    });
  }
  return found;
}

export const DocTableLook = Extension.create({
  name: "docTableLook",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations(state) {
            const found: Decoration[] = [];
            state.doc.descendants((node, pos) => {
              if (node.type.name !== "table") return true;
              found.push(...tableLook(node, pos));
              return false;
            });
            return DecorationSet.create(state.doc, found);
          },
        },
      }),
    ];
  },
});
