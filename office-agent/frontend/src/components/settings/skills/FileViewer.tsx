import { lazy, Suspense, useEffect, useRef, useState } from "react";
import type { SkillFileContentResult } from "../../../types/settings";
import { CodeIcon, EyeIcon } from "../../icons";
import { PREVIEWABLE, extension, withoutFrontmatter } from "./helpers";

const Markdown = lazy(() => import("../../Markdown").then((m) => ({ default: m.Markdown })));

function CodeView({ text }: { text: string }) {
  const lines = text.replace(/\n$/, "").split("\n");
  return (
    <div className="font-mono text-[13px] leading-6">
      {lines.map((line, index) => (
        <div key={index} className="flex">
          <span className="w-10 shrink-0 select-none pr-4 text-right tabular-nums text-[var(--muted)]">{index + 1}</span>
          <span className="min-w-0 flex-1 whitespace-pre-wrap break-words border-l border-[var(--border)] pl-4">
            {line || " "}
          </span>
        </div>
      ))}
    </div>
  );
}

export function FileViewer({
  source,
  path,
  load,
}: {
  /** Identifies what `load` reads from, so switching sources reloads. */
  source: string;
  path: string;
  load: (path: string) => Promise<SkillFileContentResult>;
}) {
  const loadRef = useRef(load);
  loadRef.current = load;
  const [content, setContent] = useState<SkillFileContentResult | null>(null);
  const [mode, setMode] = useState<"preview" | "code">("preview");
  const previewable = PREVIEWABLE.has(extension(path));
  const markdown = extension(path) === "md";

  useEffect(() => {
    let cancelled = false;
    setContent(null);
    if (previewable) {
      loadRef.current(path)
        .catch(() => ({ error: "Couldn't load this file." }))
        .then((result) => !cancelled && setContent(result));
    }
    return () => {
      cancelled = true;
    };
  }, [source, path, previewable]);

  const segment = (active: boolean) =>
    `flex h-7 w-8 items-center justify-center rounded-md ${
      active ? "bg-[var(--bg)] text-[var(--fg)] shadow-sm ring-1 ring-[var(--border)]" : "text-[var(--muted)] hover:text-[var(--fg)]"
    }`;
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex h-12 shrink-0 items-center justify-between gap-3 px-5">
        <span className="truncate font-mono text-sm text-[var(--muted)]">/{path}</span>
        {markdown && (
          <div className="flex shrink-0 rounded-lg bg-[var(--card-bg)] p-0.5">
            <button type="button" title="Preview" aria-pressed={mode === "preview"} className={segment(mode === "preview")} onClick={() => setMode("preview")}>
              <EyeIcon className="h-4 w-4" />
            </button>
            <button type="button" title="Source" aria-pressed={mode === "code"} className={segment(mode === "code")} onClick={() => setMode("code")}>
              <CodeIcon className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
        {!previewable && <p className="pt-10 text-center text-sm text-[var(--muted)]">No preview for this file type.</p>}
        {previewable && !content && <p className="text-sm text-[var(--muted)]">Loading...</p>}
        {content && "error" in content && <p className="text-sm text-[var(--muted)]">{content.error}</p>}
        {content && "content" in content &&
          (markdown && mode === "preview" ? (
            <Suspense fallback={<p className="whitespace-pre-wrap text-sm">{content.content}</p>}>
              <Markdown text={withoutFrontmatter(content.content)} />
            </Suspense>
          ) : (
            <CodeView text={content.content} />
          ))}
      </div>
    </div>
  );
}
