import { useCallback, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { CheckIcon, ChevronDownIcon } from "./icons";

export interface SelectOption<T extends string | number> {
  value: T;
  label: ReactNode;
  disabled?: boolean;
  /** A heading shown above the first option of a run with the same group. */
  group?: string;
}

const TRIGGER = {
  plain:
    "flex h-8 max-w-full items-center gap-2 rounded-lg px-3 text-sm text-[var(--fg)] hover:bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))] aria-expanded:bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))]",
  field:
    "flex w-full min-w-0 items-center justify-between gap-2 rounded-md border border-[var(--border)] bg-transparent px-2.5 py-1.5 text-left text-sm text-[var(--fg)] outline-none transition-colors hover:border-[var(--border-hover)] focus-visible:ring-2 focus-visible:ring-[var(--accent-soft)] aria-expanded:border-[var(--border-hover)] aria-[invalid=true]:border-[var(--danger)] disabled:cursor-not-allowed disabled:opacity-50",
};

const MENU_MAX_HEIGHT = 288;
const GAP = 4;

interface Place {
  left?: number;
  right?: number;
  top?: number;
  bottom?: number;
  minWidth: number;
  maxHeight: number;
}

/** Where the menu goes: under the trigger, or above it when there is more room there. It is
 * fixed to the viewport in a portal, so a dialog or a scrolling side panel can't clip it. */
function placeFor(trigger: HTMLElement, alignEnd: boolean): Place {
  const rect = trigger.getBoundingClientRect();
  const below = window.innerHeight - rect.bottom - GAP * 2;
  const above = rect.top - GAP * 2;
  const up = below < Math.min(MENU_MAX_HEIGHT, 160) && above > below;
  const horizontal = alignEnd ? { right: Math.max(GAP, window.innerWidth - rect.right) } : { left: Math.max(GAP, rect.left) };
  return {
    ...horizontal,
    ...(up ? { bottom: window.innerHeight - rect.top + GAP } : { top: rect.bottom + GAP }),
    minWidth: rect.width,
    maxHeight: Math.max(120, Math.min(MENU_MAX_HEIGHT, up ? above : below)),
  };
}

function OptionRow<T extends string | number>({
  option,
  checked,
  heading,
  onPick,
}: {
  option: SelectOption<T>;
  checked: boolean;
  heading: string | null | undefined;
  onPick: () => void;
}) {
  return (
    <div>
      {heading && <div className="px-3 pb-1 pt-2 text-xs font-medium text-[var(--muted)]">{heading}</div>}
      <button
        type="button"
        role="menuitemradio"
        aria-checked={checked}
        disabled={option.disabled}
        className={`flex w-full items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-left text-sm outline-none hover:bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))] focus-visible:bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent ${
          checked ? "bg-[color-mix(in_srgb,var(--border)_50%,var(--card-bg))]" : ""
        } ${option.group ? "pl-5" : ""}`}
        onClick={onPick}
      >
        <span className="flex-1">{option.label}</span>
        {checked && <CheckIcon className="h-4 w-4 shrink-0 text-[var(--focus)]" />}
      </button>
    </div>
  );
}

/** The open menu: takes focus, closes on a click elsewhere, follows its trigger, and moves with
 * the arrow keys. */
function MenuPopup<T extends string | number>({
  place,
  trigger,
  label,
  labelledBy,
  options,
  value,
  onPick,
  onClose,
  onMove,
}: {
  place: Place;
  trigger: RefObject<HTMLButtonElement | null>;
  label?: string;
  labelledBy?: string;
  options: readonly SelectOption<T>[];
  value: T;
  onPick: (value: T) => void;
  onClose: (refocus: boolean) => void;
  onMove: () => void;
}) {
  const menuRef = useRef<HTMLDivElement>(null);
  const enabledItems = () => [...(menuRef.current?.querySelectorAll<HTMLButtonElement>("[role=menuitemradio]:not(:disabled)") ?? [])];

  useLayoutEffect(() => {
    const items = enabledItems();
    (items.find((item) => item.getAttribute("aria-checked") === "true") ?? items[0])?.focus({ preventScroll: true });
    menuRef.current?.querySelector("[aria-checked=true]")?.scrollIntoView({ block: "nearest" });
    const onDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !trigger.current?.contains(target)) onClose(false);
    };
    // A scroll inside the menu is its own; any other moves the trigger, so follow it.
    const onScroll = (event: Event) => {
      if (!(event.target instanceof Node && menuRef.current?.contains(event.target))) onMove();
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onMove);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onMove);
    };
    // Focus and listeners belong to one opening; a new place while open must not refocus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onKeyDown = (event: KeyboardEvent) => {
    // Stops here so a dialog's own Escape handler doesn't close the dialog as well.
    event.stopPropagation();
    const items = enabledItems();
    const at = items.indexOf(document.activeElement as HTMLButtonElement);
    const move = (to: number) => {
      event.preventDefault();
      items[(to + items.length) % items.length]?.focus();
    };
    if (event.key === "Escape") {
      event.preventDefault();
      onClose(true);
    } else if (event.key === "Tab") onClose(false);
    else if (event.key === "ArrowDown") move(at + 1);
    else if (event.key === "ArrowUp") move(at < 0 ? items.length - 1 : at - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(items.length - 1);
  };

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-label={label}
      aria-labelledby={label ? undefined : labelledBy}
      style={place}
      className="fixed z-[70] min-w-[10rem] max-w-[min(32rem,calc(100vw-1rem))] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--panel-bg)] p-1.5 text-[var(--fg)] shadow-[var(--shadow)]"
      onKeyDown={onKeyDown}
    >
      {options.map((option, index) => (
        <OptionRow
          key={String(option.value)}
          option={option}
          checked={option.value === value}
          heading={option.group && option.group !== options[index - 1]?.group ? option.group : null}
          onPick={() => {
            onClose(true);
            if (option.value !== value) onPick(option.value);
          }}
        />
      ))}
    </div>,
    document.body,
  );
}

