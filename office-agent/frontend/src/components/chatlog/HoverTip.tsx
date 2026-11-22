import type { ReactNode } from "react";

/** A dark label above a control while the pointer is on it, with an optional line under it. It
 * sits on a wrapper rather than the button, so a disabled button still says why it is disabled. */
export function HoverTip({
  label,
  detail,
  align = "center",
  below = false,
  children,
}: {
  label: string;
  detail?: string;
  align?: "start" | "center" | "end";
  /** Under the control, for a control near the top of a scrolling list, which clips above it. */
  below?: boolean;
  children: ReactNode;
}) {
  return (
    <span className="group/tip relative inline-flex">
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute z-20 rounded-md bg-[var(--primary)] px-2 py-1 text-xs text-[var(--primary-fg)] opacity-0 shadow-md transition-opacity delay-150 group-hover/tip:opacity-100 ${
          detail || label.length > 40 ? "w-60" : "whitespace-nowrap"
        } ${below ? "top-full mt-1.5" : "bottom-full mb-1.5"} ${align === "end" ? "right-0" : align === "start" ? "left-0" : "left-1/2 -translate-x-1/2"}`}
      >
        <span className={detail ? "block font-medium" : undefined}>{label}</span>
        {detail && <span className="mt-0.5 block opacity-70">{detail}</span>}
      </span>
    </span>
  );
}

/** A small icon button under a message. */
export const MESSAGE_ICON_BUTTON =
  "flex h-6 w-6 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-[var(--muted)]";
