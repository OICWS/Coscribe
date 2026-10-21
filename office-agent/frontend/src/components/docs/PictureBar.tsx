import type { Editor } from "@tiptap/core";
import { NodeSelection } from "@tiptap/pm/state";
import { useEditorState } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";
import type { PictureSetting } from "../../lib/docsEditor";

const SIZES = [25, 50, 75, 100];

const chosen = (editor: Editor): { setting: PictureSetting; pos: number } | null => {
  const selection = editor.state.selection;
  if (!(selection instanceof NodeSelection) || selection.node.type.name !== "lockedBlock") return null;
  const setting = selection.node.attrs.picture as PictureSetting | null;
  return setting ? { setting, pos: selection.from } : null;
};

/** The bar over a selected picture: its width (a share of the text width) and its description for
 * people who cannot see it. Only a paragraph with one picture is offered it. */
export function PictureBar({ editor }: { editor: Editor }) {
  const now = useEditorState({ editor, selector: ({ editor: e }) => chosen(e) });
  const change = (next: Partial<PictureSetting>) => {
    if (now) editor.chain().focus().updateAttributes("lockedBlock", { picture: { ...now.setting, ...next } }).run();
  };
  return (
    <BubbleMenu editor={editor} options={{ placement: "top" }} shouldShow={({ editor: e }) => e.isEditable && chosen(e) !== null}>
      <div role="toolbar" aria-label="Picture" className="flex items-center gap-1 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-1 shadow-[0_8px_28px_rgba(0,0,0,0.12)]">
        {SIZES.map((size) => (
          <button
            key={size}
            type="button"
            title={`${size}% of the text width`}
            aria-pressed={now?.setting.width === size}
            className={`h-8 rounded-md px-2 text-sm hover:bg-[var(--card-bg)] ${now?.setting.width === size ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => change({ width: size })}
          >
            {size}%
          </button>
        ))}
        <span className="mx-0.5 h-5 border-l border-[var(--border)]" />
        <input
          key={now?.pos}
          aria-label="Description"
          placeholder="Describe the picture"
          defaultValue={now?.setting.alt ?? ""}
          maxLength={500}
          className="h-8 w-48 rounded-md border border-[var(--border)] bg-transparent px-2 text-sm outline-none focus:border-[var(--accent)]"
          onBlur={(e) => e.target.value !== now?.setting.alt && change({ alt: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
          }}
        />
      </div>
    </BubbleMenu>
  );
}
