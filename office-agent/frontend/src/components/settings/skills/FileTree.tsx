import { ChevronDownIcon, FolderIcon } from "../../icons";
import type { FileTreeNode } from "./helpers";

export function FileTreeView({
  node,
  prefix,
  depth,
  selectedPath,
  collapsed,
  onToggleDir,
  onSelectFile,
}: {
  node: FileTreeNode;
  prefix: string;
  depth: number;
  selectedPath: string | null;
  collapsed: Set<string>;
  onToggleDir: (path: string) => void;
  onSelectFile: (path: string) => void;
}) {
  const indent = { paddingLeft: 10 + depth * 18 };
  // SKILL.md first, as the entry point; then folders, then other files.
  const entry = node.files.filter((f) => f === "SKILL.md");
  const rest = node.files.filter((f) => f !== "SKILL.md").sort((a, b) => a.localeCompare(b));
  const fileButton = (fileName: string) => {
    const filePath = prefix ? `${prefix}/${fileName}` : fileName;
    return (
      <FileButton key={filePath} path={filePath} name={fileName} indent={indent} selected={filePath === selectedPath} onSelect={onSelectFile} />
    );
  };
  return (
    <>
      {entry.map(fileButton)}
      {[...node.dirs.keys()].sort().map((dirName) => {
        const dirPath = prefix ? `${prefix}/${dirName}` : dirName;
        const open = !collapsed.has(dirPath);
        return (
          <div key={dirPath}>
            <button
              type="button"
              aria-expanded={open}
              className="flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-left text-[15px] text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              style={indent}
              onClick={() => onToggleDir(dirPath)}
            >
              <FolderIcon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 flex-1 truncate">{dirName}</span>
              <ChevronDownIcon className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "" : "-rotate-90"}`} />
            </button>
            {open && (
              <FileTreeView
                node={node.dirs.get(dirName)!}
                prefix={dirPath}
                depth={depth + 1}
                selectedPath={selectedPath}
                collapsed={collapsed}
                onToggleDir={onToggleDir}
                onSelectFile={onSelectFile}
              />
            )}
          </div>
        );
      })}
      {rest.map(fileButton)}
    </>
  );
}

function FileButton({
  path,
  name,
  indent,
  selected,
  onSelect,
}: {
  path: string;
  name: string;
  indent: { paddingLeft: number };
  selected: boolean;
  onSelect: (path: string) => void;
}) {
  return (
    <button
      type="button"
      title={path}
      className={`block w-full truncate rounded-md py-1.5 pr-2 text-left text-[15px] ${
        selected ? "bg-[var(--card-bg)] font-medium text-[var(--fg)]" : "text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
      }`}
      style={{ paddingLeft: indent.paddingLeft + (indent.paddingLeft > 10 ? 6 : 0) }}
      onClick={() => onSelect(path)}
    >
      {name}
    </button>
  );
}
