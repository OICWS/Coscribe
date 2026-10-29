import type { Editor } from "@tiptap/core";
import { TextSelection } from "@tiptap/pm/state";
import { BubbleMenu } from "@tiptap/react/menus";
import { useEffect, useState } from "react";
import { LinkDialog } from "./LinkDialog";
import { SlideMenu, type MenuEntry } from "../slides/SlideMenu";
import { AskBox, Composer } from "./DocBubbleBoxes";
import { DocFormatRow } from "./DocFormatRow";

/** The bar over selected words. It turns into the box for a comment, or the box that asks coscribe about the words. */
export function DocBubble({ editor, onAsk, onComment }: { editor: Editor; onAsk?: (instruction: string, words: string) => void; onComment: (text: string, send: boolean) => void }) {
  const [linking, setLinking] = useState(false);
  const [mode, setMode] = useState<"tools" | "ask" | "comment">("tools");
  const [menu, setMenu] = useState<{ anchor: DOMRect; entries: MenuEntry[] } | null>(null);
  // The page scrolls inside its own box, and the menu only follows what it is told scrolls.
  const [scroller, setScroller] = useState<HTMLElement | null>(null);
  useEffect(() => setScroller(editor.view.dom.closest<HTMLElement>("[data-doc-scroll]")), [editor]);
  const words = () => editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to, "\n");
  const tools = () => setMode("tools");
  return (
    <>
      <BubbleMenu
        editor={editor}
        options={{ placement: "top", onHide: tools, scrollTarget: scroller ?? window }}
        shouldShow={({ editor: e, state }) => e.isEditable && !state.selection.empty && state.selection instanceof TextSelection && !e.isActive("rawBlock") && !e.isActive("codeBlock")}
      >
        {mode === "comment" && <Composer canSend={!!onAsk} onComment={onComment} onClose={tools} />}
        {mode === "ask" && onAsk && <AskBox onAsk={(instruction) => onAsk(instruction, words())} onClose={tools} />}
        {(mode === "tools" || (mode === "ask" && !onAsk)) && (
          <DocFormatRow
            editor={editor}
            canAsk={!!onAsk}
            onAsk={() => setMode("ask")}
            onComment={() => setMode("comment")}
            onLink={() => setLinking(true)}
            onMenu={(anchor, entries) => setMenu({ anchor, entries })}
          />
        )}
      </BubbleMenu>
      {menu && <SlideMenu anchor={menu.anchor} label="Text" width={170} align="left" entries={menu.entries} onClose={() => setMenu(null)} />}
      {linking && <LinkDialog editor={editor} onClose={() => setLinking(false)} />}
    </>
  );
}
