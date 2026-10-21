import { Extension, type Editor, type Range } from "@tiptap/core";
import { choosePicture } from "./docsPictures";
import Suggestion, { type SuggestionKeyDownProps, type SuggestionProps } from "@tiptap/suggestion";

/** One line of the menu that "/" opens in the editor: what it makes, and how. */
export interface SlashItem {
  id: string;
  label: string;
  hint: string;
  words: string;
  run: (editor: Editor, range: Range) => void;
}

const block = (editor: Editor, range: Range) => editor.chain().focus().deleteRange(range);

export const SLASH_ITEMS: SlashItem[] = [
  { id: "h1", label: "Heading 1", hint: "Large section title", words: "heading title h1", run: (e, r) => block(e, r).setHeading({ level: 1 }).run() },
  { id: "h2", label: "Heading 2", hint: "Section title", words: "heading h2", run: (e, r) => block(e, r).setHeading({ level: 2 }).run() },
  { id: "h3", label: "Heading 3", hint: "Smaller title", words: "heading h3", run: (e, r) => block(e, r).setHeading({ level: 3 }).run() },
  { id: "bullets", label: "Bulleted list", hint: "A list with dots", words: "bullet list dots", run: (e, r) => block(e, r).toggleBulletList().run() },
  { id: "numbers", label: "Numbered list", hint: "A list with numbers", words: "numbered ordered list", run: (e, r) => block(e, r).toggleOrderedList().run() },
  { id: "quote", label: "Quote", hint: "Set a passage apart", words: "quote blockquote", run: (e, r) => block(e, r).setParagraph().setBlockquote().run() },
  { id: "picture", label: "Picture", hint: "From a file on this computer", words: "picture image photo", run: (e, r) => { block(e, r).run(); choosePicture(e); } },
  { id: "table", label: "Table", hint: "Rows and columns, 3 × 3", words: "table grid", run: (e, r) => block(e, r).insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run() },
];

export const matchingItems = (query: string): SlashItem[] => {
  const wanted = query.trim().toLowerCase();
  return SLASH_ITEMS.filter((item) => !wanted || `${item.label} ${item.words}`.toLowerCase().includes(wanted));
};

/** What the menu's host is told while "/" is open: the lines, where to draw them, how to pick one. */
export interface SlashOpen {
  items: SlashItem[];
  rect: DOMRect | null;
  choose: (item: SlashItem) => void;
}

export interface SlashHost {
  show: (open: SlashOpen | null) => void;
  /** A key pressed while the menu is open; true when the menu used it. */
  key: (event: KeyboardEvent) => boolean;
}

/** "/" at the start of a block, or after a space, opens the menu; typing narrows it. Not inside a table,
 * whose cells hold one plain paragraph. */
export function slashExtension(host: SlashHost) {
  const report = (props: SuggestionProps<SlashItem, SlashItem>) =>
    host.show({ items: props.items, rect: props.clientRect?.() ?? null, choose: (item) => props.command(item) });
  return Extension.create({
    name: "slashCommand",
    addProseMirrorPlugins() {
      return [
        Suggestion<SlashItem, SlashItem>({
          editor: this.editor,
          char: "/",
          allow: ({ editor }) => !editor.isActive("table") && !editor.isActive("lockedBlock"),
          items: ({ query }) => matchingItems(query),
          command: ({ editor, range, props }) => props.run(editor, range),
          render: () => ({
            onStart: report,
            onUpdate: report,
            onKeyDown: ({ event }: SuggestionKeyDownProps) => host.key(event),
            onExit: () => host.show(null),
          }),
        }),
      ];
    },
  });
}
