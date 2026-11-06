import { type SummaryParts } from "../../lib/transcriptGrouping";

/** write_docx/write_xlsx/write_pptx's tool result carries a `preview_path`
 * (a bare filename under GET /api/previews/) when a thumbnail was
 * rendered -- other tools' results never have this shape. */
export function previewPathOf(result: unknown): string | null {
  if (!result || typeof result !== "object" || !("preview_path" in result)) return null;
  const value = (result as Record<string, unknown>).preview_path;
  return typeof value === "string" ? value : null;
}

/** Click-a-shape-to-target-it (PptxShapeOverlay) only makes sense for a
 * .pptx preview -- write_docx/write_xlsx thumbnails share the exact same
 * preview_path shape but have no shape_index concept to click into.
 * `arguments.slide` covers every edit tool that targets one slide
 * (edit_pptx_shape, delete/duplicate/reorder_pptx_slide, ...); a bare
 * write_pptx has no `slide` argument at all, and its own preview is
 * always the deck's first slide (see tools/_thumbnail.py). */
export function pptxOverlayTargetOf(arguments_: Record<string, unknown>): { path: string; slide: number } | null {
  const path = arguments_.path;
  if (typeof path !== "string" || !path.toLowerCase().endsWith(".pptx")) return null;
  const slide = arguments_.slide;
  return { path, slide: typeof slide === "number" ? slide : 1 };
}

/** Clauses after the first read as one sentence ("Ran 3 commands, read a
 * file"); an acronym-led verb ("PDF ...") keeps its capitals. */
export function inSentence(parts: SummaryParts, index: number): SummaryParts {
  if (index === 0 || !/^[A-Z][a-z]/.test(parts.verb)) return parts;
  return { ...parts, verb: parts.verb[0].toLowerCase() + parts.verb.slice(1) };
}

// Matches the end the server gives a stopped turn (conversation/stopped_turn.py): the history keeps
// "[stopped]" so the model knows, and the page shows it as a status line instead of prose.
const STOPPED_END = /\s*\[stopped\](?:\s*\((\d+) background task\(s\) still running; stop them in the Background tasks panel\.\))?\s*$/;

/** A reply split into what the model said and whether the user stopped it, with the number of
 * background tasks the stop left running. */
export function splitStopped(text: string): { said: string; stopped: boolean; running: number } {
  const match = STOPPED_END.exec(text);
  if (!match) return { said: text, stopped: false, running: 0 };
  return { said: text.slice(0, match.index), stopped: true, running: Number(match[1] ?? 0) };
}
