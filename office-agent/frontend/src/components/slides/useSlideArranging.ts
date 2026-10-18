import { useState } from "react";
import { arrangeSlides, type Arrange } from "../../lib/slideEditing";
import { slideLayouts, type SlideLayout } from "../../lib/slideLayouts";
import { accentOf, parseSection, styleOf } from "../../lib/slideSource";
import type { MenuEntry } from "./SlideMenu";

/** New, copied, moved and deleted slides: the New slide dialog (its layouts in the look of the
 * slide it follows), the thumbnails' menu, and the change itself, after which the deck is read
 * again and the slide it names is shown. */
export function useSlideArranging({
  threadId,
  path,
  loadSource,
  onDone,
  onProblem,
}: {
  threadId: string;
  path: string;
  loadSource: (index: number) => Promise<string>;
  onDone: (index: number) => void;
  onProblem: (message: string | null) => void;
}) {
  const [dialog, setDialog] = useState<{ after: number; layouts: SlideLayout[] } | null>(null);
  const [menu, setMenu] = useState<{ index: number; anchor: DOMRect } | null>(null);
  const fail = (e: unknown) => onProblem(e instanceof Error ? e.message : String(e));

  const act = (change: Arrange) =>
    void arrangeSlides(threadId, path, change).then(({ index }) => {
      onProblem(null);
      onDone(index);
    }, fail);
  const openNew = (after: number) =>
    void loadSource(Math.max(after, 0)).then((source) => setDialog({ after, layouts: slideLayouts(lookOf(source)) }), fail);

  const menuEntries = (index: number, count: number): MenuEntry[] => [
    { label: "New slide after this", onSelect: () => openNew(index) },
    { label: "Duplicate", onSelect: () => act({ action: "duplicate", index }) },
    { label: "Delete", disabled: count <= 1, onSelect: () => act({ action: "delete", index }) },
  ];
  return {
    dialog,
    closeDialog: () => setDialog(null),
    pick: (layout: SlideLayout) => {
      if (dialog) act({ action: "insert", index: dialog.after, source: layout.source });
      setDialog(null);
    },
    openNew,
    menu,
    setMenu,
    menuEntries,
    move: (index: number, to: number) => index !== to && act({ action: "move", index, to }),
  };
}

/** The look a new slide takes from the slide it follows. */
function lookOf(source: string) {
  const doc = parseSection(source);
  const section = doc.documentElement;
  const text = styleOf(section, "color") ?? "#1F2937";
  return {
    background: styleOf(section, "background") ?? "#FFFFFF",
    text,
    muted: text,
    accent: accentOf(doc),
    font: styleOf(section, "font-family") ?? "Microsoft YaHei, Arial",
  };
}
