import { EditorContent, type Editor } from "@tiptap/react";
import { useRef, type RefObject } from "react";
import { sheetStyle, type Page } from "../../lib/docsLook";
import { useSheetZoom } from "./useSheetZoom";

/** The scrolling area the editor sits in: the page the file is laid out on, scaled to fit, or a plain column for a file without one. */
export function DocsSheet({ editor, page, pageRef }: { editor: Editor | null; page: Page | undefined; pageRef: RefObject<HTMLDivElement | null> }) {
  const scroller = useRef<HTMLDivElement>(null);
  const zoom = useSheetZoom(scroller, page?.w);
  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-auto bg-[var(--bg)]" onClick={() => editor?.commands.focus()}>
      {page ? (
        <div className="px-4 py-6">
          <div ref={pageRef} className="docs-sheet mx-auto" style={{ ...sheetStyle(page), zoom }} onClick={(e) => e.stopPropagation()}>
            <EditorContent editor={editor} />
          </div>
        </div>
      ) : (
        <div ref={pageRef} className="mx-auto max-w-[760px] px-10 pb-24 pt-8" onClick={(e) => e.stopPropagation()}>
          <EditorContent editor={editor} />
        </div>
      )}
    </div>
  );
}
