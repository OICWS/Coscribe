import { useContext, useRef, useState, type MouseEvent, type FocusEvent } from "react";
import { createPortal } from "react-dom";
import { editedLabel, KINDS, lookupArtifact, type ArtifactSummary } from "../../lib/artifacts";
import { baseName, KIND_WORDS, kindOfFile } from "../../lib/fileMentions";
import { KindIcon } from "../artifacts/artifactIcons";
import { ThreadIdContext } from "../threadContext";
import { openMentioned, ViewFile } from "./contexts";

const CARD_WIDTH = 288;

/** A file this conversation made, named in a reply: a chip that opens it in its panel, and a small
 * card on hover with what it is and when it last changed. */
export function FileChip({ path }: { path: string }) {
  const view = useContext(ViewFile);
  const threadId = useContext(ThreadIdContext);
  const [found, setFound] = useState<ArtifactSummary | null | undefined>(undefined);
  const [edited, setEdited] = useState("");
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const kind = kindOfFile(path);
  const name = baseName(path);
  if (!view) return <>{name}</>;
  const show = (event: MouseEvent<HTMLElement> | FocusEvent<HTMLElement>) => {
    window.clearTimeout(timer.current);
    setAnchor(event.currentTarget.getBoundingClientRect());
    if (found === undefined) {
      lookupArtifact(threadId, path).then(
        (item) => {
          setFound(item);
          if (item) setEdited(editedLabel(item.modified_at, new Date()));
        },
        () => setFound(null),
      );
    }
  };
  const hide = () => {
    timer.current = window.setTimeout(() => setAnchor(null), 120);
  };
  return (
    <>
      <button
        type="button"
        className="mx-0.5 inline-flex max-w-full items-center gap-1 rounded-md bg-[var(--accent-soft)] px-1.5 py-px align-baseline text-[0.95em] text-[var(--accent-ink)] hover:brightness-95"
        onClick={() => openMentioned(view, threadId, path)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        <KindIcon kind={kind} className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{(found?.name ?? name).replace(/\.[^.]+$/, "")}</span>
      </button>
      {anchor &&
        createPortal(
          <div
            role="tooltip"
            className="fixed z-50 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3 text-sm shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
            style={{ left: Math.max(8, Math.min(anchor.left, window.innerWidth - CARD_WIDTH - 8)), top: anchor.bottom + 6, width: CARD_WIDTH }}
            onMouseEnter={() => window.clearTimeout(timer.current)}
            onMouseLeave={hide}
          >
            <div className="flex items-center justify-between gap-3 text-xs text-[var(--muted)]">
              <span className="flex items-center gap-1.5">
                <KindIcon kind={kind} className="h-3.5 w-3.5" style={{ color: KINDS[kind].colour }} />
                {KIND_WORDS[kind]}
              </span>
              {edited && <span>{edited}</span>}
            </div>
            <div className="mt-1.5 break-words font-medium">{found?.name ?? name.replace(/\.[^.]+$/, "")}</div>
          </div>,
          document.body,
        )}
    </>
  );
}
