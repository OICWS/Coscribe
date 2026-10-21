import { Extension, type Editor } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";

const TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
const MAX_BYTES = 8 * 1024 * 1024;

/** Fired on the editor's element when a picture cannot be added; the panel shows `detail`. */
export const PROBLEM_EVENT = "docs-problem";

const problem = (editor: Editor, message: string) => editor.view.dom.dispatchEvent(new CustomEvent(PROBLEM_EVENT, { detail: message, bubbles: true }));

const readAsUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

/** A picture goes in as a block that carries its own data until the next save writes it into the file;
 * the save then gives it an id and the data is dropped (useDocsSave). */
async function addPictureFile(editor: Editor, file: File) {
  if (editor.isActive("table")) return problem(editor, "A picture cannot go inside a table");
  if (!TYPES.includes(file.type)) return problem(editor, "Only PNG, JPEG, GIF and WebP pictures can be added");
  if (file.size > MAX_BYTES) return problem(editor, "A picture can be at most 8 MB");
  let url: string;
  try {
    url = await readAsUrl(file);
  } catch {
    return problem(editor, "That picture could not be read");
  }
  editor.chain().focus().insertContent({ type: "lockedBlock", attrs: { what: "image or drawing", text: "", images: [url], upload: url } }).run();
}

/** Asks for a picture file in the system's own picker and adds it. */
export function choosePicture(editor: Editor) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = TYPES.join(",");
  input.onchange = () => {
    const file = input.files?.[0];
    if (file) void addPictureFile(editor, file);
  };
  input.click();
}

/** A picture pasted or dropped on its own (a screenshot, a file) is added; pasted text and Word's own
 * pastes, which carry an image beside their text, are left to the editor. */
export const Pictures = Extension.create({
  name: "pictures",
  addProseMirrorPlugins() {
    const editor = this.editor;
    const take = (transfer: DataTransfer | null, onlyFiles: boolean) => {
      const file = [...(transfer?.files ?? [])].find((f) => f.type.startsWith("image/"));
      if (!file || (onlyFiles && (transfer?.getData("text/plain") || transfer?.getData("text/html")))) return false;
      void addPictureFile(editor, file);
      return true;
    };
    return [new Plugin({ props: { handlePaste: (_view, event) => take(event.clipboardData, true), handleDrop: (_view, event) => take(event.dataTransfer, false) } })];
  },
});
