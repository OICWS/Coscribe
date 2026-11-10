import type { ReactNode } from "react";

/** Text fields and selects across Settings: a bright field with a blue
 * focus ring. */
export const fieldClass =
  "h-9 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3 text-sm text-[var(--fg)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--focus)] focus:ring-2 focus:ring-[var(--focus)]/15";

export const primaryButtonClass =
  "h-9 rounded-lg bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:cursor-default disabled:opacity-40";

export const secondaryButtonClass =
  "h-9 rounded-lg border border-[var(--border)] bg-[var(--field-bg)] px-3.5 text-sm text-[var(--fg)] hover:bg-[var(--card-bg)] disabled:cursor-default disabled:opacity-40";

/** A titled group of settings: a bold heading, an optional line under
 * it, then its rows or content. */
export function SettingsSection({ title, description, action, children }: { title: string; description?: ReactNode; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="flex flex-col">
      <div className="mb-1 flex items-start justify-between gap-4">
        <div className="min-w-0">
          {title && <h2 className="text-[17px] font-semibold text-[var(--fg)]">{title}</h2>}
          {description && <p className="mt-1 text-sm leading-relaxed text-[var(--muted)]">{description}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </section>
  );
}

/** Rows separated by hairlines, the way a section lists its settings. */
export function SettingRows({ children }: { children: ReactNode }) {
  // A block of sub-options (`.sub-rows`) belongs to the row above it, so no hairline parts them.
  return (
    <div className="flex flex-col divide-y divide-[color-mix(in_srgb,var(--border)_55%,transparent)] [&>.sub-rows]:!border-t-0 [&>:has(+.sub-rows)]:!border-b-0">{children}</div>
  );
}

/** One setting: its name and what it does on the left, its control on
 * the right. */
export function SettingRow({ label, description, control }: { label: string; description?: ReactNode; control: ReactNode }) {
  return (
    <div data-setting-label={label} className="setting-row relative isolate has-[[aria-expanded=true]]:z-10 flex min-h-[64px] items-center justify-between gap-10 py-3.5">
      <div className="flex min-w-0 max-w-[480px] flex-col gap-1">
        <span data-setting-name className="relative text-[15px] text-[var(--fg)]">
          {label}
        </span>
        {description && <span className="text-[13px] leading-snug text-[var(--muted)]">{description}</span>}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

/** Options that belong to the row above: indented under it, inside the same divider. */
export function SubRows({ children }: { children: ReactNode }) {
  return <div className="sub-rows -mt-1.5 flex flex-col pb-1.5 pl-[18px] [&_.setting-row]:min-h-0 [&_.setting-row]:py-2.5">{children}</div>;
}
