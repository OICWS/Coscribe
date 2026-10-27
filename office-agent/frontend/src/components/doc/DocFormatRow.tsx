import type { Editor } from "@tiptap/core";
import { useEditorState } from "@tiptap/react";
import { ChevronDownIcon, LinkIcon, MessageCircleIcon } from "../icons";
import { BoldIcon, CommentPlusIcon, ItalicIcon, ListIcon } from "../slides/formatIcons";
import type { MenuEntry } from "../slides/SlideMenu";
import { currentStyle, listEntries, styleEntries } from "./docCommands";
import { CodeInlineIcon, StrikeIcon } from "./docIcons";

const tool = (active: boolean) => `flex h-8 w-8 items-center justify-center rounded-md hover:bg-[var(--card-bg)] ${active ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`;
const divider = <span className="mx-0.5 h-5 border-l border-[var(--border)]" />;

/** The row of tools over selected words: the text style, bold, italic, strike, code, lists, a link, a
 * comment and, where there is a conversation, a request to coscribe. */
export function DocFormatRow({
  editor,
  canAsk,
  onAsk,
  onComment,
  onLink,
  onMenu,
}: {
  editor: Editor;
  canAsk: boolean;
  onAsk: () => void;
  onComment: () => void;
  onLink: () => void;
  onMenu: (anchor: DOMRect, entries: MenuEntry[]) => void;
}) {
  const now = useEditorState({
    editor,
    selector: ({ editor: e }) => ({ style: currentStyle(e), bold: e.isActive("bold"), italic: e.isActive("italic"), strike: e.isActive("strike"), code: e.isActive("code"), link: e.isActive("link") }),
  });
  const mark = (command: "toggleBold" | "toggleItalic" | "toggleStrike" | "toggleCode") => () => editor.chain().focus()[command]().run();
  const menu = (entries: MenuEntry[]) => (e: React.MouseEvent<HTMLButtonElement>) => onMenu(e.currentTarget.getBoundingClientRect(), entries);
  return (
    <div
      role="toolbar"
      aria-label="Format selected text"
      className="flex items-center gap-0.5 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1 shadow-[0_8px_28px_rgba(0,0,0,0.12)]"
      onMouseDown={(e) => e.preventDefault()}
    >
      <button type="button" aria-haspopup="menu" title="Text style" className="flex h-8 items-center gap-1 rounded-md px-2 text-sm hover:bg-[var(--card-bg)]" onClick={menu(styleEntries(editor))}>
        {now.style}
        <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
      </button>
      {divider}
      <button type="button" title="Bold" aria-label="Bold" aria-pressed={now.bold} className={tool(now.bold)} onClick={mark("toggleBold")}>
        <BoldIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Italic" aria-label="Italic" aria-pressed={now.italic} className={tool(now.italic)} onClick={mark("toggleItalic")}>
        <ItalicIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Strikethrough" aria-label="Strikethrough" aria-pressed={now.strike} className={tool(now.strike)} onClick={mark("toggleStrike")}>
        <StrikeIcon className="h-4 w-4" />
      </button>
      <button type="button" title="Code" aria-label="Code" aria-pressed={now.code} className={tool(now.code)} onClick={mark("toggleCode")}>
        <CodeInlineIcon className="h-4 w-4" />
      </button>
      {divider}
      <button
        type="button"
        aria-haspopup="menu"
        title="List"
        aria-label="List"
        className="flex h-8 items-center gap-0.5 rounded-md px-1.5 hover:bg-[var(--card-bg)]"
        onClick={menu(listEntries(editor))}
      >
        <ListIcon className="h-4 w-4" />
        <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
      </button>
      <button type="button" title="Link" aria-label="Link" aria-pressed={now.link} className={tool(now.link)} onClick={onLink}>
        <LinkIcon className="h-4 w-4" />
      </button>
      {divider}
      <button type="button" title="Comment" aria-label="Comment" className={tool(false)} onClick={onComment}>
        <CommentPlusIcon className="h-4 w-4" />
      </button>
      {canAsk && (
        <button type="button" className="flex h-8 items-center gap-1.5 rounded-md px-2 text-sm hover:bg-[var(--card-bg)]" onClick={onAsk}>
          <MessageCircleIcon className="h-4 w-4" />
          Ask coscribe
        </button>
      )}
    </div>
  );
}
