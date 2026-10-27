import type { Editor } from "@tiptap/core";
import { Mapping } from "@tiptap/pm/transform";
import { useCallback, useEffect, useRef, useState } from "react";
import { DocChangedError, saveDoc, type DocRead } from "../../lib/docFile";
import { docEdits, type Loaded } from "../../lib/docModel";

export type SaveState = { kind: "saved" } | { kind: "unsaved" } | { kind: "saving" } | { kind: "conflict" } | { kind: "error"; message: string };

const IDLE_MS = 1200;
/** The meta on a transaction that only gives the file's new indexes to the blocks: not an edit. */
const INDEXES_META = "docIndexes";

/** The editor saves itself a moment after the person stops typing, and as the panel closes. A save
 * names only the blocks that changed; the answer carries the indexes the blocks now have, which are put on
 * their nodes through whatever the person typed meanwhile. A save over a file that changed meanwhile
 * (coscribe's turn) is not forced: the person is offered the file as it is. */
export function useDocSave(editor: Editor | null, threadId: string, path: string, version: { current: string }, initial: Map<number, Loaded>, onLost: () => void) {
  const [state, setState] = useState<SaveState>({ kind: "saved" });
  const timer = useRef<number | undefined>(undefined);
  const flight = useRef<Mapping | null>(null);
  const dirty = useRef(false);
  const loaded = useRef(initial);
  // A refused save stops this editor's saving for good: its retry, after a Reload has taken the
  // file's new version, would be accepted and write the old text over the file.
  const stopped = useRef(false);

  const save = useCallback(async () => {
    window.clearTimeout(timer.current);
    timer.current = undefined;
    if (!editor || editor.isDestroyed || flight.current || !dirty.current || stopped.current) return;
    const { edits, slots } = docEdits(editor.state.doc, loaded.current);
    dirty.current = false;
    if (!edits.length) return setState({ kind: "saved" });
    const mapping = new Mapping();
    flight.current = mapping;
    setState({ kind: "saving" });
    try {
      const saved = await saveDoc(threadId, path, version.current, edits);
      version.current = saved.version;
      if (saved.blocks.length !== slots.length) return onLost();
      giveIndexes(editor, slots, saved, mapping);
      loaded.current = new Map(saved.blocks.map((block, i) => [block.index, { text: block.text, key: slots[i].key }]));
      setState(dirty.current ? { kind: "unsaved" } : { kind: "saved" });
    } catch (error) {
      dirty.current = true;
      if (error instanceof DocChangedError) {
        stopped.current = true;
        editor.setEditable(false);
        setState({ kind: "conflict" });
      } else setState({ kind: "error", message: error instanceof Error ? error.message : String(error) });
    } finally {
      flight.current = null;
      if (dirty.current && !stopped.current && timer.current === undefined) timer.current = window.setTimeout(() => void save(), IDLE_MS);
    }
  }, [editor, threadId, path, version, onLost]);

  useEffect(() => {
    if (!editor) return;
    const onTransaction = ({ transaction }: { transaction: { docChanged: boolean; getMeta: (key: string) => unknown; mapping: Mapping } }) => {
      if (!transaction.docChanged) return;
      flight.current?.appendMapping(transaction.mapping);
      if (transaction.getMeta(INDEXES_META)) return;
      dirty.current = true;
      setState((now) => (now.kind === "conflict" || now.kind === "error" ? now : { kind: "unsaved" }));
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => void save(), IDLE_MS);
    };
    editor.on("transaction", onTransaction);
    return () => {
      editor.off("transaction", onTransaction);
      window.clearTimeout(timer.current);
      // The panel closing is a save, not a loss.
      void save();
    };
  }, [editor, save]);

  return { state, loaded, flush: save };
}

function giveIndexes(editor: Editor, slots: { pos: number; key: string }[], saved: DocRead, mapping: Mapping) {
  const tr = editor.state.tr.setMeta(INDEXES_META, true).setMeta("addToHistory", false);
  slots.forEach((slot, i) => {
    const pos = mapping.map(slot.pos, 1);
    const node = tr.doc.nodeAt(pos);
    if (node && node.attrs.blockIndex !== saved.blocks[i].index) tr.setNodeMarkup(pos, undefined, { ...node.attrs, blockIndex: saved.blocks[i].index });
  });
  if (tr.docChanged) editor.view.dispatch(tr);
}
