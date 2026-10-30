import { useContext } from "react";
import { KINDS } from "../../lib/artifacts";
import { baseName, KIND_WORDS, kindOfFile, madeFiles } from "../../lib/fileMentions";
import { ChevronRightIcon } from "../icons";
import { KindIcon } from "../artifacts/artifactIcons";
import { ThreadIdContext } from "../threadContext";
import { openMentioned, ViewFile } from "./contexts";
import { useShownFile } from "./useShownFile";
import type { ToolOrApprovalItem } from "./types";

/** The decks and documents a run of calls made or changed, each a card that opens it in its panel:
 * the end of a turn's answer points at what it made. */
export function FileCards({ items }: { items: ToolOrApprovalItem[] }) {
  const view = useContext(ViewFile);
  const paths = madeFiles(items);
  if (!view || paths.length === 0) return null;
  return (
    <div className="mt-2 flex flex-col gap-2">
      {paths.map((path) => (
        <FileCard key={path} path={path} view={view} calls={items.length} />
      ))}
    </div>
  );
}

function FileCard({ path, view, calls }: { path: string; view: (path: string) => boolean; calls: number }) {
  const threadId = useContext(ThreadIdContext);
  const shown = useShownFile(threadId, path, calls);
  if (!shown) return null;
  const kind = kindOfFile(path);
  const name = baseName(path);
  const stem = name.replace(/\.[^.]+$/, "");
  return (
    <button
      type="button"
      title={`Open ${name}`}
      className="flex w-full max-w-[460px] items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-left hover:bg-[var(--card-bg)]"
      onClick={() => openMentioned(view, threadId, path)}
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ color: KINDS[kind].colour, background: `color-mix(in srgb, ${KINDS[kind].colour} 14%, transparent)` }}>
        <KindIcon kind={kind} className="h-5 w-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{stem}</span>
        <span className="block truncate text-xs text-[var(--muted)]">
          {KIND_WORDS[kind]} · {name.slice(stem.length)}
        </span>
      </span>
      <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
    </button>
  );
}
