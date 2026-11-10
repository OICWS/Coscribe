import { useEffect, useRef, useState } from "react";
import { readStored, writeStored } from "../../lib/storage";
import { useClickOutside } from "../../lib/useClickOutside";
import { isViewable } from "../../lib/viewers";
import { openThreadFile, threadFileDownloadUrl } from "../../lib/rest";
import {
  appPath,
  baseName,
  closeTab,
  type FileRef,
  fileKind,
  getRoots,
  hasSource,
  keepTab,
  NO_TABS,
  openTab,
  refKey,
  sameRef,
  type Tabs,
  type WorkspaceRoot,
} from "../../lib/workspaceFiles";
import { useDockPanel } from "../dock/dockContext";
import { CheckIcon, CloseIcon, CodeIcon, EyeIcon, MoreIcon, SearchIcon } from "../icons";
import { itemClass, menuClass } from "../menuStyle";
import { PinIcon } from "../dock/windowIcons";
import { CollapseAllIcon, TreeToggleIcon } from "./fileIcons";
import { FilePreview } from "./FilePreview";
import { FileTree } from "./FileTree";

const TREE_KEY = "coscribe.files.tree";
const WRAP_KEY = "coscribe.files.wrap";

/** The panel's own view settings, kept in the browser: whether the tree shows and long lines wrap. */
function useViewSettings() {
  const [treeOpen, setTreeOpen] = useState(() => readStored(TREE_KEY) !== "closed");
  const [wrap, setWrap] = useState(() => readStored(WRAP_KEY) !== "off");
  const [findKey, setFindKey] = useState(0);
  const showTree = (open: boolean) => {
    setTreeOpen(open);
    writeStored(TREE_KEY, open ? "open" : "closed");
  };
  // While the panel is open, Ctrl+P finds a file, as in an editor, rather than printing the app.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.altKey || e.key.toLowerCase() !== "p") return;
      e.preventDefault();
      showTree(true);
      setFindKey((k) => k + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  return {
    treeOpen,
    showTree,
    wrap,
    setWrap: (on: boolean) => {
      setWrap(on);
      writeStored(WRAP_KEY, on ? "on" : "off");
    },
    findKey,
    goToFile: () => {
      showTree(true);
      setFindKey((k) => k + 1);
    },
  };
}
type ViewSettings = ReturnType<typeof useViewSettings>;
const iconButton = (on: boolean) =>
  `flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${on ? "bg-[var(--card-bg)] text-[var(--fg)]" : "text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"}`;

/** The conversation's folders: a tree to the right, the open files as tabs, each shown drawn or
 * as highlighted source. Read only; a file is changed by asking, or in its own program. */
export function FilesPanel({ threadId, refreshKey, onView }: { threadId: string; refreshKey: string; onView: (path: string) => boolean }) {
  const dock = useDockPanel();
  const [roots, setRoots] = useState<WorkspaceRoot[] | null>(null);
  const [rootsError, setRootsError] = useState<string | null>(null);
  const [tabs, setTabs] = useState<Tabs>(NO_TABS);
  const [sourceOf, setSourceOf] = useState<Set<string>>(new Set());
  const view = useViewSettings();
  const { treeOpen, showTree } = view;
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    void getRoots(threadId)
      .then((r) => !cancelled && setRoots(r))
      .catch((e: Error) => !cancelled && setRootsError(e.message));
    return () => {
      cancelled = true;
    };
  }, [threadId, refreshKey]);

  const active = tabs.active;
  const kind = active ? fileKind(active.path) : null;
  const source = !!active && kind !== null && hasSource(kind) && sourceOf.has(refKey(active));
  const toggleSource = () => {
    if (!active) return;
    const next = new Set(sourceOf);
    if (next.has(refKey(active))) next.delete(refKey(active));
    else next.add(refKey(active));
    setSourceOf(next);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-12 shrink-0 items-center gap-1 px-2" {...dock.headerProps}>
        <div role="tablist" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {tabs.open.length === 0 && <span className="px-2 text-[15px]">Files</span>}
          {tabs.open.map(({ ref, kept }) => (
            <FileTab
              key={refKey(ref)}
              name={baseName(ref.path)}
              title={ref.path}
              selected={sameRef(ref, active)}
              kept={kept}
              onSelect={() => setTabs((t) => openTab(t, ref))}
              onKeep={() => setTabs((t) => keepTab(t, ref))}
              onClose={() => setTabs((t) => closeTab(t, ref))}
            />
          ))}
        </div>
        {dock.controls}
      </div>
      <div className="flex h-12 shrink-0 items-center gap-1 border-y border-[var(--border)] px-3">
        <Breadcrumb roots={roots} file={active} />
        {active && kind && hasSource(kind) && (
          <button type="button" title={source ? "Preview" : "View source"} aria-pressed={source} className={iconButton(source)} onClick={toggleSource}>
            {source ? <EyeIcon className="h-[18px] w-[18px]" /> : <CodeIcon className="h-[18px] w-[18px]" />}
          </button>
        )}
        {treeOpen && (
          <button type="button" title="Collapse folders" className={iconButton(false)} onClick={() => setExpanded(new Set())}>
            <CollapseAllIcon className="h-[18px] w-[18px]" />
          </button>
        )}
        <button type="button" title={treeOpen ? "Hide file tree" : "Show file tree"} aria-pressed={treeOpen} className={iconButton(treeOpen)} onClick={() => showTree(!treeOpen)}>
          <TreeToggleIcon className="h-[18px] w-[18px]" />
        </button>
        <FileMenu threadId={threadId} path={active && roots ? appPath(roots, active) : null} onView={onView} view={view} onCollapse={() => setExpanded(new Set())} />
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="min-h-0 min-w-0 flex-1">
          {active && kind ? (
            <FilePreview
              key={refKey(active)}
              threadId={threadId}
              file={active}
              kind={kind}
              source={source}
              wrap={view.wrap}
              refreshKey={refreshKey}
              fallback={roots && <NoPreview threadId={threadId} path={appPath(roots, active)} onView={onView} />}
            />
          ) : (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-[var(--muted)]">
              {rootsError ?? "Pick a file to see it here."}
            </div>
          )}
        </div>
        {treeOpen && roots && (
          <TreePane findKey={view.findKey} threadId={threadId} roots={roots} refreshKey={refreshKey} expanded={expanded} onExpanded={setExpanded} selected={active} onOpen={(ref, keep) => setTabs((t) => openTab(t, ref, keep))} />
        )}
      </div>
    </div>
  );
}

