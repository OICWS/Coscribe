import { useCallback, useEffect, useRef, useState } from "react";
import {
  baseName,
  type FileRef,
  fileKind,
  listFolder,
  sameRef,
  searchFiles,
  type WorkspaceEntry,
  type WorkspaceRoot,
} from "../../lib/workspaceFiles";
import { ChevronRightIcon } from "../icons";
import { FileCodeIcon, FileIcon, FileImageIcon, FileTextIcon } from "./fileIcons";

type Folder = { entries: WorkspaceEntry[]; truncated: boolean } | { error: string };

const folderKey = (root: number, path: string) => `${root}:${path}`;
const join = (folder: string, name: string) => (folder ? `${folder}/${name}` : name);

function KindIcon({ name }: { name: string }) {
  const kind = fileKind(name);
  const icon = "h-4 w-4 shrink-0";
  if (kind === "markdown" || kind === "office" || kind === "pdf") return <FileTextIcon className={icon} />;
  if (kind === "image" || kind === "svg") return <FileImageIcon className={icon} />;
  if (kind === "html") return <FileCodeIcon className={icon} />;
  if (kind === "text" && /^[^.].*\.[a-z0-9]+$/i.test(baseName(name)) && !/\.(txt|log)$/i.test(name)) return <FileCodeIcon className={icon} />;
  return <FileIcon className={icon} />;
}

const row = (selected: boolean, dim?: boolean) =>
  `flex w-full items-center gap-2 rounded-lg py-1.5 pr-2 text-left text-[15px] ${
    selected ? "bg-[var(--card-bg)]" : "hover:bg-[var(--card-bg)]"
  } ${dim ? "text-[var(--muted)]" : "text-[var(--fg)]"}`;

/** The conversation's folders as a tree loaded one level at a time, or, while `filter` holds
 * text, the files whose names match it. */
