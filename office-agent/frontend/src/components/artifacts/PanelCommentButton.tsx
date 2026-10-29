import { ChevronDownIcon, MessageCircleIcon } from "../icons";

/** The comment control in a panel's header: the button, and beside it the menu of what else can be
 * done with comments. Slides and Docs both draw it, so a panel's comments look the same. */
export function PanelCommentButton({
  pressed,
  title,
  dot = false,
  onToggle,
  onMenu,
}: {
  pressed: boolean;
  title: string;
  /** A mark on the icon while some comments are open. */
  dot?: boolean;
  onToggle: () => void;
  onMenu: (anchor: DOMRect) => void;
}) {
  const half = "flex h-7 items-center justify-center hover:bg-[var(--card-bg)]";
  return (
    <div className="flex items-center overflow-hidden rounded-lg border border-[var(--border)]" onPointerDown={(e) => e.stopPropagation()}>
      <button
        type="button"
        title={title}
        aria-label="Comment"
        aria-pressed={pressed}
        className={`${half} relative w-8 ${pressed ? "bg-[var(--accent-soft)] text-[var(--accent-ink)]" : "text-[var(--fg)]"}`}
        onClick={onToggle}
      >
        <MessageCircleIcon className="h-4 w-4" />
        {dot && <span aria-hidden className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[var(--accent)]" />}
      </button>
      <span className="h-4 border-l border-[var(--border)]" />
      <button
        type="button"
        title="Comment options"
        aria-label="Comment options"
        aria-haspopup="menu"
        className={`${half} w-6 text-[var(--muted)]`}
        onClick={(e) => onMenu(e.currentTarget.getBoundingClientRect())}
      >
        <ChevronDownIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