/** The one dropdown of the app: a button that opens a checked-item menu, in place of the
 * native <select> whose popup the OS draws in its own colors and font. `plain` is the
 * borderless button of a settings row; `field` sits among bordered inputs in a form. Keep
 * SegmentedControl for two to four short choices worth seeing at once. */
export function SelectMenu<T extends string | number>({
  value,
  options,
  onChange,
  ariaLabel,
  id,
  placeholder = "",
  variant = "plain",
  className = "",
  triggerClassName = "",
  disabled = false,
  invalid = false,
}: {
  value: T;
  options: readonly SelectOption<T>[];
  onChange: (value: T) => void;
  /** Leave it out when a <label htmlFor={id}> names the control. */
  ariaLabel?: string;
  id?: string;
  placeholder?: ReactNode;
  variant?: "plain" | "field";
  /** On the wrapper: the width of a field, a margin. */
  className?: string;
  /** On the button itself: a smaller padding or font beside compact inputs. */
  triggerClassName?: string;
  disabled?: boolean;
  invalid?: boolean;
}) {
  const [place, setPlace] = useState<Place | null>(null);
  const open = place !== null;
  const triggerRef = useRef<HTMLButtonElement>(null);
  const current = options.find((option) => option.value === value);
  const alignEnd = variant === "plain";

  const close = useCallback((refocus: boolean) => {
    setPlace(null);
    if (refocus) triggerRef.current?.focus();
  }, []);
  const show = () => {
    if (triggerRef.current && !disabled) setPlace(placeFor(triggerRef.current, alignEnd));
  };

  return (
    <div className={variant === "plain" ? `w-fit max-w-full ${className}` : `min-w-0 ${className}`}>
      <button
        ref={triggerRef}
        id={id}
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-invalid={invalid || undefined}
        disabled={disabled}
        className={`${TRIGGER[variant]} ${triggerClassName}`}
        onClick={() => (open ? close(false) : show())}
        onKeyDown={(event) => {
          if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
            event.preventDefault();
            show();
          }
        }}
      >
        <span className={`min-w-0 truncate ${current ? "" : "text-[var(--muted)]"}`}>{current?.label ?? placeholder}</span>
        <ChevronDownIcon className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
      </button>
      {place && (
        <MenuPopup place={place} trigger={triggerRef} label={ariaLabel} labelledBy={id} options={options} value={value} onPick={onChange} onClose={close} onMove={() => show()} />
      )}
    </div>
  );
}
