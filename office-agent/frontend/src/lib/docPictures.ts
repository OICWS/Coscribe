import { Extension } from "@tiptap/core";
import { Image, type ImageOptions } from "@tiptap/extension-image";
import { Plugin } from "@tiptap/pm/state";

const TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
const MAX_BYTES = 8 * 1024 * 1024;

const base = (threadId: string) => `/api/threads/${encodeURIComponent(threadId)}/doc/asset`;

/** A picture the Doc keeps (`name.doc/assets/x.png`) as the address the editor shows it from; a picture
 * named by a web address or inline data is shown from there. The file keeps the short path. */
export function pictureUrl(threadId: string, path: string, src: string): string {
  return /^(https?:|data:image\/)/i.test(src) ? src : `${base(threadId)}?path=${encodeURIComponent(path)}&src=${encodeURIComponent(src)}`;
}

/** Why a file cannot be added as a picture, or null. */
export function pictureProblem(file: File): string | null {
  if (!TYPES.includes(file.type)) return "Only PNG, JPEG, GIF and WebP pictures can be added";
  return file.size > MAX_BYTES ? "A picture can be at most 8 MB" : null;
}

/** Keeps a picture in the Doc's folder; the answer is the path the markdown names it by. */
export async function uploadPicture(threadId: string, path: string, file: File): Promise<{ src: string }> {
  const form = new FormData();
  form.append("path", path);
  form.append("file", file);
  const response = await fetch(base(threadId), { method: "POST", body: form });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as { src: string };
}

/** The picture node shown from `resolve(src)`, while the document keeps `src` as it is written. */
export const DocImage = Image.extend<ImageOptions & { resolve: (src: string) => string }>({
  addOptions() {
    return { ...(this.parent?.() as ImageOptions), resolve: (src: string) => src };
  },
  renderHTML({ HTMLAttributes }) {
    const src = typeof HTMLAttributes.src === "string" ? this.options.resolve(HTMLAttributes.src) : "";
    return ["img", { ...HTMLAttributes, src }];
  },
});

/** Asks for a picture in the system's own picker. */
export function choosePicture(onFile: (file: File) => void) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = TYPES.join(",");
  input.onchange = () => {
    const file = input.files?.[0];
    if (file) onFile(file);
  };
  input.click();
}

/** A picture pasted or dropped on its own (a screenshot, a file) goes to `onFile`; pasted text, and
 * pastes that carry text beside the picture, are left to the editor. */
export const DocPictureDrop = Extension.create<{ onFile: (file: File) => void }>({
  name: "docPictureDrop",
  addOptions: () => ({ onFile: () => undefined }),
  addProseMirrorPlugins() {
    const take = (transfer: DataTransfer | null, onlyFiles: boolean) => {
      const file = [...(transfer?.files ?? [])].find((f) => f.type.startsWith("image/"));
      if (!file || (onlyFiles && (transfer?.getData("text/plain") || transfer?.getData("text/html")))) return false;
      this.options.onFile(file);
      return true;
    };
    return [new Plugin({ props: { handlePaste: (_view, event) => take(event.clipboardData, true), handleDrop: (_view, event) => take(event.dataTransfer, false) } })];
  },
});