export function FileTree({
  threadId,
  roots,
  refreshKey,
  filter,
  expanded,
  onExpanded,
  selected,
  onOpen,
}: {
  threadId: string;
  roots: WorkspaceRoot[];
  refreshKey: string;
  filter: string;
  expanded: Set<string>;
  onExpanded: (next: Set<string>) => void;
  selected: FileRef | null;
  onOpen: (ref: FileRef, keep: boolean) => void;
}) {
  const [folders, setFolders] = useState<Record<string, Folder>>({});
  const asked = useRef(new Set<string>());

  const load = useCallback(
    (root: number, path: string) => {
      const key = folderKey(root, path);
      asked.current.add(key);
      void listFolder(threadId, root, path)
        .then((listing): Folder => listing)
        .catch((error: Error): Folder => ({ error: error.message }))
        .then((folder) => setFolders((all) => ({ ...all, [key]: folder })));
    },
    [threadId],
  );

  // Every folder open now is read again when the conversation may have changed files.
  useEffect(() => {
    roots.forEach((_, root) => load(root, ""));
    expanded.forEach((key) => {
      const at = key.indexOf(":");
      load(Number(key.slice(0, at)), key.slice(at + 1));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- a toggle loads its own folder
  }, [roots, refreshKey, load]);

  const toggle = (root: number, path: string) => {
    const key = folderKey(root, path);
    const next = new Set(expanded);
    if (next.has(key)) next.delete(key);
    else {
      next.add(key);
      if (!asked.current.has(key)) load(root, path);
    }
    onExpanded(next);
  };

  const rows = { folders, expanded, toggle, selected, onOpen };

  if (filter.trim()) return <SearchResults threadId={threadId} roots={roots} query={filter.trim()} selected={selected} onOpen={onOpen} />;
  if (roots.length === 1) return <div className="px-2 pb-4">{<FolderRows {...rows} root={0} path="" depth={0} />}</div>;
  return (
    <div className="px-2 pb-4">
      {roots.map((root, index) => {
        const open = expanded.has(folderKey(index, "")) !== (index === 0);
        return (
          <div key={root.path}>
            <button type="button" aria-expanded={open} title={root.path} className={`${row(false)} font-medium`} onClick={() => toggle(index, "")}>
              <ChevronRightIcon className={`h-3.5 w-3.5 shrink-0 text-[var(--muted)] transition-transform ${open ? "rotate-90" : ""}`} />
              <span className="min-w-0 flex-1 truncate">{root.name}</span>
            </button>
            {open && <FolderRows {...rows} root={index} path="" depth={1} />}
          </div>
        );
      })}
    </div>
  );
}

interface RowsProps {
  folders: Record<string, Folder>;
  expanded: Set<string>;
  toggle: (root: number, path: string) => void;
  selected: FileRef | null;
  onOpen: (ref: FileRef, keep: boolean) => void;
  root: number;
  path: string;
  depth: number;
}

function FolderRows(props: RowsProps) {
  const { folders, expanded, toggle, selected, onOpen, root, path, depth } = props;
  const folder = folders[folderKey(root, path)];
  const indent = 8 + depth * 15;
  if (!folder) return <p className="py-1 text-sm text-[var(--muted)]" style={{ paddingLeft: indent + 22 }}>Loading...</p>;
  if ("error" in folder) return <p className="py-1 text-sm text-[var(--muted)]" style={{ paddingLeft: indent + 22 }}>{folder.error}</p>;
  if (folder.entries.length === 0 && depth === 0) return <p className="px-3 py-2 text-sm text-[var(--muted)]">This folder is empty.</p>;
  return (
    <>
      {folder.entries.map((entry) => {
        const entryPath = join(path, entry.name);
        if (entry.dir) {
          const open = expanded.has(folderKey(root, entryPath));
          return (
            <div key={entryPath}>
              <button type="button" aria-expanded={open} className={row(false, entry.dim)} style={{ paddingLeft: indent }} onClick={() => toggle(root, entryPath)}>
                <ChevronRightIcon className={`h-3.5 w-3.5 shrink-0 text-[var(--muted)] transition-transform ${open ? "rotate-90" : ""}`} />
                <span className="min-w-0 flex-1 truncate">{entry.name}</span>
              </button>
              {open && <FolderRows {...props} path={entryPath} depth={depth + 1} />}
            </div>
          );
        }
        const ref = { root, path: entryPath };
        return (
          <button
            key={entryPath}
            type="button"
            title={entryPath}
            className={row(sameRef(selected, ref))}
            style={{ paddingLeft: indent + 6 }}
            onClick={() => onOpen(ref, false)}
            onDoubleClick={() => onOpen(ref, true)}
          >
            <KindIcon name={entry.name} />
            <span className="min-w-0 flex-1 truncate">{entry.name}</span>
          </button>
        );
      })}
      {folder.truncated && <p className="py-1 text-xs text-[var(--muted)]" style={{ paddingLeft: indent + 22 }}>Only the first 2,000 are listed.</p>}
    </>
  );
}

function SearchResults({
  threadId,
  roots,
  query,
  selected,
  onOpen,
}: {
  threadId: string;
  roots: WorkspaceRoot[];
  query: string;
  selected: FileRef | null;
  onOpen: (ref: FileRef, keep: boolean) => void;
}) {
  const [found, setFound] = useState<{ query: string; refs: FileRef[] } | null>(null);
  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void Promise.all(
        roots.map((_, root) =>
          searchFiles(threadId, root, query)
            .then((r) => r.entries.filter((e) => !e.dir).map((e) => ({ root, path: e.path ?? e.name })))
            .catch(() => [] as FileRef[]),
        ),
      ).then((lists) => !cancelled && setFound({ query, refs: lists.flat() }));
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [threadId, roots, query]);

  if (!found || found.query !== query) return <p className="px-4 py-2 text-sm text-[var(--muted)]">Searching...</p>;
  if (found.refs.length === 0) return <p className="px-4 py-2 text-sm text-[var(--muted)]">No file name matches.</p>;
  return (
    <div className="px-2 pb-4">
      {found.refs.map((ref) => {
        const folder = ref.path.includes("/") ? ref.path.slice(0, ref.path.lastIndexOf("/")) : "";
        return (
          <button key={`${ref.root}:${ref.path}`} type="button" title={ref.path} className={row(sameRef(selected, ref))} style={{ paddingLeft: 10 }} onClick={() => onOpen(ref, false)} onDoubleClick={() => onOpen(ref, true)}>
            <KindIcon name={ref.path} />
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate">{baseName(ref.path)}</span>
              {(folder || roots.length > 1) && (
                <span className="truncate text-xs text-[var(--muted)]">{roots.length > 1 ? `${roots[ref.root].name}/${folder}` : folder}</span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
