import type { Node as PMNode } from "@tiptap/pm/model";

/** Where the person's caret is in the text, by what is around it, so it can be found again in a
 * document that was rebuilt: the words of its paragraph, how far into them, and which paragraph
 * of the document it is (counting every paragraph, heading, list item and cell). */
export interface Caret {
  text: string;
  offset: number;
  index: number;
}

function blocksOf(doc: PMNode): { node: PMNode; start: number }[] {
  const found: { node: PMNode; start: number }[] = [];
  doc.descendants((node, pos) => {
    if (node.isTextblock) found.push({ node, start: pos + 1 });
  });
  return found;
}

export function caretOf(doc: PMNode, pos: number): Caret | null {
  const blocks = blocksOf(doc);
  const index = blocks.findIndex(({ node, start }) => pos >= start && pos <= start + node.content.size);
  if (index < 0) return null;
  return { text: blocks[index].node.textContent, offset: pos - blocks[index].start, index };
}

/** The position in `doc` for `caret`: in the paragraph with the same words that is nearest to where it
 * was, else in the paragraph at the same place in the document. Null for a document with no text. */
export function caretIn(doc: PMNode, caret: Caret): number | null {
  const blocks = blocksOf(doc);
  if (!blocks.length) return null;
  const same = blocks.map((block, index) => ({ block, index })).filter(({ block }) => block.node.textContent === caret.text);
  const pick = same.length ? same.reduce((best, now) => (Math.abs(now.index - caret.index) < Math.abs(best.index - caret.index) ? now : best)) : { block: blocks[Math.min(caret.index, blocks.length - 1)] };
  return pick.block.start + Math.min(caret.offset, pick.block.node.content.size);
}
