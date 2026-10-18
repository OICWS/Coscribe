import { useState, type ReactNode } from "react";
import { ChevronDownIcon } from "../icons";
import { ColourPicker } from "./SlideFormatBar";
import { SlideMenu, type MenuEntry } from "./SlideMenu";

export const field =
  "flex h-8 min-w-0 flex-1 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-2.5 text-sm text-[var(--fg)] hover:border-[var(--muted)]";

/** A titled group of rows in the properties panel. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2 border-b border-[var(--border)] px-3 py-3 last:border-b-0">
      <h3 className="pb-0.5 text-[15px] font-semibold text-[var(--fg)]">{title}</h3>
      {children}
    </section>
  );
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-[84px] shrink-0 text-sm text-[var(--muted)]">{label}</span>
      {children}
    </div>
  );
}

/** A number typed in, applied on Enter or when the field loses focus. */
export function NumberField({
  label,
  value,
  unit,
  onCommit,
}: {
  label: string;
  value: number;
  unit?: string;
  onCommit: (value: number) => void;
}) {
  const shown = String(Math.round(value * 100) / 100);
  const [typed, setTyped] = useState<{ of: string; text: string } | null>(null);
  const text = typed && typed.of === shown ? typed.text : shown;
  const commit = () => {
    const n = Number(text);
    if (text.trim() !== "" && Number.isFinite(n) && String(n) !== shown) onCommit(n);
    setTyped(null);
  };
  return (
    <label className={`${field} gap-1`}>
      <input
        aria-label={label}
        className="h-full min-w-0 flex-1 bg-transparent outline-none"
        value={text}
        inputMode="decimal"
        onChange={(e) => setTyped({ of: shown, text: e.target.value })}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />
      {unit && <span className="text-xs text-[var(--muted)]">{unit}</span>}
    </label>
  );
}

/** A field that opens a menu of choices. */
export function MenuField({ label, value, entries }: { label: string; value: string; entries: MenuEntry[] }) {
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  return (
    <>
      <button type="button" aria-label={label} aria-haspopup="menu" className={field} onClick={(e) => setAnchor(e.currentTarget.getBoundingClientRect())}>
        <span className="flex-1 truncate text-left">{value}</span>
        <ChevronDownIcon className="h-4 w-4 text-[var(--muted)]" />
      </button>
      {anchor && <SlideMenu anchor={anchor} label={label} width={Math.max(anchor.width, 200)} align="left" entries={entries} onClose={() => setAnchor(null)} />}
    </>
  );
}

interface Choice<T extends string> {
  value: T;
  title: string;
  icon: ReactNode;
}

/** One choice of a few, as icon buttons. */
export function Segmented<T extends string>({ label, choices, value, onChange }: { label: string; choices: Choice<T>[]; value: T; onChange: (value: T) => void }) {
  return (
    <div role="group" aria-label={label} className="flex h-8 flex-1 rounded-lg bg-[var(--card-bg)] p-0.5">
      {choices.map((choice) => (
        <button
          key={choice.value}
          type="button"
          title={choice.title}
          aria-label={choice.title}
          aria-pressed={choice.value === value}
          className={`flex flex-1 items-center justify-center rounded-md text-[var(--fg)] ${choice.value === value ? "bg-[var(--bg)] shadow-sm" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}
          onClick={() => onChange(choice.value)}
        >
          {choice.icon}
        </button>
      ))}
    </div>
  );
}

/** A colour shown as a swatch and its hex, opening the picker; `onClear` adds a way to none. */
export function ColourField({
  label,
  value,
  colours,
  onPick,
  onClear,
}: {
  label: string;
  value: string | null;
  colours: string[];
  onPick: (colour: string) => void;
  onClear?: () => void;
}) {
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  return (
    <>
      <button type="button" aria-label={label} className={field} onClick={(e) => setAnchor(e.currentTarget.getBoundingClientRect())}>
        <span className="h-[18px] w-[18px] shrink-0 rounded border border-[var(--border)]" style={{ background: value ?? "transparent" }} />
        <span className="flex-1 truncate text-left font-mono text-[13px]">{value ?? "None"}</span>
      </button>
      {onClear && value && (
        <button type="button" aria-label={`Remove ${label.toLowerCase()}`} className="px-1 text-[var(--muted)] hover:text-[var(--fg)]" onClick={onClear}>
          −
        </button>
      )}
      {anchor && (
        <ColourPicker
          anchor={anchor}
          current={value ?? "#FFFFFF"}
          colours={colours}
          onPick={(colour) => {
            onPick(colour);
            setAnchor(null);
          }}
          onClose={() => setAnchor(null)}
        />
      )}
    </>
  );
}
