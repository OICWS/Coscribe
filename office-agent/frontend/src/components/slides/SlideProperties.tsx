import { useState } from "react";
import { transitionLabel, type SlideInfo } from "../../lib/slides";
import { setBackground, setTransition, sourceColours } from "../../lib/slideSource";
import { ChevronDownIcon, CloseIcon } from "../icons";
import { ColourPicker } from "./SlideFormatBar";
import { SlideMenu } from "./SlideMenu";

const field =
  "flex h-8 min-w-0 flex-1 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-2.5 text-sm text-[var(--fg)] hover:border-[var(--muted)]";

/** The transitions a section can name, by PowerPoint's name for each (as the deck reports it). */
const TRANSITIONS: [string | null, string | null][] = [
  [null, null],
  ["fade", "fade"],
  ["push", "push"],
  ["magic", "morph"],
];

/** A change to the slide's section, saved by the panel. */
export type SlideEdit = (edit: (doc: Document) => void) => void;

/** The current slide's transition and background, changed here; the slide's own colours come
 * first in the background picker. */
export function SlideProperties({
  slide,
  beside,
  onEdit,
  loadSource,
  onClose,
}: {
  slide: SlideInfo;
  beside: boolean;
  onEdit: SlideEdit;
  /** The slide's section source, for its colours. */
  loadSource: () => Promise<string>;
  onClose: () => void;
}) {
  const background = slide.background?.toUpperCase() ?? null;
  const [open, setOpen] = useState<{ kind: "transition" | "background"; anchor: DOMRect; colours?: string[] } | null>(null);
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
    </aside>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-[84px] shrink-0 text-sm text-[var(--muted)]">{label}</span>
      {children}
    </div>
  );
}
