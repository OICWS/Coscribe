import { Extension } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { DocComment } from "./docComments";

/** The slice of a comment the page draws. */
export type Marked = Pick<DocComment, "id" | "block" | "quote">;

interface Storage {
  comments: Marked[];
  onOpen: (id: string) => void;
}

const key = new PluginKey("docComments");
/** The meta on a transaction that only asks for the marks to be drawn again. */
export const REDRAW = "docCommentsRedraw";

/** Where `quote` sits inside a block, as document positions: text nodes in order, so the words are found
 * across bold and links, not only inside one run. */
export function quoteRange(block: PMNode, start: number, quote: string): { from: number; to: number } | null {
  let text = "";
  const at: { pos: number; at: number; length: number }[] = [];
  block.descendants((node, pos) => {
    if (!node.isText) {
      if (node.isBlock && text) text += "\n";
      return;
    }
    at.push({ pos: start + 1 + pos, at: text.length, length: node.text?.length ?? 0 });
    text += node.text ?? "";
  });
  const found = quote ? text.indexOf(quote) : -1;
  if (found < 0) return null;
  const place = (offset: number) => {
    const run = at.findLast((r) => r.at <= offset) ?? at[0];
    return run.pos + (offset - run.at);
  };
  return { from: place(found), to: place(found + quote.length - 1) + 1 };
}

/** A row of no height before the block, so the count can sit in the margin beside it. */
function badge(ids: string[], onOpen: (id: string) => void): HTMLElement {
  const row = document.createElement("div");
  row.className = "doc-comment-row";
  row.contentEditable = "false";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "doc-comment-badge";
  button.title = ids.length === 1 ? "1 comment" : `${ids.length} comments`;
  button.setAttribute("aria-label", button.title);
  button.textContent = String(ids.length);
  button.addEventListener("mousedown", (e) => e.preventDefault());
  button.addEventListener("click", () => onOpen(ids[0]));
  row.append(button);
  return row;
}

/** Draws the open comments on the page: the words a comment is on are shaded, and a block with comments
 * has a count in the margin that opens the first of them. */
export const DocCommentMarks = Extension.create<unknown, Storage>({
  name: "docCommentMarks",
  addStorage: () => ({ comments: [], onOpen: () => undefined }),
  addProseMirrorPlugins() {
    const storage = this.storage;
    return [
      new Plugin({
        key,
        props: {
          decorations(state) {
            const byBlock = new Map<number, Marked[]>();
            for (const comment of storage.comments) if (comment.block !== null) byBlock.set(comment.block, [...(byBlock.get(comment.block) ?? []), comment]);
            if (!byBlock.size) return DecorationSet.empty;
            const decorations: Decoration[] = [];
            state.doc.forEach((node, pos) => {
              const here = byBlock.get(node.attrs.blockIndex as number);
              if (!here) return;
              decorations.push(Decoration.node(pos, pos + node.nodeSize, { class: "doc-has-comments" }));
              for (const comment of here) {
                const range = quoteRange(node, pos, comment.quote);
                if (range) decorations.push(Decoration.inline(range.from, range.to, { class: "doc-commented" }));
              }
              decorations.push(
                Decoration.widget(
                  pos,
                  () =>
                    badge(
                      here.map((c) => c.id),
                      storage.onOpen,
                    ),
                  { side: -1, key: `badge-${here.map((c) => c.id).join(",")}` },
                ),
              );
            });
            return DecorationSet.create(state.doc, decorations);
          },
        },
      }),
    ];
  },
});
