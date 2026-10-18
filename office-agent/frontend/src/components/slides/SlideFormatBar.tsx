import { useState, type ReactNode } from "react";
import { PRESETS, type Preset } from "../../lib/slideSource";
import { CheckIcon, ChevronDownIcon, CloseIcon, LinkIcon, MoreIcon } from "../icons";
import { SlideMenu } from "./SlideMenu";
import { AlignIcon, BoldIcon, CommentPlusIcon, ItalicIcon, ListIcon, UnderlineIcon } from "./formatIcons";

export type Align = "left" | "center" | "right";

/** What the bar shows for the selected text. */
export interface TextFormat {
  preset: Preset;
  colour: string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  list: boolean;
  align: Align;
}

interface FormatActions {
  preset: (preset: Preset) => void;
  colour: (colour: string) => void;
  toggle: (what: "bold" | "italic" | "underline" | "list") => void;
  align: (align: Align) => void;
  comment: () => void;
  more: (anchor: DOMRect) => void;
}

const NEXT_ALIGN: Record<Align, Align> = { left: "center", center: "right", right: "left" };

/** The floating bar over the selected element (design §3): for text its style, colour, bold,
 * italic, underline, list and alignment; for anything, a comment and the More menu. Pressing
 * one keeps the text's own selection, so a change applies to the words selected. */
export function SlideFormatBar({
  x,
  y,
  text,
  colours,
  actions,
}: {
  /** The bar's bottom-left corner, in the editor's px. */
  x: number;
  y: number;
  /** Null when the element is not text. */
  text: TextFormat | null;
  colours: string[];
  actions: FormatActions;
}) {
  const [open, setOpen] = useState<{ kind: "preset" | "colour"; anchor: DOMRect } | null>(null);
  return (
    <div
      data-format-bar
      className="absolute z-20 flex h-10 -translate-y-full items-center gap-0.5 whitespace-nowrap rounded-xl border border-[var(--border)] bg-[var(--bg)] px-1.5 shadow-[0_4px_16px_rgba(0,0,0,0.12)]"
      style={{ left: Math.max(4, x), top: y - 8 }}
      onPointerDown={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.preventDefault()}
    >
      {text && (
        <>
          <button
            type="button"
            aria-label="Text style"
            className="flex h-8 w-[120px] items-center gap-2 rounded-lg border border-[var(--border)] px-2 text-[15px] hover:bg-[var(--card-bg)]"
            onClick={(e) => setOpen({ kind: "preset", anchor: e.currentTarget.getBoundingClientRect() })}
          >
            <span className="text-xs text-[var(--muted)]">Aa</span>
            <span className="flex-1 text-left">{text.preset}</span>
            <ChevronDownIcon className="h-3.5 w-3.5 text-[var(--muted)]" />
          </button>
          <button
            type="button"
            aria-label="Text colour"
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--card-bg)]"
            onClick={(e) => setOpen({ kind: "colour", anchor: e.currentTarget.getBoundingClientRect() })}
          >
            <span className="h-[18px] w-[18px] rounded border border-black/15" style={{ background: text.colour }} />
          </button>
          <Divider />
          <Toggle label="Bold" on={text.bold} onClick={() => actions.toggle("bold")}>
            <BoldIcon className="h-4 w-4" />
          </Toggle>
          <Toggle label="Italic" on={text.italic} onClick={() => actions.toggle("italic")}>
            <ItalicIcon className="h-4 w-4" />
          </Toggle>
          <Toggle label="Underline" on={text.underline} onClick={() => actions.toggle("underline")}>
            <UnderlineIcon className="h-4 w-4" />
          </Toggle>
          <Toggle label="Links are not part of slides yet" on={false} disabled onClick={() => undefined}>
            <LinkIcon className="h-4 w-4" />
          </Toggle>
          <Divider />
          <Toggle label="Bulleted list" on={text.list} disabled={text.preset === "Title" || text.preset === "Heading"} onClick={() => actions.toggle("list")}>
            <ListIcon className="h-4 w-4" />
          </Toggle>
          <Toggle label={`Align ${NEXT_ALIGN[text.align]}`} on={false} onClick={() => actions.align(NEXT_ALIGN[text.align])}>
            <AlignIcon align={text.align} className="h-4 w-4" />
          </Toggle>
          <Divider />
        </>
      )}
      <Toggle label="Comment" on={false} onClick={actions.comment}>
        <CommentPlusIcon className="h-4 w-4" />
      </Toggle>
      <Toggle label="More" on={false} onClick={(e) => actions.more(e.currentTarget.getBoundingClientRect())}>
        <MoreIcon className="h-4 w-4" />
      </Toggle>
      {open && text && <BarPopup open={open} text={text} colours={colours} actions={actions} onClose={() => setOpen(null)} />}
    </div>
  );
}

