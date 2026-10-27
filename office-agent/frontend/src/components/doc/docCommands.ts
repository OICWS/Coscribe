import type { Editor } from "@tiptap/core";
import type { MenuEntry } from "../slides/SlideMenu";

type Chain = ReturnType<Editor["chain"]>;
const run = (editor: Editor, command: (chain: Chain) => { run: () => boolean }) => () => void command(editor.chain().focus()).run();

/** What the "+" menu inserts (and the list menu offers): the blocks Markdown can hold. */
export function insertEntries(editor: Editor): MenuEntry[] {
  const at = (command: (chain: Chain) => { run: () => boolean }) => run(editor, command);
  return [
    { label: "Bulleted list", onSelect: at((c) => c.toggleBulletList()) },
    { label: "Numbered list", onSelect: at((c) => c.toggleOrderedList()) },
    { label: "Checklist", onSelect: at((c) => c.toggleTaskList()) },
    "divider",
    { label: "Heading 1", onSelect: at((c) => c.setHeading({ level: 1 })) },
    { label: "Heading 2", onSelect: at((c) => c.setHeading({ level: 2 })) },
    { label: "Heading 3", onSelect: at((c) => c.setHeading({ level: 3 })) },
    "divider",
    { label: "Quote", onSelect: at((c) => c.toggleBlockquote()) },
    { label: "Code block", onSelect: at((c) => c.toggleCodeBlock()) },
    { label: "Divider", onSelect: at((c) => c.setHorizontalRule()) },
    { label: "Table", onSelect: at((c) => c.insertTable({ rows: 3, cols: 3, withHeaderRow: true })) },
  ];
}

export function listEntries(editor: Editor): MenuEntry[] {
  return [
    { label: "Bulleted list", checked: editor.isActive("bulletList"), onSelect: run(editor, (c) => c.toggleBulletList()) },
    { label: "Numbered list", checked: editor.isActive("orderedList"), onSelect: run(editor, (c) => c.toggleOrderedList()) },
    { label: "Checklist", checked: editor.isActive("taskList"), onSelect: run(editor, (c) => c.toggleTaskList()) },
  ];
}

export type TextStyle = "Text" | "H1" | "H2" | "H3";

export const currentStyle = (editor: Editor): TextStyle => {
  for (const level of [1, 2, 3] as const) if (editor.isActive("heading", { level })) return `H${level}`;
  return "Text";
};

export function styleEntries(editor: Editor): MenuEntry[] {
  const current = currentStyle(editor);
  const entry = (label: TextStyle, command: (chain: Chain) => { run: () => boolean }): MenuEntry => ({ label, checked: current === label, onSelect: run(editor, command) });
  return [
    entry("Text", (c) => c.setParagraph()),
    entry("H1", (c) => c.setHeading({ level: 1 })),
    entry("H2", (c) => c.setHeading({ level: 2 })),
    entry("H3", (c) => c.setHeading({ level: 3 })),
  ];
}

/** What the "…" of a table offers: rows and columns added or taken out, and the table itself. */
export function tableEntries(editor: Editor): MenuEntry[] {
  const at = (command: (chain: Chain) => { run: () => boolean }) => run(editor, command);
  return [
    { label: "Add row above", onSelect: at((c) => c.addRowBefore()) },
    { label: "Add row below", onSelect: at((c) => c.addRowAfter()) },
    { label: "Add column left", onSelect: at((c) => c.addColumnBefore()) },
    { label: "Add column right", onSelect: at((c) => c.addColumnAfter()) },
    "divider",
    { label: "Delete row", onSelect: at((c) => c.deleteRow()) },
    { label: "Delete column", onSelect: at((c) => c.deleteColumn()) },
    { label: "Delete table", danger: true, onSelect: at((c) => c.deleteTable()) },
  ];
}
