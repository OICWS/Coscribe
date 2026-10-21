import { useContext } from "react";
import { isViewable } from "../../lib/viewers";
import { FileTextIcon } from "../icons";
import { ViewFile } from "./contexts";
import type { ToolOrApprovalItem } from "./types";

/** The decks and documents a run of calls made or changed, each one click from opening in its
 * panel instead of only through the Outputs list. */
export function OpenFileChips({ items }: { items: ToolOrApprovalItem[] }) {
  const view = useContext(ViewFile);
  const paths = new Set<string>();
  for (const item of items) {
    const path = item.arguments.path;
    const done = item.kind === "tool" && item.result !== undefined && !item.isError;
    if (done && typeof path === "string" && isViewable(path) && !item.toolName.startsWith("read_")) paths.add(path);
  }
  if (!view || paths.size === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {[...paths].map((path) => (
        <button
          key={path}
          type="button"
          title="Open"
          className="flex max-w-full items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-sm hover:bg-[var(--card-bg)]"
          onClick={() => view(path)}
        >
          <FileTextIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
          <span className="truncate">{path.split(/[\\/]/).pop()}</span>
        </button>
      ))}
    </div>
  );
}
