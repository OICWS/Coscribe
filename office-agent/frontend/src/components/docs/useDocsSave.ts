import type { Editor } from "@tiptap/core";
import { Mapping } from "@tiptap/pm/transform";
import { useCallback, useEffect, useRef, useState } from "react";
import { DocChangedError, docToBlocks, saveDocBlocks, type Block } from "../../lib/docsEditor";

export type SaveState = { kind: "saved" } | { kind: "unsaved" } | { kind: "saving" } | { kind: "conflict" } | { kind: "error"; message: string };

const IDLE_MS = 1200;
/** The meta on a transaction that only hands the file's new ids to the blocks: not an edit. */
const IDS_META = "docsIds";

/** The editor saves itself a moment after the person stops typing, and when the panel closes. A save
 * sends every block with the id the file gave it; the answer carries the ids of the blocks made since,
 * which are put on their nodes through whatever the person typed meanwhile. */
export function useDocsSave(editor: Editor | null, threadId: string, path: string, firstVersion: string, onLost: () => void) {
  const [state, setState] = useState<SaveState>({ kind: "saved" });
  const version = useRef(firstVersion);
  const timer = useRef<number | undefined>(undefined);
  const flight = useRef<Mapping | null>(null);
  const dirty = useRef(false);

  const save = useCallback(async () => {
    window.clearTimeout(timer.current);
    if (!editor || editor.isDestroyed || flight.current || !dirty.current) return;
    const sent = docToBlocks(editor.state.doc);
    const mapping = new Mapping();
    flight.current = mapping;
    dirty.current = false;
    setState({ kind: "saving" });
    try {
      const saved = await saveDocBlocks(threadId, path, version.current, sent.blocks);
      version.current = saved.version;
      if (saved.blocks.length !== sent.blocks.length) return onLost();
      giveIds(editor, sent.slots, saved.blocks, mapping);
      setState(dirty.current ? { kind: "unsaved" } : { kind: "saved" });
    } catch (error) {
      dirty.current = true;
      setState(error instanceof DocChangedError ? { kind: "conflict" } : { kind: "error", message: error instanceof Error ? error.message : String(error) });
      if (error instanceof DocChangedError) editor.setEditable(false);
    } finally {
      flight.current = null;
      if (dirty.current && !timer.current) timer.current = window.setTimeout(() => void save(), IDLE_MS);
    }
  }, [editor, threadId, path, onLost]);

  useEffect(() => {
    if (!editor) return;
    const onTransaction = ({ transaction }: { transaction: { docChanged: boolean; getMeta: (key: string) => unknown; mapping: Mapping } }) => {
      if (!transaction.docChanged || transaction.getMeta(IDS_META)) return;
      flight.current?.appendMapping(transaction.mapping);
      dirty.current = true;
      setState((now) => (now.kind === "saving" || now.kind === "conflict" ? now : { kind: "unsaved" }));
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        timer.current = undefined;
        void save();
      }, IDLE_MS);
    };
    editor.on("transaction", onTransaction);
    return () => {
      editor.off("transaction", onTransaction);
      window.clearTimeout(timer.current);
      timer.current = undefined;
      void save();
    };
  }, [editor, save]);

  return { state, saveNow: save };
}

function giveIds(editor: Editor, slots: ReturnType<typeof docToBlocks>["slots"], blocks: Block[], mapping: Mapping) {
  const tr = editor.state.tr;
  slots.forEach((slot, index) => {
    const id = blocks[index]?.id;
    if (slot.pos < 0 || !id) return;
    const moved = mapping.mapResult(slot.pos);
    const node = moved.deleted ? null : tr.doc.nodeAt(moved.pos);
    if (node && node.type.name === slot.type && node.attrs.blockId !== id) tr.setNodeMarkup(moved.pos, undefined, { ...node.attrs, blockId: id });
  });
  if (!tr.docChanged) return;
  tr.setMeta(IDS_META, true).setMeta("addToHistory", false).setMeta("preventUpdate", true);
  editor.view.dispatch(tr);
}
