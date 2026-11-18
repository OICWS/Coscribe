import { useRef, useState } from "react";
import { useClickOutside } from "../lib/useClickOutside";
import { ArchiveIcon, CheckIcon, ChevronRightIcon, FolderIcon, FolderPlusIcon, TrashIcon } from "./icons";
import { itemClass, menuClass } from "./menuStyle";

/** "Move to group" and its submenu of the conversation's possible groups. */
export function MoveToGroupItem({
  groups,
  current,
  open,
  onOpen,
  flip,
  width,
  onMove,
}: {
  groups: string[];
  current: string | null;
  open: boolean;
  onOpen: () => void;
  flip: boolean;
  width: number;
  onMove: (group: string) => void;
}) {
  return (
    <div className="relative" onMouseEnter={onOpen}>
      <button
        type="button"
        role="menuitem"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${itemClass} justify-between`}
        onClick={onOpen}
      >
        <span className="flex items-center gap-2">
          <FolderIcon className="h-3.5 w-3.5" /> Move to group
        </span>
        <ChevronRightIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label="Move to group"
          className={`${menuClass} absolute top-[-5px] ${flip ? "right-full mr-1" : "left-full ml-1"}`}
          style={{ width }}
        >
          {groups.map((group) => (
            <button
              key={group}
              type="button"
              role="menuitemradio"
              aria-checked={current === group}
              className={`${itemClass} justify-between`}
              onClick={() => onMove(group)}
            >
              <span className="min-w-0 truncate">{group}</span>
              {current === group && <CheckIcon className="h-3.5 w-3.5 shrink-0" />}
            </button>
          ))}
          {groups.length > 0 && <div className="my-1 border-t border-[var(--border)]" />}
          <button
            type="button"
            role="menuitemradio"
            aria-checked={!current}
            className={`${itemClass} justify-between`}
            onClick={() => onMove("")}
          >
            Ungrouped
            {!current && <CheckIcon className="h-3.5 w-3.5 shrink-0" />}
          </button>
          <NewGroupItem onCreate={onMove} />
        </div>
      )}
    </div>
  );
}

/** "New group..." in a menu: a button that turns into a name field. */
function NewGroupItem({ onCreate }: { onCreate: (name: string) => void }) {
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  if (!naming) {
    return (
      <button type="button" role="menuitem" className={itemClass} onClick={() => setNaming(true)}>
        <FolderPlusIcon className="h-3.5 w-3.5" /> New group…
      </button>
    );
  }
  return (
    <div className="px-2 py-1">
      <input
        autoFocus
        aria-label="New group name"
        placeholder="Group name"
        className="w-full rounded-md border border-[var(--accent)] bg-[var(--bg)] px-2 py-1 text-sm outline-none"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && name.trim()) {
            e.preventDefault();
            onCreate(name.trim());
          }
        }}
      />
    </div>
  );
}

/** The actions for the selected conversations. Rename, environment and export
 * are left out: each works on one conversation. */
export function BatchBar({
  count,
  total,
  groups,
  allArchived,
  onSelectAll,
  onMove,
  onArchive,
  onDelete,
  onCancel,
}: {
  count: number;
  total: number;
  groups: string[];
  allArchived: boolean;
  onSelectAll: () => void;
  onMove: (group: string) => void;
  onArchive: () => void;
  onDelete: () => void;
  onCancel: () => void;
}) {
  const [picking, setPicking] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setPicking(false), picking);
  const none = count === 0;
  const button = "flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-[var(--card-bg)] disabled:opacity-40";
  return (
    <div data-testid="batch-bar" className="mt-1 flex flex-col gap-1 border-t border-[var(--border)] px-1 pt-2">
      <div className="flex items-center justify-between px-1 text-xs text-[var(--muted)]">
        <span>{count} selected</span>
        <span className="flex gap-2">
          <button type="button" className="hover:text-[var(--fg)]" onClick={onSelectAll}>
            {count === total ? "Clear" : "Select all"}
          </button>
          <button type="button" className="hover:text-[var(--fg)]" onClick={onCancel}>
            Cancel
          </button>
        </span>
      </div>
      <div className="relative flex items-center justify-center gap-1" ref={ref}>
        <button type="button" disabled={none} className={button} aria-haspopup="menu" onClick={() => setPicking((v) => !v)}>
          <FolderIcon className="h-3.5 w-3.5" /> Move
        </button>
        <button type="button" disabled={none} className={button} onClick={onArchive}>
          <ArchiveIcon className="h-3.5 w-3.5" /> {allArchived ? "Unarchive" : "Archive"}
        </button>
        <button type="button" disabled={none} className={`${button} text-red-500`} onClick={onDelete}>
          <TrashIcon className="h-3.5 w-3.5" /> Delete
        </button>
        {picking && (
          <div role="menu" aria-label="Move to group" className={`${menuClass} absolute bottom-full left-1/2 mb-1 w-48 -translate-x-1/2`}>
            {groups.map((group) => (
              <button key={group} type="button" role="menuitem" className={itemClass} onClick={() => onMove(group)}>
                <span className="min-w-0 truncate">{group}</span>
              </button>
            ))}
            {groups.length > 0 && <div className="my-1 border-t border-[var(--border)]" />}
            <button type="button" role="menuitem" className={itemClass} onClick={() => onMove("")}>
              Ungrouped
            </button>
            <NewGroupItem onCreate={onMove} />
          </div>
        )}
      </div>
    </div>
  );
}

