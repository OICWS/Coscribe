import type { Editor } from "@tiptap/core";
import { TextSelection } from "@tiptap/pm/state";
import { useEditorState } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";
import { useState } from "react";
import { ChevronDownIcon, LinkIcon, MessageCircleIcon } from "../icons";
import { LinkDialog } from "../docs/LinkDialog";
import { BoldIcon, ItalicIcon, ListIcon } from "../slides/formatIcons";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { currentStyle, listEntries, styleEntries } from "./docCommands";
import { CodeInlineIcon, StrikeIcon } from "./docIcons";

const tool = (active: boolean) =>
  `flex h-8 w-8 items-center justify-center rounded-md hover:bg-[var(--card-bg)] ${active ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`;

const QUICK = ["Make it shorter", "Make it simpler", "Fix spelling and grammar"];

/** What coscribe is asked about the selected words: they are quoted, then what to do with them. */
function AskBox({ onAsk, onClose }: { onAsk: (instruction: string) => void; onClose: () => void }) {
  const [text, setText] = useState("");
  const send = (instruction: string) => {
    if (!instruction.trim()) return;
    onAsk(instruction.trim());
    onClose();
  };
  return (
    <div className="w-[min(380px,90vw)] rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3 shadow-[0_8px_28px_rgba(0,0,0,0.12)]" onMouseDown={(e) => e.stopPropagation()}>
      <input
        autoFocus
        aria-label="Tell coscribe what to change"
        placeholder="Tell coscribe what to change"
        value={text}
        className="h-9 w-full bg-transparent text-sm outline-none"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") send(text);
          if (e.key === "Escape") onClose();
        }}
      />
      <div className="mt-2 flex flex-wrap gap-1.5">
        {QUICK.map((label) => (
          <button key={label} type="button" className="rounded-full border border-[var(--border)] px-2.5 py-1 text-xs hover:bg-[var(--card-bg)]" onClick={() => send(label)}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** The bar over selected words: the text style, bold, italic, strike, code, lists and a link, and
 * where there is a conversation, a request to coscribe about those words. */
export function DocBubble({ editor, onAsk }: { editor: Editor; onAsk?: (instruction: string, words: string) => void }) {
  const [linking, setLinking] = useState(false);
  const [asking, setAsking] = useState(false);
  const [menu, setMenu] = useState<{ anchor: DOMRect; entries: MenuEntry[] } | null>(null);
  const now = useEditorState({
    editor,
    selector: ({ editor: e }) => ({ style: currentStyle(e), bold: e.isActive("bold"), italic: e.isActive("italic"), strike: e.isActive("strike"), code: e.isActive("code"), link: e.isActive("link"), list: e.isActive("bulletList") || e.isActive("orderedList") || e.isActive("taskList") }),
  });
  const mark = (command: "toggleBold" | "toggleItalic" | "toggleStrike" | "toggleCode") => () => editor.chain().focus()[command]().run();
  const words = () => editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to, "\n");
  const drop = (entries: MenuEntry[]) => (e: React.MouseEvent<HTMLButtonElement>) => setMenu({ anchor: e.currentTarget.getBoundingClientRect(), entries });
  return (
    <>
      <BubbleMenu
        editor={editor}
        options={{ placement: "top", onHide: () => setAsking(false) }}
        shouldShow={({ editor: e, state }) => e.isEditable && !state.selection.empty && state.selection instanceof TextSelection && !e.isActive("rawBlock") && !e.isActive("codeBlock")}
      >
        {asking && onAsk ? (
          <AskBox onAsk={(instruction) => onAsk(instruction, words())} onClose={() => setAsking(false)} />
        ) : (
          <div role="toolbar" aria-label="Format selected text" className="flex items-center gap-0.5 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1 shadow-[0_8px_28px_rgba(0,0,0,0.12)]" onMouseDown={(e) => e.preventDefault()}>
            <button type="button" aria-haspopup="menu" title="Text style" className="flex h-8 items-center gap-1 rounded-md px-2 text-sm hover:bg-[var(--card-bg)]" onClick={drop(styleEntries(editor))}>
              {now.style}
              <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
            </button>
            <span className="mx-0.5 h-5 border-l border-[var(--border)]" />
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
            <span className="mx-0.5 h-5 border-l border-[var(--border)]" />
            <button type="button" aria-haspopup="menu" title="List" aria-label="List" className="flex h-8 items-center gap-0.5 rounded-md px-1.5 hover:bg-[var(--card-bg)]" onClick={drop(listEntries(editor))}>
              <ListIcon className="h-4 w-4" />
              <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
            </button>
            <button type="button" title="Link" aria-label="Link" aria-pressed={now.link} className={tool(now.link)} onClick={() => setLinking(true)}>
              <LinkIcon className="h-4 w-4" />
            </button>
            {onAsk && (
              <>
                <span className="mx-0.5 h-5 border-l border-[var(--border)]" />
                <button type="button" className="flex h-8 items-center gap-1.5 rounded-md px-2 text-sm hover:bg-[var(--card-bg)]" onClick={() => setAsking(true)}>
                  <MessageCircleIcon className="h-4 w-4" />
                  Ask coscribe
                </button>
              </>
            )}
          </div>
        )}
      </BubbleMenu>
      {menu && <SlideMenu anchor={menu.anchor} label="Text" width={170} align="left" entries={menu.entries} onClose={() => setMenu(null)} />}
      {linking && <LinkDialog editor={editor} onClose={() => setLinking(false)} />}
    </>
  );
}
