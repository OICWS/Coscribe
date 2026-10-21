import type { Editor } from "@tiptap/core";
import { BubbleMenu } from "@tiptap/react/menus";
import { TextSelection } from "@tiptap/pm/state";
import { useState } from "react";
import { LinkIcon, MessageCircleIcon } from "../icons";
import { BoldIcon, ItalicIcon, UnderlineIcon } from "../slides/formatIcons";
import { LinkDialog } from "./LinkDialog";

const tool = (active: boolean) =>
  `flex h-8 w-8 items-center justify-center rounded-md hover:bg-[var(--card-bg)] ${active ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`;

/** The bar over selected words: bold, italic, underline, a link and, where there is a conversation,
 * a question about those words for coscribe. Pressing a button keeps the selection. */
export function DocsBubble({ editor, onAsk }: { editor: Editor; onAsk?: (words: string) => void }) {
  const [linking, setLinking] = useState(false);
  const run = (command: "toggleBold" | "toggleItalic" | "toggleUnderline") => () => editor.chain().focus()[command]().run();
  const words = () => editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to, "\n");
  return (
    <>
      <BubbleMenu
        editor={editor}
        options={{ placement: "top" }}
        shouldShow={({ editor: e, state }) => e.isEditable && !state.selection.empty && state.selection instanceof TextSelection && !e.isActive("lockedBlock")}
      >
        <div role="toolbar" aria-label="Format selected text" className="flex items-center gap-0.5 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1 shadow-[0_8px_28px_rgba(0,0,0,0.12)]" onMouseDown={(e) => e.preventDefault()}>
          <button type="button" title="Bold" aria-label="Bold" className={tool(editor.isActive("bold"))} onClick={run("toggleBold")}>
            <BoldIcon className="h-4 w-4" />
          </button>
          <button type="button" title="Italic" aria-label="Italic" className={tool(editor.isActive("italic"))} onClick={run("toggleItalic")}>
            <ItalicIcon className="h-4 w-4" />
          </button>
          <button type="button" title="Underline" aria-label="Underline" className={tool(editor.isActive("underline"))} onClick={run("toggleUnderline")}>
            <UnderlineIcon className="h-4 w-4" />
          </button>
          <button type="button" title="Link" aria-label="Link" className={tool(editor.isActive("link"))} onClick={() => setLinking(true)}>
            <LinkIcon className="h-4 w-4" />
          </button>
          {onAsk && (
            <>
              <span className="mx-0.5 h-5 border-l border-[var(--border)]" />
              <button type="button" className="flex h-8 items-center gap-1.5 rounded-md px-2 text-sm text-[var(--fg)] hover:bg-[var(--card-bg)]" onClick={() => onAsk(words())}>
                <MessageCircleIcon className="h-4 w-4" />
                Ask coscribe
              </button>
            </>
          )}
        </div>
      </BubbleMenu>
      {linking && <LinkDialog editor={editor} onClose={() => setLinking(false)} />}
    </>
  );
}
