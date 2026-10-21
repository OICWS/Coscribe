import type { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import { useState } from "react";
import { ChevronDownIcon, LinkIcon, RedoIcon, UndoIcon } from "../icons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { BoldIcon, ItalicIcon, ListIcon, UnderlineIcon } from "../slides/formatIcons";
import { choosePicture } from "../../lib/docsPictures";
import { ImageIcon, OrderedListIcon, QuoteIcon, TableIcon } from "./docsIcons";
import { LinkDialog } from "./LinkDialog";

const STYLES = ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Quote"] as const;
type StyleName = (typeof STYLES)[number];

const button = (active: boolean) =>
  `flex h-8 w-8 items-center justify-center rounded-md hover:bg-[var(--card-bg)] disabled:opacity-40 ${active ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`;

function setStyle(editor: Editor, style: StyleName) {
  const chain = editor.chain().focus();
  if (style === "Normal") chain.setParagraph().run();
  else if (style === "Title") chain.setNode("title").run();
  else if (style === "Quote") chain.setParagraph().setBlockquote().run();
  else chain.setHeading({ level: Number(style.slice(-1)) as 1 | 2 | 3 }).run();
}

function tableEntries(editor: Editor, inTable: boolean): MenuEntry[] {
  const run = (command: (chain: ReturnType<Editor["chain"]>) => { run: () => boolean }) => () => command(editor.chain().focus()).run();
  if (!inTable) return [{ label: "Insert table (3 × 3)", onSelect: run((c) => c.insertTable({ rows: 3, cols: 3, withHeaderRow: true })) }];
  return [
    { label: "Add row below", onSelect: run((c) => c.addRowAfter()) },
    { label: "Add column to the right", onSelect: run((c) => c.addColumnAfter()) },
    { label: "Delete row", onSelect: run((c) => c.deleteRow()) },
    { label: "Delete column", onSelect: run((c) => c.deleteColumn()) },
    "divider",
    { label: "Delete table", danger: true, onSelect: run((c) => c.deleteTable()) },
  ];
}

/** The editor's one row of tools (decision 0019): undo, the style, bold, italic, underline, lists,
 * a link, a table. Styles, not fonts: the look of each style is the document's. */
export function DocsToolbar({ editor }: { editor: Editor }) {
  const [menu, setMenu] = useState<{ kind: "style" | "table"; anchor: DOMRect } | null>(null);
  const [linking, setLinking] = useState(false);
  const now = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      style: (e.isActive("title") ? "Title" : e.isActive("heading") ? `Heading ${e.getAttributes("heading").level}` : e.isActive("blockquote") ? "Quote" : "Normal") as StyleName,
      bold: e.isActive("bold"),
      italic: e.isActive("italic"),
      underline: e.isActive("underline"),
      bullets: e.isActive("bulletList"),
      numbers: e.isActive("orderedList"),
      link: e.isActive("link"),
      inTable: e.isActive("table"),
      undo: e.can().undo(),
      redo: e.can().redo(),
    }),
  });
  const toggle = (what: "toggleBold" | "toggleItalic" | "toggleUnderline" | "toggleBulletList" | "toggleOrderedList") => () => editor.chain().focus()[what]().run();
  return (
    <div className="flex h-11 shrink-0 items-center gap-0.5 border-y border-[var(--border)] px-2" onPointerDown={(e) => e.preventDefault()}>
      <button type="button" title="Undo" aria-label="Undo" className={button(false)} disabled={!now.undo} onClick={() => editor.chain().focus().undo().run()}>
        <UndoIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Redo" aria-label="Redo" className={button(false)} disabled={!now.redo} onClick={() => editor.chain().focus().redo().run()}>
        <RedoIcon className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button
        type="button"
        aria-haspopup="menu"
        title="Paragraph style"
        className="flex h-8 items-center gap-1 rounded-md px-2 text-sm text-[var(--fg)] hover:bg-[var(--card-bg)]"
        onClick={(e) => setMenu({ kind: "style", anchor: e.currentTarget.getBoundingClientRect() })}
      >
        {now.style}
        <ChevronDownIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button type="button" title="Bold" aria-label="Bold" aria-pressed={now.bold} className={button(now.bold)} onClick={toggle("toggleBold")}>
        <BoldIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Italic" aria-label="Italic" aria-pressed={now.italic} className={button(now.italic)} onClick={toggle("toggleItalic")}>
        <ItalicIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Underline" aria-label="Underline" aria-pressed={now.underline} className={button(now.underline)} onClick={toggle("toggleUnderline")}>
        <UnderlineIcon className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button type="button" title="Bulleted list" aria-label="Bulleted list" aria-pressed={now.bullets} className={button(now.bullets)} onClick={toggle("toggleBulletList")}>
        <ListIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Numbered list" aria-label="Numbered list" aria-pressed={now.numbers} className={button(now.numbers)} onClick={toggle("toggleOrderedList")}>
        <OrderedListIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Quote" aria-label="Quote" aria-pressed={now.style === "Quote"} className={button(now.style === "Quote")} onClick={() => setStyle(editor, now.style === "Quote" ? "Normal" : "Quote")}>
        <QuoteIcon className="h-4 w-4" />
      </button>
      <span className="mx-1 h-5 border-l border-[var(--border)]" />
      <button type="button" title="Link" aria-label="Link" aria-pressed={now.link} className={button(now.link)} onClick={() => setLinking(true)}>
        <LinkIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Picture" aria-label="Picture" className={button(false)} onClick={() => choosePicture(editor)}>
        <ImageIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-haspopup="menu"
        title="Table"
        aria-label="Table"
        className={button(now.inTable)}
        onClick={(e) => setMenu({ kind: "table", anchor: e.currentTarget.getBoundingClientRect() })}
      >
        <TableIcon className="h-4 w-4" />
      </button>
      {menu && (
        <SlideMenu
          anchor={menu.anchor}
          label={menu.kind === "style" ? "Paragraph style" : "Table"}
          width={menu.kind === "style" ? 180 : 230}
          align="left"
          entries={
            menu.kind === "style"
              ? STYLES.map((name) => ({ label: name, checked: now.style === name, onSelect: () => setStyle(editor, name) }))
              : tableEntries(editor, now.inTable)
          }
          onClose={() => setMenu(null)}
        />
      )}
      {linking && <LinkDialog editor={editor} onClose={() => setLinking(false)} />}
    </div>
  );
}