function TreePane({ findKey, ...props }: Omit<Parameters<typeof FileTree>[0], "filter"> & { findKey: number }) {
  const [filter, setFilter] = useState("");
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (findKey > 0) input.current?.focus();
  }, [findKey]);
  return (
    <div className="flex w-[42%] min-w-[220px] max-w-[420px] shrink-0 flex-col border-l border-[var(--border)]">
      <label className="m-3 flex h-10 shrink-0 items-center gap-2 rounded-xl border border-[var(--border)] px-3 focus-within:border-[var(--accent)]">
        <SearchIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        <input
          ref={input}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setFilter("")}
          placeholder="Filter files..."
          aria-label="Filter files"
          className="min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-[var(--muted)]"
        />
      </label>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <FileTree {...props} filter={filter} />
      </div>
    </div>
  );
}

function FileTab(props: { name: string; title: string; selected: boolean; kept: boolean; onSelect: () => void; onKeep: () => void; onClose: () => void }) {
  const { name, title, selected, kept, onSelect, onKeep, onClose } = props;
  return (
    <div
      role="tab"
      aria-selected={selected}
      title={title}
      className={`group flex h-9 shrink-0 cursor-default items-center gap-1 rounded-xl pl-3 pr-1 text-[15px] ${selected ? "bg-[var(--card-bg)]" : "hover:bg-[var(--card-bg)]"}`}
      onClick={onSelect}
      onDoubleClick={onKeep}
    >
      <span className={`max-w-[180px] truncate ${kept ? "" : "italic"}`}>{name}</span>
      {selected && (
        <button type="button" title={kept ? "Let the next file replace this tab" : "Keep this tab open"} aria-pressed={kept} className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:text-[var(--fg)]" onClick={(e) => { e.stopPropagation(); onKeep(); }}>
          <PinIcon className={`h-3.5 w-3.5 ${kept ? "fill-current" : ""}`} />
        </button>
      )}
      <button type="button" title="Close" className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:text-[var(--fg)]" onClick={(e) => { e.stopPropagation(); onClose(); }}>
        <CloseIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function Breadcrumb({ roots, file }: { roots: WorkspaceRoot[] | null; file: FileRef | null }) {
  if (!file) return <span className="min-w-0 flex-1" />;
  const parts = file.path.split("/");
  const shown = roots && roots.length > 1 ? [roots[file.root]?.name ?? "", ...parts] : parts;
  return (
    <span className="min-w-0 flex-1 truncate text-[15px] text-[var(--muted)]" title={file.path}>
      {shown.map((part, i) => (
        <span key={i}>
          {i > 0 && <span className="px-1">/</span>}
          <span className={i === shown.length - 1 ? "text-[var(--fg)]" : ""}>{part}</span>
        </span>
      ))}
    </span>
  );
}

function FileMenu(props: { threadId: string; path: string | null; onView: (path: string) => boolean; view: ViewSettings; onCollapse: () => void }) {
  const { threadId, path, onView, view, onCollapse } = props;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  const item = (label: string, action: () => void, end?: React.ReactNode) => (
    <button type="button" role="menuitem" className={itemClass} onClick={() => { setOpen(false); action(); }}>
      <span className="flex-1">{label}</span>
      {end}
    </button>
  );
  const check = (on: boolean) => on && <CheckIcon className="h-4 w-4 text-[var(--accent)]" />;
  const hint = (keys: string) => <span className="text-xs text-[var(--muted)]">{keys}</span>;
  const line = <div className="my-1 border-t border-[var(--border)]" />;
  return (
    <div ref={ref} className="relative">
      <button type="button" title="More" aria-expanded={open} className={iconButton(open)} onClick={() => setOpen(!open)}>
        <MoreIcon className="h-[18px] w-[18px]" />
      </button>
      {open && (
        <div role="menu" className={`${menuClass} absolute right-0 top-9 w-64`}>
          {item("Go to file", view.goToFile, hint("Ctrl+P"))}
          {line}
          {item("Show file tree", () => view.showTree(!view.treeOpen), check(view.treeOpen))}
          {item("Collapse all folders", onCollapse)}
          {line}
          {item("Word wrap", () => view.setWrap(!view.wrap), check(view.wrap))}
          {path && (
            <>
              {line}
              {isViewable(path) && item("Open in Viewer", () => onView(path))}
              {item("Open in its app", () => void openThreadFile(threadId, path, false))}
              {item("Show in folder", () => void openThreadFile(threadId, path, true))}
              {item("Copy path", () => void navigator.clipboard.writeText(path))}
              <a role="menuitem" className={itemClass} href={threadFileDownloadUrl(threadId, path)} onClick={() => setOpen(false)}>Download</a>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function NoPreview({ threadId, path, onView }: { threadId: string; path: string; onView: (path: string) => boolean }) {
  const link = "rounded-lg border border-[var(--border)] px-3 py-1.5 text-[var(--fg)] hover:bg-[var(--card-bg)]";
  return (
    <span className="flex flex-col items-center gap-3">
      <span>No preview for this file here.</span>
      <span className="flex gap-2">
        {isViewable(path) && <button type="button" className={link} onClick={() => onView(path)}>Open in Viewer</button>}
        <button type="button" className={link} onClick={() => void openThreadFile(threadId, path, false)}>Open in its app</button>
      </span>
    </span>
  );
}
