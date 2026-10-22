import type { Block } from "./docsEditor";

/** A stretch of the base, `base[from, to)`, that a side replaced with `other[start, end)`. */
interface Hunk {
  from: number;
  to: number;
  start: number;
  end: number;
}

const print = (block: Block) => JSON.stringify({ ...block, id: undefined });

/** The stretches where `other` differs from `base`, by what the blocks hold (not their ids, which
 * the file numbers by position and so shift when a block is added). */
function hunks(base: string[], other: string[]): Hunk[] {
  let head = 0;
  while (head < base.length && head < other.length && base[head] === other[head]) head += 1;
  let tail = 0;
  while (tail < base.length - head && tail < other.length - head && base[base.length - 1 - tail] === other[other.length - 1 - tail]) tail += 1;
  const a = base.slice(head, base.length - tail);
  const b = other.slice(head, other.length - tail);
  // Longest common run of the middle, as a table of its suffixes.
  const common = Array.from({ length: a.length + 1 }, () => new Uint32Array(b.length + 1));
  for (let i = a.length - 1; i >= 0; i -= 1) for (let j = b.length - 1; j >= 0; j -= 1) common[i][j] = a[i] === b[j] ? common[i + 1][j + 1] + 1 : Math.max(common[i + 1][j], common[i][j + 1]);
  const found: Hunk[] = [];
  let i = 0;
  let j = 0;
  let open: Hunk | null = null;
  const close = () => {
    if (open) found.push(open);
    open = null;
  };
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      close();
      i += 1;
      j += 1;
      continue;
    }
    open ??= { from: head + i, to: head + i, start: head + j, end: head + j };
    if (j < b.length && (i === a.length || common[i][j + 1] >= common[i + 1][j])) {
      j += 1;
      open.end = head + j;
    } else {
      i += 1;
      open.to = head + i;
    }
  }
  close();
  return found;
}

/** Whether two hunks touch the same part of the base: two changes to a block, or two additions at the
 * same place. A change beside an untouched block does not. */
const clash = (x: Hunk, y: Hunk) => (x.from === x.to && y.from === y.to ? x.from === y.from : x.from < y.to && y.from < x.to) || (x.from === x.to && x.from > y.from && x.from < y.to) || (y.from === y.to && y.from > x.from && y.from < x.to);

/** Joins what the person changed (`mine`) and what the file changed meanwhile (`theirs`), both from
 * `base`. Null when both changed the same blocks: there the person decides. The blocks come out with
 * the ids of `theirs`, so a save over its version finds each where it is; a block the person changed
 * keeps the id of the block it replaced, and one they added has none. */
export function mergeBlocks(base: Block[], mine: Block[], theirs: Block[]): Block[] | null {
  const prints = [base, mine, theirs].map((blocks) => blocks.map(print));
  const ours = hunks(prints[0], prints[1]).map((hunk) => ({ ...hunk, side: "mine" as const }));
  const theirHunks = hunks(prints[0], prints[2]).map((hunk) => ({ ...hunk, side: "theirs" as const }));
  if (ours.some((x) => theirHunks.some((y) => clash(x, y)))) return null;
  // The block of `theirs` each block of the base became, where the file left it as it was.
  const kept = new Map<number, Block>();
  const shift = (i: number) => theirHunks.reduce((moved, h) => (h.to <= i ? moved + (h.end - h.start) - (h.to - h.from) : moved), 0);
  base.forEach((_, i) => {
    if (!theirHunks.some((h) => h.from <= i && i < h.to)) kept.set(i, theirs[i + shift(i)]);
  });
  const merged: Block[] = [];
  let i = 0;
  for (const hunk of [...ours, ...theirHunks].sort((x, y) => x.from - y.from || x.to - y.to)) {
    for (; i < hunk.from; i += 1) merged.push(kept.get(i) ?? base[i]);
    if (hunk.side === "theirs") merged.push(...theirs.slice(hunk.start, hunk.end));
    else {
      const replaced = hunk.to - hunk.from === hunk.end - hunk.start;
      merged.push(...mine.slice(hunk.start, hunk.end).map((block, k) => ({ ...block, id: replaced ? kept.get(hunk.from + k)?.id : undefined }) as Block));
    }
    i = Math.max(i, hunk.to);
  }
  for (; i < base.length; i += 1) merged.push(kept.get(i) ?? base[i]);
  return merged;
}
