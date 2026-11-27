import { EditorContent, useEditor } from "@tiptap/react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { DocChartPreview } from "../../lib/docChartPreview";
import { getDoc, NotADocError, type DocBlock } from "../../lib/docFile";
import { loadLook, type DocLook } from "../../lib/docLook";
import { docContent, editorExtensions } from "../../lib/docModel";
import { pictureUrl } from "../../lib/docPictures";
import { DocTableLook } from "../../lib/docTableLook";

export function DocReading({ threadId, path, blocks }: { threadId: string; path: string; blocks: DocBlock[] }) {
  const [look] = useState(loadLook);
  const content = useMemo(() => docContent(blocks), [blocks]);
  const extensions = useMemo(
    () => [...editorExtensions((src) => pictureUrl(threadId, path, src)), DocChartPreview, DocTableLook],
    [threadId, path],
  );
  const editor = useEditor({
    editable: false,
    extensions,
    content,
    editorProps: { attributes: { class: "doc-editor", "aria-label": "Document preview" } },
  }, [threadId, path]);
  useEffect(() => {
    if (editor && !editor.isDestroyed) editor.commands.setContent(content, { emitUpdate: false });
  }, [editor, content]);
  return <DocPage look={look}><EditorContent editor={editor} /></DocPage>;
}

export function DocPage({ look, hidden, children }: { look: DocLook; hidden?: boolean; children: ReactNode }) {
  return <div hidden={hidden} className={`doc-page mx-auto px-10 pb-24 pt-8 ${look.wide ? "max-w-[1100px]" : "max-w-[760px]"}`}
    data-headings={look.headings} data-text={look.text}>{children}</div>;
}

export function DocFileReading({ threadId, path, revision, markdown }: {
  threadId: string; path: string; revision: string; markdown: ReactNode;
}) {
  const [blocks, setBlocks] = useState<DocBlock[]>();
  const [error, setError] = useState("");
  const [plain, setPlain] = useState(false);
  useEffect(() => {
    let active = true;
    void getDoc(threadId, path).then(
      (doc) => { if (active) { setBlocks(doc.blocks); setPlain(false); setError(""); } },
      (error: unknown) => {
        if (!active) return;
        if (error instanceof NotADocError) setPlain(true);
        else setError("This document could not be previewed.");
      },
    );
    return () => { active = false; };
  }, [threadId, path, revision]);
  if (plain) return markdown;
  return <div className="h-full overflow-auto [overflow-anchor:none]">
    {error || !blocks ? <p className="p-4 text-sm text-[var(--muted)]">{error || "Loading document…"}</p>
      : <DocReading threadId={threadId} path={path} blocks={blocks} />}
  </div>;
}
