import { useEffect, useMemo, useState } from "react";
import { getSkillFileContent, getSkillFiles, getTools } from "../../../lib/rest";
import type { SkillInfo } from "../../../types/settings";
import { ArrowLeftIcon } from "../../icons";
import { ToggleSwitch } from "../../ToggleSwitch";
import { SOURCE_BYLINE, PREVIEWABLE, extension, shortDate, buildFileTree } from "./helpers";
import { SkillBadge } from "./badges";
import { SkillMenu } from "./SkillMenu";
import { FileTreeView } from "./FileTree";
import { FileViewer } from "./FileViewer";

export function SkillDetailView({
  skill,
  onBack,
  onToggle,
  onRemove,
}: {
  skill: SkillInfo;
  onBack: () => void;
  onToggle: () => void;
  onRemove: () => void;
}) {
  const [tab, setTab] = useState<"overview" | "contents">("contents");
  const [files, setFiles] = useState<string[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [mentionedTools, setMentionedTools] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    getSkillFiles(skill.name)
      .then((result) => {
        if (cancelled) return;
        setFiles(result.files);
        setSelected(result.files.includes("SKILL.md") ? "SKILL.md" : (result.files[0] ?? null));
      })
      .catch(() => !cancelled && setFiles([]));
    return () => {
      cancelled = true;
    };
  }, [skill.name]);

  // Which of coscribe's tools the skill names, from its text files only.
  useEffect(() => {
    if (tab !== "overview" || !files) return;
    let cancelled = false;
    const textFiles = files.filter((path) => PREVIEWABLE.has(extension(path))).slice(0, 40);
    Promise.all([getTools(), ...textFiles.map((path) => getSkillFileContent(skill.name, path))])
      .then(([tools, ...contents]) => {
        if (cancelled) return;
        const text = contents.map((c) => ("content" in c ? c.content : "")).join("\n");
        setMentionedTools(tools.tools.map((t) => t.name).filter((name) => new RegExp(`\\b${name}\\b`).test(text)).sort());
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [tab, files, skill.name]);

  const tree = useMemo(() => buildFileTree(files ?? []), [files]);
  const tabClass = (active: boolean) =>
    `-mb-px border-b-2 px-4 py-2.5 text-[15px] ${
      active ? "border-[var(--fg)] text-[var(--fg)]" : "border-transparent text-[var(--muted)] hover:text-[var(--fg)]"
    }`;

  return (
    <div className="flex h-full min-h-0 flex-col gap-5">
      <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
        <ArrowLeftIcon className="h-4 w-4" /> Your skills
      </button>
      <div className="flex items-center gap-4">
        <SkillBadge large />
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-semibold">{skill.name}</div>
          <div className="text-sm text-[var(--muted)]">
            {SOURCE_BYLINE[skill.source].replace(/^./, (c) => c.toUpperCase())} &middot; updated {shortDate(skill.updated)}
          </div>
        </div>
        <ToggleSwitch on={skill.enabled} onClick={onToggle} label={skill.enabled ? "Turn off" : "Turn on"} />
        {skill.source !== "builtin" && <SkillMenu skill={skill} onToggle={onToggle} onRemove={onRemove} />}
      </div>
      <div className="flex border-b border-[var(--border)]">
        <button type="button" className={tabClass(tab === "overview")} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button type="button" className={tabClass(tab === "contents")} onClick={() => setTab("contents")}>
          Contents{files ? <span className="text-[var(--muted)]"> &middot; {files.length}</span> : null}
        </button>
      </div>

      {tab === "overview" ? (
        <div className="flex flex-col gap-4">
          <p className="text-[15px] leading-relaxed">{skill.description}</p>
          {skill.source === "anthropic" && (
            <p className="text-sm text-[var(--muted)]">
              From github.com/anthropics/skills, under the Apache License 2.0 (see LICENSE.txt in Contents).
            </p>
          )}
          {mentionedTools.length > 0 && (
            <div>
              <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">coscribe tools it uses</div>
              <div className="flex flex-wrap gap-1.5">
                {mentionedTools.map((name) => (
                  <code key={name} className="rounded bg-[var(--card-bg)] px-1.5 py-0.5 font-mono text-xs">
                    {name}
                  </code>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : files === null ? (
        <p className="py-6 text-center text-sm text-[var(--muted)]">Loading...</p>
      ) : (
        <div className="flex min-h-[420px] flex-1 overflow-hidden rounded-xl border border-[var(--border)]">
          <div className="w-60 shrink-0 overflow-y-auto border-r border-[var(--border)] bg-[var(--card-bg)]/40 p-2">
            <FileTreeView
              node={tree}
              prefix=""
              depth={0}
              selectedPath={selected}
              collapsed={collapsed}
              onToggleDir={(path) =>
                setCollapsed((prev) => {
                  const next = new Set(prev);
                  if (next.has(path)) next.delete(path);
                  else next.add(path);
                  return next;
                })
              }
              onSelectFile={setSelected}
            />
          </div>
          {selected ? (
            <FileViewer source={skill.name} path={selected} load={(path) => getSkillFileContent(skill.name, path)} />
          ) : (
            <p className="p-5 text-sm text-[var(--muted)]">No files.</p>
          )}
        </div>
      )}
    </div>
  );
}
