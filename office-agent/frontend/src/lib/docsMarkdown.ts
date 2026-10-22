import type { Block } from "./docsEditor";

type Runs = Extract<Block, { runs: unknown }>["runs"];

// A table cell also escapes the bar, in the same pass as the backslash it is escaped with.
const escaped = (text: string, inCell: boolean) => text.replace(inCell ? /([\\`*_[\]|])/g : /([\\`*_[\]])/g, "\\$1");

function inline(runs: Runs, inCell = false): string {
  return runs
    .map((run) => {
      const lead = run.t.match(/^\s*/)?.[0] ?? "";
      const trail = run.t.match(/\s*$/)?.[0] ?? "";
      const core = run.t.trim();
      if (!core) return run.t;
      let text = escaped(core, inCell).replace(/\n/g, "  \n");
      if (run.b) text = `**${text}**`;
      if (run.i) text = `*${text}*`;
      if (run.link) text = `[${text}](${run.link})`;
      return `${lead}${text}${trail}`;
    })
    .join("");
}

const cell = (runs: Runs) => inline(runs, true).replace(/\s*\n\s*/g, "<br>");

function table(rows: Runs[][], header: boolean): string {
  const width = rows[0]?.length ?? 0;
  const line = (cells: string[]) => `| ${cells.join(" | ")} |`;
  const body = rows.map((row) => line(row.map(cell)));
  const head = header ? body.shift() : line(Array(width).fill(" "));
  return [head, line(Array(width).fill("---")), ...body].join("\n");
}

/** A document's blocks as Markdown: the title as `#`, headings one level down, lists, quotes, tables
 * and links. A picture or a block the editor keeps as it is stays a short bracketed note. */
export function blocksToMarkdown(blocks: Block[]): string {
  const titled = blocks.some((block) => block.kind === "title");
  const out: string[] = [];
  let previousList = false;
  for (const block of blocks) {
    const listed = block.kind === "bullet" || block.kind === "number";
    let text = "";
    if (block.kind === "title") text = `# ${inline(block.runs)}`;
    else if (block.kind === "heading") text = `${"#".repeat(Math.min(block.level + (titled ? 1 : 0), 6))} ${inline(block.runs)}`;
    else if (block.kind === "quote") text = `> ${inline(block.runs)}`;
    else if (block.kind === "bullet") text = `${"  ".repeat(block.level - 1)}- ${inline(block.runs)}`;
    else if (block.kind === "number") text = `${"   ".repeat(block.level - 1)}1. ${inline(block.runs)}`;
    else if (block.kind === "table") text = table(block.rows, block.header);
    else if (block.kind === "divider") text = "---";
    else if (block.kind === "locked") text = block.images?.length ? "[Picture]" : (block.text ?? "");
    else if (block.kind === "paragraph") text = inline(block.runs);
    if (!text.trim()) continue;
    // A list's items follow each other; everything else is a paragraph of its own.
    if (out.length) out.push(listed && previousList ? "\n" : "\n\n");
    out.push(text);
    previousList = listed;
  }
  return `${out.join("").replace(/\n\n\n/g, "\n")}\n`;
}
