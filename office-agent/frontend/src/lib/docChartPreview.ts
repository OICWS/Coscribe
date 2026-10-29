import { Extension } from "@tiptap/core";
import { Plugin, TextSelection } from "@tiptap/pm/state";
import { Decoration, DecorationSet, type EditorView } from "@tiptap/pm/view";
import { chartSvg, parseChart } from "./docChart";

function preview(source: string, view: EditorView, at: number): HTMLElement {
  const box = document.createElement("div");
  box.className = "doc-chart";
  box.contentEditable = "false";
  box.title = view.editable ? "Click to edit the chart's data" : "";
  box.addEventListener("mousedown", (event) => {
    if (!view.editable) return;
    event.preventDefault();
    view.dispatch(view.state.tr.setSelection(TextSelection.create(view.state.doc, at + 1)));
    view.focus();
  });
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

/** Draws each chart block in place of its source; the source shows, under the chart, only while the
 * caret is in it (a click on the chart puts it there), so the person reads a chart, not a table of
 * numbers in a code box. */
export const DocChartPreview = Extension.create({
  name: "docChartPreview",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations(state) {
            const found: Decoration[] = [];
            const { from, to } = state.selection;
            state.doc.forEach((node, pos) => {
              if (node.type.name !== "rawBlock" || node.attrs.kind !== "chart") return;
              found.push(Decoration.widget(pos, (view) => preview(node.textContent, view, pos), { side: -1, key: `${pos}:${node.textContent}` }));
              const editing = from <= pos + node.nodeSize && to >= pos;
              if (!editing) found.push(Decoration.node(pos, pos + node.nodeSize, { class: "doc-chart-source-hidden" }));
            });
            return DecorationSet.create(state.doc, found);
          },
        },
      }),
    ];
  },
});
