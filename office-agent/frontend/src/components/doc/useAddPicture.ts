import type { Editor } from "@tiptap/core";
import { useEffect, type RefObject } from "react";
import { pictureProblem, uploadPicture } from "../../lib/docPictures";

/** Gives `add` (which the editor's paste and drop handlers were built with) its job once the editor exists:
 * a picture is checked, kept in the Doc's folder and put in a paragraph of its own at the caret. */
export function useAddPicture(add: RefObject<(file: File) => void>, editor: Editor | null, threadId: string, path: string, onProblem: (message: string | null) => void) {
  useEffect(() => {
    add.current = (file) => {
      const refused = pictureProblem(file);
      if (refused || !editor) return onProblem(refused);
      uploadPicture(threadId, path, file).then(
        ({ src }) =>
          editor
            .chain()
            .focus()
            .insertContent({ type: "paragraph", content: [{ type: "image", attrs: { src, alt: file.name.replace(/\.[^.]+$/, "") } }] })
            .run(),
        (e: unknown) => onProblem(e instanceof Error ? e.message : String(e)),
      );
    };
  });
}