/** The text style menu or the colour picker, under the button that opened it. */
function BarPopup({
  open,
  text,
  colours,
  actions,
  onClose,
}: {
  open: { kind: "preset" | "colour"; anchor: DOMRect };
  text: TextFormat;
  colours: string[];
  actions: FormatActions;
  onClose: () => void;
}) {
  if (open.kind === "colour") {
    return (
      <ColourPicker
        anchor={open.anchor}
        current={text.colour}
        colours={colours}
        onPick={(colour) => {
          actions.colour(colour);
          onClose();
        }}
        onClose={onClose}
      />
    );
  }
  return (
    <SlideMenu
      anchor={open.anchor}
      label="Text style"
      width={160}
      entries={(Object.keys(PRESETS) as Preset[]).map((preset) => ({
        label: preset,
        checked: preset === text.preset,
        onSelect: () => actions.preset(preset),
      }))}
      onClose={onClose}
    />
  );
}

const Divider = () => <span className="mx-1 h-5 border-l border-[var(--border)]" />;

function Toggle({
  label,
  on,
  disabled,
  onClick,
  children,
}: {
  label: string;
  on: boolean;
  disabled?: boolean;
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={on}
      disabled={disabled}
      className={`flex h-8 w-8 items-center justify-center rounded-lg disabled:opacity-35 ${on ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "hover:bg-[var(--card-bg)]"}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

/** The slide's own colours first (Theme), or any as hex (Custom). */
function ColourPicker({
  anchor,
  current,
  colours,
  onPick,
  onClose,
}: {
  anchor: DOMRect;
  current: string;
  colours: string[];
  onPick: (colour: string) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"theme" | "custom">("theme");
  const [typed, setTyped] = useState(current);
  const valid = /^#[0-9a-fA-F]{6}$/.test(typed);
  const tabClass = (on: boolean) => `rounded-md px-2.5 py-1 text-[15px] ${on ? "bg-[var(--card-bg)] font-medium" : "text-[var(--muted)]"}`;
  return (
    <div
      role="dialog"
      aria-label="Colour"
      className="fixed z-50 w-[300px] rounded-xl border border-[var(--border)] bg-[var(--bg)] p-2 shadow-[0_8px_28px_rgba(0,0,0,0.16)]"
      style={{ left: Math.min(anchor.left, window.innerWidth - 308), top: anchor.bottom + 6 }}
    >
      <div className="mb-1 flex items-center gap-1">
        <button type="button" className={tabClass(tab === "theme")} onClick={() => setTab("theme")}>
          Theme
        </button>
        <button type="button" className={tabClass(tab === "custom")} onClick={() => setTab("custom")}>
          Custom
        </button>
        <span className="flex-1" />
        <button type="button" aria-label="Close" className="rounded p-1 text-[var(--muted)] hover:bg-[var(--card-bg)]" onClick={onClose}>
          <CloseIcon className="h-4 w-4" />
        </button>
      </div>
      {tab === "theme" ? (
        <div className="max-h-[260px] overflow-auto">
          {colours.map((colour) => (
            <button
              key={colour}
              type="button"
              className={`flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-[15px] hover:bg-[var(--card-bg)] ${colour === current ? "bg-[var(--card-bg)]" : ""}`}
              onClick={() => onPick(colour)}
            >
              <span className="h-5 w-5 rounded border border-black/15" style={{ background: colour }} />
              <span className="flex-1">{colour}</span>
              {colour === current && <CheckIcon className="h-4 w-4 text-[var(--accent)]" />}
            </button>
          ))}
        </div>
      ) : (
        <form
          className="flex items-center gap-2 p-1"
          onSubmit={(e) => {
            e.preventDefault();
            if (valid) onPick(typed.toUpperCase());
          }}
        >
          <input type="color" aria-label="Pick a colour" value={valid ? typed : "#000000"} onChange={(e) => setTyped(e.target.value.toUpperCase())} />
          <input
            aria-label="Hex colour"
            className="h-8 flex-1 rounded-lg border border-[var(--border)] bg-transparent px-2 text-[15px]"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
          <button type="submit" disabled={!valid} className="h-8 rounded-lg bg-[var(--accent)] px-3 text-sm text-white disabled:opacity-40">
            Apply
          </button>
        </form>
      )}
    </div>
  );
}
