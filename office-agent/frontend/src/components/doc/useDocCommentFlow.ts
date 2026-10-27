import type { Editor } from "@tiptap/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { REDRAW } from "../../lib/docCommentMarks";
import { addDocComment, docCommentsMessage, markDocCommentSent, type DocComment } from "../../lib/docComments";
import type { Loaded } from "../../lib/docModel";
import type { CommentLink } from "../../lib/slideComments";
import { useDocComments } from "./DocComments";
import type { SaveState } from "./useDocSave";

const SNIPPET = 60;

interface Marks {
  comments: unknown;
  onOpen: (id: string) => void;
}

/** What the editor does with the Doc's comments: draws the open ones on the page, makes a new one on the
 * selected words (sent to coscribe now or kept to send with others) and sends the unsent ones together. */
export function useDocCommentFlow({
  editor,
  threadId,
  path,
  refreshKey,
  saveState,
  loaded,
  flush,
  onAsk,
}: {
  editor: Editor | null;
  threadId: string;
  path: string;
  refreshKey: string;
  saveState: SaveState["kind"];
  loaded: { current: Map<number, Loaded> };
  flush: () => Promise<void>;
  onAsk?: (text: string, link?: CommentLink) => void;
}) {
  const store = useDocComments(threadId, path, refreshKey);
  const [show, setShow] = useState(false);
  const [focus, setFocus] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const open = useMemo(() => store.comments.filter((c) => !c.resolved), [store.comments]);
  // The blocks' indexes change as saves go through, and a comment's block with them.
  const was = useRef(saveState);
  const { refresh } = store;
  useEffect(() => {
    if (was.current === "saving" && saveState === "saved") void refresh();
    was.current = saveState;
  }, [saveState, refresh]);
  useEffect(() => {
    if (!editor) return;
    const marks = (editor.storage as unknown as Record<string, Marks>).docCommentMarks;
    marks.comments = open;
    marks.onOpen = (id) => {
      setFocus(id);
      setShow(true);
    };
    editor.view.dispatch(editor.state.tr.setMeta(REDRAW, true));
  }, [editor, open]);

  const blockText = useCallback((index: number | null) => (index === null ? "" : (loaded.current.get(index)?.text ?? "")), [loaded]);
  const hintFor = (c: DocComment) => c.quote || blockText(c.block).replace(/\s+/g, " ").slice(0, SNIPPET);

  const add = async (text: string, send: boolean) => {
    if (!editor) return;
    const { from, to, $from } = editor.state.selection;
    const start = $from.before(1);
    const end = start + $from.node(1).nodeSize;
    const quote = editor.state.doc.textBetween(from, Math.min(to, end - 1), "\n");
    // A block typed since the last save has no place in the file yet: save, then ask for its index.
    await flush();
    const index = (editor.state.doc.nodeAt(start)?.attrs.blockIndex as number | null | undefined) ?? null;
    if (index === null) return setProblem("Wait for the document to save, then comment again.");
    try {
      const made = await addDocComment(threadId, { path, block: index, text, quote, sent: send && !!onAsk });
      if (send && onAsk) onAsk(docCommentsMessage(path, [{ quote, blockText: blockText(index), text }]), { path, commentId: made.id, doc: true });
      setProblem(null);
      setFocus(made.id);
      setShow(true);
      await refresh();
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    }
  };

  const sendUnsent = (unsent: DocComment[]) => {
    if (!onAsk) return;
    onAsk(
      docCommentsMessage(
        path,
        unsent.map((c) => ({ quote: c.quote, blockText: blockText(c.block), text: c.text })),
      ),
      { path, commentId: unsent[0].id, doc: true, alsoCommentIds: unsent.slice(1).map((c) => c.id) },
    );
    void store.act(Promise.all(unsent.map((c) => markDocCommentSent(threadId, path, c.id))));
  };

  return { store, open, show, setShow, focus, problem, setProblem, hintFor, add, sendUnsent };
}
