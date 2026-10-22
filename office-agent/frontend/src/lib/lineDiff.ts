/** A line diff of two texts, for showing how a plan changed. Pure, so the
 * rules are unit-tested; the component only draws the rows. */

export interface DiffRow {
  kind: "same" | "add" | "del";
  /** 1-based line number in the old / new text; null where the line is not there. */
  oldNo: number | null;
  newNo: number | null;
  text: string;
  /** The part of a changed line that differs from its counterpart, [start, end). */
  mark?: [number, number];
}

export type DiffEntry = DiffRow | { kind: "gap"; hidden: number };

const CONTEXT = 2;

const linesOf = (text: string): string[] => (text === "" ? [] : text.replace(/\r\n/g, "\n").split("\n"));

/** The rows that turn `before` into `after`: the longest common run of lines
 * stays, the rest is deleted and added. */
export function diffLines(before: string, after: string): DiffRow[] {
  const a = linesOf(before);
  const b = linesOf(after);
  // lengths[i][j]: how many lines the tails a[i..] and b[j..] share.
  const lengths = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lengths[i][j] = a[i] === b[j] ? lengths[i + 1][j + 1] + 1 : Math.max(lengths[i + 1][j], lengths[i][j + 1]);
    }
  }
  const rows: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      rows.push({ kind: "same", oldNo: i + 1, newNo: j + 1, text: a[i] });
      i++;
      j++;
    } else if (j < b.length && (i === a.length || lengths[i][j + 1] > lengths[i + 1][j])) {
      rows.push({ kind: "add", oldNo: null, newNo: j + 1, text: b[j] });
      j++;
    } else {
      rows.push({ kind: "del", oldNo: i + 1, newNo: null, text: a[i] });
      i++;
    }
  }
  return markPairs(rows);
}

/** A deleted line right before an added one is usually the same line edited:
 * mark what is between their common start and common end. */
function markPairs(rows: DiffRow[]): DiffRow[] {
  const out = rows.slice();
  for (let k = 0; k < out.length;) {
    let del = k;
    while (del < out.length && out[del].kind === "del") del++;
    let add = del;
    while (add < out.length && out[add].kind === "add") add++;
    const deleted = del - k;
    const added = add - del;
    if (deleted > 0 && added > 0) {
      for (let n = 0; n < Math.min(deleted, added); n++) {
        const [oldMark, newMark] = changedSpan(out[k + n].text, out[del + n].text);
        out[k + n] = { ...out[k + n], mark: oldMark };
        out[del + n] = { ...out[del + n], mark: newMark };
      }
    }
    k = Math.max(add, k + 1);
  }
  return out;
}

function changedSpan(before: string, after: string): [[number, number], [number, number]] {
  let start = 0;
  while (start < before.length && start < after.length && before[start] === after[start]) start++;
  let end = 0;
  while (end < before.length - start && end < after.length - start && before[before.length - 1 - end] === after[after.length - 1 - end]) end++;
  return [
    [start, before.length - end],
    [start, after.length - end],
  ];
}

export function diffStat(rows: DiffRow[]): { added: number; removed: number } {
  return {
    added: rows.filter((row) => row.kind === "add").length,
    removed: rows.filter((row) => row.kind === "del").length,
  };
}

/** The rows near a change, with a gap row for each stretch of unchanged lines left out. */
export function withContext(rows: DiffRow[], context = CONTEXT): DiffEntry[] {
  const keep = rows.map((row) => row.kind !== "same");
  const near = keep.map((_, index) => {
    for (let k = Math.max(0, index - context); k <= Math.min(rows.length - 1, index + context); k++) if (keep[k]) return true;
    return false;
  });
  // A gap row for a single line would take as much room as the line.
  near.forEach((shown, index) => {
    if (!shown && near[index - 1] && near[index + 1]) near[index] = true;
  });
  const out: DiffEntry[] = [];
  let hidden = 0;
  rows.forEach((row, index) => {
    if (near[index]) {
      if (hidden > 0) out.push({ kind: "gap", hidden });
      hidden = 0;
      out.push(row);
    } else {
      hidden++;
    }
  });
  if (hidden > 0 && out.length > 0) out.push({ kind: "gap", hidden });
  return out;
}
