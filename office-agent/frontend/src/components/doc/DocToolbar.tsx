import type { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import { useState } from "react";
import type { DocLook, Face } from "../../lib/docLook";
import { ChevronDownIcon, MoreIcon, PlusIcon, RedoIcon, UndoIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { TableIcon } from "../slides/formatIcons";
import { calloutEntries, insertEntries, tableEntries } from "./docCommands";
import { ChecklistIcon, FontIcon, ImageIcon, WidthIcon } from "./docIcons";

const button = (active = false) =>
  `flex h-8 w-8 items-center justify-center rounded-md hover:bg-[var(--card-bg)] disabled:opacity-40 ${active ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`;

type Menu = "font" | "insert" | "table" | "callout";

function fontEntries(look: DocLook, onLook: (look: DocLook) => void): MenuEntry[] {
  const face = (group: "headings" | "text", name: Face): MenuEntry => ({
    label: name === "serif" ? "Serif" : "Sans",
    checked: look[group] === name,
    onSelect: () => onLook({ ...look, [group]: name }),
  });
  return [{ note: "Headings" }, face("headings", "serif"), face("headings", "sans"), "divider", { note: "Text" }, face("text", "serif"), face("text", "sans")];
}

/** The editor's one row of tools: the reading look (font, width), then the blocks a Doc can hold. What
 * a Doc looks like is the reader's choice, kept in the browser; the file holds only the words. */
export function DocToolbar({ editor, look, onLook, onPicture }: { editor: Editor; look: DocLook; onLook: (look: DocLook) => void; onPicture: () => void }) {
  const [menu, setMenu] = useState<{ kind: Menu; anchor: DOMRect } | null>(null);
  const now = useEditorState({
    editor,
    selector: ({ editor: e }) => ({ inTable: e.isActive("table"), inCallout: e.isActive("callout"), tasks: e.isActive("taskList"), undo: e.can().undo(), redo: e.can().redo() }),
  });
  const open = (kind: Menu) => (e: React.MouseEvent<HTMLButtonElement>) => setMenu({ kind, anchor: e.currentTarget.getBoundingClientRect() });
  const entries = menu?.kind === "font" ? fontEntries(look, onLook) : menu?.kind === "table" ? tableEntries(editor) : menu?.kind === "callout" ? calloutEntries(editor) : insertEntries(editor);
  return (
    <div className="flex h-11 shrink-0 items-center gap-0.5 border-y border-[var(--border)] px-2" role="toolbar" aria-label="Document tools" onPointerDown={(e) => e.preventDefault()}>
      <button type="button" title="Undo" aria-label="Undo" className={button()} disabled={!now.undo} onClick={() => editor.chain().focus().undo().run()}>
        <UndoIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Redo" aria-label="Redo" className={button()} disabled={!now.redo} onClick={() => editor.chain().focus().redo().run()}>
        <RedoIcon className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button type="button" aria-haspopup="menu" title="Font" aria-label="Font" className={button()} onClick={open("font")}>
        <FontIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        title={look.wide ? "Back to default width" : "Wider page"}
        aria-label={look.wide ? "Back to default width" : "Wider page"}
        aria-pressed={look.wide}
        className={button()}
        onClick={() => onLook({ ...look, wide: !look.wide })}
      >
        <WidthIcon wide={look.wide} className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button type="button" title="Table" aria-label="Table" className={button(now.inTable)} onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}>
        <TableIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Picture" aria-label="Picture" className={button()} onClick={onPicture}>
        <ImageIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Checklist" aria-label="Checklist" aria-pressed={now.tasks} className={button(now.tasks)} onClick={() => editor.chain().focus().toggleTaskList().run()}>
        <ChecklistIcon className="h-4 w-4" />
      </button>
      <button type="button" aria-haspopup="menu" title="Insert" aria-label="Insert" className="flex h-8 items-center gap-0.5 rounded-md px-1.5 hover:bg-[var(--card-bg)]" onClick={open("insert")}>
        <PlusIcon className="h-4 w-4" />
        <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
      </button>
      {now.inTable && (
        <button type="button" aria-haspopup="menu" title="Table options" aria-label="Table options" className={button()} onClick={open("table")}>
          <MoreIcon className="h-4 w-4" />
        </button>
      )}
      {now.inCallout && (
        <button
          type="button"
          aria-haspopup="menu"
          title="Callout kind"
          aria-label="Callout kind"
          className="flex h-8 items-center gap-1 rounded-md px-2 text-sm hover:bg-[var(--card-bg)]"
          onClick={open("callout")}
        >
          Callout
          <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
        </button>
      )}
      {menu && <SlideMenu anchor={menu.anchor} label={menu.kind} width={menu.kind === "table" ? 200 : 190} align="left" entries={entries} onClose={() => setMenu(null)} />}
    </div>
  );
}
