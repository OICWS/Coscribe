import { Extension } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { chartSvg, parseChart } from "./docChart";

function preview(source: string): HTMLElement {
  const box = document.createElement("div");
  box.className = "doc-chart";
  box.contentEditable = "false";
  const chart = parseChart(source);
  if (typeof chart === "string") {
    box.classList.add("doc-chart-bad");
    box.textContent = `This chart cannot be drawn: ${chart}`;
  } else {
    // The SVG is made here from numbers and escaped text, never from the document's own markup.
    box.innerHTML = chartSvg(chart);
  }
  return box;
}

/** Draws each chart block above its source, so the source stays what the person edits. */
export const DocChartPreview = Extension.create({
  name: "docChartPreview",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations(state) {
            const found: Decoration[] = [];
            state.doc.forEach((node, pos) => {
              if (node.type.name === "rawBlock" && node.attrs.kind === "chart") found.push(Decoration.widget(pos, () => preview(node.textContent), { side: -1, key: node.textContent }));
            });
            return DecorationSet.create(state.doc, found);
          },
        },
      }),
    ];
  },
});
