import { useState } from "react";
import { transitionLabel, type SlideInfo } from "../../lib/slides";
import { setBackground, setTransition, sourceColours } from "../../lib/slideSource";
import type { DesignSystem } from "../../lib/slideText";
import { ChevronDownIcon, CloseIcon } from "../icons";
import { Row, field } from "./PropertyRows";
import { ColourPicker } from "./SlideFormatBar";
import { SlideMenu } from "./SlideMenu";
import { TextProperties, type EditorSelection } from "./SlideTextProperties";

/** The transitions a section can name, by PowerPoint's name for each (as the deck reports it). */
const TRANSITIONS: [string | null, string | null][] = [
  [null, null],
  ["fade", "fade"],
  ["push", "push"],
  ["magic", "morph"],
];

/** A change to the slide's section, saved by the panel. */
export type SlideEdit = (edit: (doc: Document) => void) => void;

/** The selected text's properties, or else the current slide's transition and background. */
export function SlideProperties({
  slide,
  beside,
  selection,
  design,
  onEdit,
  loadSource,
  onClose,
}: {
  slide: SlideInfo;
  beside: boolean;
  /** The text element selected in the editor, if one is. */
  selection: EditorSelection | null;
  design: DesignSystem | null;
  onEdit: SlideEdit;
  /** The slide's section source, for its colours. */
  loadSource: () => Promise<string>;
  onClose: () => void;
}) {
  return (
    <aside
      aria-label="Slide properties"
      className={`shrink-0 overflow-auto bg-[var(--bg)] ${beside ? "w-[280px] border-l" : "max-h-[45%] border-t"} border-[var(--border)]`}
    >
      <div className="flex h-10 items-center justify-end px-2">
        <button
          type="button"
          title="Hide the properties panel"
          aria-label="Hide the properties panel"
          className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
          onClick={onClose}
        >
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
      {selection ? <TextProperties selection={selection} design={design} /> : <SlideSettings slide={slide} onEdit={onEdit} loadSource={loadSource} />}
    </aside>
  );
}

/** The current slide's transition and background; the slide's own colours come first in the
 * background picker. */
function SlideSettings({ slide, onEdit, loadSource }: { slide: SlideInfo; onEdit: SlideEdit; loadSource: () => Promise<string> }) {
  const background = slide.background?.toUpperCase() ?? null;
  const [open, setOpen] = useState<{ kind: "transition" | "background"; anchor: DOMRect; colours?: string[] } | null>(null);
  return (
    <>
      <section className="border-b border-[var(--border)] px-3 pb-3">
        <h3 className="pb-2.5 text-[15px] font-semibold text-[var(--fg)]">Slide</h3>
        <Row label="Transition">
          <button
            type="button"
            aria-label="Transition"
            aria-haspopup="menu"
            className={field}
            onClick={(e) => setOpen({ kind: "transition", anchor: e.currentTarget.getBoundingClientRect() })}
          >
            <span className="flex-1 truncate text-left">{transitionLabel(slide.transition)}</span>
            <ChevronDownIcon className="h-4 w-4 text-[var(--muted)]" />
          </button>
        </Row>
      </section>
      <section className="px-3 py-3">
        <h3 className="pb-2.5 text-[15px] font-semibold text-[var(--fg)]">Appearance</h3>
        <Row label="Background">
          <button
            type="button"
            aria-label="Background"
            className={field}
            onClick={(e) => {
              const anchor = e.currentTarget.getBoundingClientRect();
              void loadSource().then((source) => setOpen({ kind: "background", anchor, colours: sourceColours(source) }));
            }}
          >
            <span className="h-[18px] w-[18px] shrink-0 rounded border border-[var(--border)]" style={{ background: background ?? "transparent" }} />
            <span className="flex-1 truncate text-left font-mono text-[13px]">{background ?? "Drawn on the slide"}</span>
          </button>
        </Row>
      </section>
      {open?.kind === "transition" && (
        <SlideMenu
          anchor={open.anchor}
          label="Transition"
          width={200}
          entries={TRANSITIONS.map(([name, reported]) => ({
            label: transitionLabel(reported),
            checked: (slide.transition ?? null) === reported,
            onSelect: () => onEdit((doc) => setTransition(doc, name)),
          }))}
          onClose={() => setOpen(null)}
        />
      )}
      {open?.kind === "background" && (
        <ColourPicker
          anchor={open.anchor}
          current={background ?? "#FFFFFF"}
          colours={open.colours ?? []}
          onPick={(colour) => {
            onEdit((doc) => setBackground(doc, colour));
            setOpen(null);
          }}
          onClose={() => setOpen(null)}
        />
      )}
    </>
  );
}
