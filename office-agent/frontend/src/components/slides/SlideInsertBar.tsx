import { useRef, useState } from "react";
import type { Insert } from "../../lib/slideSource";
import { uploadSlidePicture } from "../../lib/slideEditing";
import { ChevronDownIcon, TextToolIcon } from "../icons";
import { SlideMenu } from "./SlideMenu";
import { PictureIcon, ShapesIcon, TableIcon } from "./formatIcons";

const button = "flex h-8 w-8 items-center justify-center rounded-lg text-[var(--fg)] hover:bg-[var(--card-bg)] disabled:opacity-40";
const SHAPES: [string, Extract<Insert, { kind: "shape" }>["shape"]][] = [
  ["Rectangle", "rect"],
  ["Rounded rectangle", "round-rect"],
  ["Ellipse", "ellipse"],
  ["Triangle", "triangle"],
  ["Arrow", "arrow"],
  ["Line", "line"],
];

/** The card at the stage's top left: a text box, a picture, a table or a shape, added to the
 * middle of the slide and selected. */
export function SlideInsertBar({
  threadId,
  path,
  disabled,
  onInsert,
  onProblem,
}: {
  threadId: string;
  path: string;
  disabled: boolean;
  onInsert: (insert: Insert) => void;
  onProblem: (message: string | null) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [shapes, setShapes] = useState<DOMRect | null>(null);
  const pick = (file: File | undefined) => {
    if (!file) return;
    uploadSlidePicture(threadId, path, file).then(
      (picture) => onInsert({ kind: "picture", ...picture }),
      (e: unknown) => onProblem(e instanceof Error ? e.message : String(e)),
    );
  };
  return (
    <div className="absolute left-4 top-4 z-10 flex h-11 items-center gap-1 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-1.5 shadow-[var(--panel-shadow)]">
      <button type="button" title="Add a text box" aria-label="Add a text box" disabled={disabled} className={button} onClick={() => onInsert({ kind: "text" })}>
        <TextToolIcon className="h-[17px] w-[17px]" />
      </button>
      <button type="button" title="Insert a picture" aria-label="Insert a picture" disabled={disabled} className={button} onClick={() => fileRef.current?.click()}>
        <PictureIcon className="h-[17px] w-[17px]" />
      </button>
      <button type="button" title="Insert a table" aria-label="Insert a table" disabled={disabled} className={button} onClick={() => onInsert({ kind: "table" })}>
        <TableIcon className="h-[17px] w-[17px]" />
      </button>
      <button
        type="button"
        title="Insert a shape"
        aria-label="Insert a shape"
        aria-haspopup="menu"
        disabled={disabled}
        className="flex h-8 items-center gap-0.5 rounded-lg px-1.5 text-[var(--fg)] hover:bg-[var(--card-bg)] disabled:opacity-40"
        onClick={(e) => setShapes(e.currentTarget.getBoundingClientRect())}
      >
        <ShapesIcon className="h-[17px] w-[17px]" />
        <ChevronDownIcon className="h-3 w-3 text-[var(--muted)]" />
      </button>
      <input
        ref={fileRef}
        type="file"
        hidden
        accept="image/png,image/jpeg,image/gif,image/webp"
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {shapes && (
        <SlideMenu
          anchor={shapes}
          label="Shapes"
          width={200}
          align="left"
          entries={SHAPES.map(([label, shape]) => ({ label, onSelect: () => onInsert({ kind: "shape", shape }) }))}
          onClose={() => setShapes(null)}
        />
      )}
    </div>
  );
}
