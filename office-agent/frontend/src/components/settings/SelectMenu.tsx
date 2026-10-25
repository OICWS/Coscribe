import { useRef, useState, type ReactNode } from "react";
import { useClickOutside } from "../../lib/useClickOutside";
import { CheckIcon, ChevronDownIcon } from "../icons";

export interface SelectOption<T extends string> {
  value: T;
  label: ReactNode;
}

/** A borderless button that opens a checked-item menu, replacing the
 * native <select> whose popup the OS draws in its own colors. Keep
 * SegmentedControl for two to four short choices worth seeing at once. */
export function SelectMenu<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  placeholder = "",
}: {
  value: T;
  options: readonly SelectOption<T>[];
  onChange: (value: T) => void;
  ariaLabel: string;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useClickOutside(rootRef, () => setOpen(false), open);
  const current = options.find((option) => option.value === value);

  return (
    <div
      className="relative w-fit max-w-full"
      ref={rootRef}
      onKeyDown={(e) => {
        if (e.key === "Escape") setOpen(false);
      }}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-8 max-w-full items-center gap-2 rounded-lg px-3 text-sm text-[var(--fg)] hover:bg-[var(--border)] aria-expanded:bg-[var(--border)]"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="min-w-0 truncate">{current?.label ?? placeholder}</span>
        <ChevronDownIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={ariaLabel}
          className="absolute right-0 top-full z-20 mt-1 max-h-72 min-w-[14rem] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-1 shadow-[var(--shadow)]"
        >
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              role="menuitemradio"
              aria-checked={option.value === value}
              className={`flex w-full items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--border)] ${
                option.value === value ? "bg-[var(--border)]" : ""
              }`}
              onClick={() => {
                setOpen(false);
                onChange(option.value);
              }}
            >
              <span className="flex-1">{option.label}</span>
              {option.value === value && <CheckIcon className="h-4 w-4 shrink-0 text-[var(--focus)]" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
