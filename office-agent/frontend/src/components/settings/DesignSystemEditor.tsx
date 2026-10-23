import { useState, type ReactNode } from "react";
import { saveDesignSystem } from "../../lib/rest";
import type { DesignColor, DesignNamedValue, DesignSystem, DesignTextStyle } from "../../types/settings";
import { ArrowLeftIcon, PlusIcon, TrashIcon } from "../icons";
import { ConfirmDialog } from "../ConfirmDialog";
import { fieldClass, primaryButtonClass, secondaryButtonClass } from "./SettingRow";

const SECTIONS = ["Overview", "Colors", "Typography", "Spacing", "Corner radius"] as const;
type Section = (typeof SECTIONS)[number];

const numberField = `${fieldClass} w-full min-w-0`;

function Heading({ title, hint }: { title: string; hint: ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-[17px] font-medium">{title}</h3>
      <p className="mt-1 text-sm text-[var(--muted)]">{hint}</p>
    </div>
  );
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" aria-label={label} title={label} className={`${secondaryButtonClass} !px-2.5`} onClick={onClick}>
      <TrashIcon className="h-4 w-4" />
    </button>
  );
}

function replaceAt<T>(list: T[], index: number, change: Partial<T>): T[] {
  return list.map((item, i) => (i === index ? { ...item, ...change } : item));
}

function Colors({ colors, onChange }: { colors: DesignColor[]; onChange: (next: DesignColor[]) => void }) {
  return (
    <div className="flex flex-col gap-2">
      {colors.map((color, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2">
          <input
            type="color"
            aria-label={`${color.name || "Color"} swatch`}
            className="h-9 w-10 cursor-pointer rounded-lg border border-[var(--border)] bg-transparent p-0.5"
            value={/^#[0-9a-fA-F]{6}$/.test(color.value) ? color.value : "#000000"}
            onChange={(e) => onChange(replaceAt(colors, i, { value: e.target.value.toUpperCase() }))}
          />
          <input
            aria-label="Color name"
            className={`${fieldClass} w-36`}
            placeholder="Name"
            value={color.name}
            onChange={(e) => onChange(replaceAt(colors, i, { name: e.target.value }))}
          />
          <input
            aria-label="Color value"
            className={`${fieldClass} w-28 font-mono`}
            value={color.value}
            onChange={(e) => onChange(replaceAt(colors, i, { value: e.target.value }))}
          />
          <input
            aria-label="When to use it"
            className={`${fieldClass} min-w-40 flex-1`}
            placeholder="When to use it"
            value={color.note}
            onChange={(e) => onChange(replaceAt(colors, i, { note: e.target.value }))}
          />
          <RemoveButton label="Remove color" onClick={() => onChange(colors.filter((_, k) => k !== i))} />
        </div>
      ))}
      <div>
        <button
          type="button"
          className={`${secondaryButtonClass} flex items-center gap-1.5`}
          onClick={() => onChange([...colors, { name: "", value: "#2563EB", note: "" }])}
        >
          <PlusIcon className="h-4 w-4" /> Add color
        </button>
      </div>
    </div>
  );
}

function NamedValues({
  rows,
  what,
  valueHint,
  onChange,
}: {
  rows: DesignNamedValue[];
  what: string;
  valueHint: string;
  onChange: (next: DesignNamedValue[]) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {rows.map((row, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            aria-label={`${what} name`}
            className={`${fieldClass} w-48`}
            placeholder="Name"
            value={row.name}
            onChange={(e) => onChange(replaceAt(rows, i, { name: e.target.value }))}
          />
          <input
            aria-label={`${what} value`}
            className={`${fieldClass} w-32`}
            placeholder={valueHint}
            value={row.value}
            onChange={(e) => onChange(replaceAt(rows, i, { value: e.target.value }))}
          />
          <RemoveButton label={`Remove ${what}`} onClick={() => onChange(rows.filter((_, k) => k !== i))} />
        </div>
      ))}
      <div>
        <button
          type="button"
          className={`${secondaryButtonClass} flex items-center gap-1.5`}
          onClick={() => onChange([...rows, { name: "", value: "" }])}
        >
          <PlusIcon className="h-4 w-4" /> Add {what}
        </button>
      </div>
    </div>
  );
}

function Typography({ typography, onChange }: { typography: DesignSystem["typography"]; onChange: (next: DesignSystem["typography"]) => void }) {
  const styles = typography.styles;
  const setStyles = (next: DesignTextStyle[]) => onChange({ ...typography, styles: next });
  const numeric = (i: number, key: "size" | "weight" | "line_height" | "letter_spacing", text: string) => {
    const value = Number(text);
    if (text.trim() !== "" && !Number.isNaN(value)) setStyles(replaceAt(styles, i, { [key]: value }));
  };
  return (
    <div className="flex flex-col gap-5">
      <label className="flex flex-col gap-1 text-sm">
        Fonts
        <textarea
          aria-label="Fonts"
          className={`${fieldClass} h-20 py-2`}
          placeholder="One font per line, as installed on this computer"
          value={typography.fonts.join("\n")}
          onChange={(e) => onChange({ ...typography, fonts: e.target.value.split("\n") })}
        />
        <span className="text-xs text-[var(--muted)]">The first one is the main font. A font that is not installed is replaced when a deck is opened elsewhere.</span>
      </label>
      <div className="flex flex-col gap-2">
        <div className="text-sm">Text styles</div>
        <div className="grid grid-cols-[minmax(0,1fr)_repeat(4,5.5rem)_2.5rem] gap-2 text-xs text-[var(--muted)]">
          <span>Name</span>
          <span>Size (px)</span>
          <span>Weight</span>
          <span>Line height</span>
          <span>Spacing (px)</span>
          <span />
        </div>
        {styles.map((style, i) => (
          <div key={style.id} className="grid grid-cols-[minmax(0,1fr)_repeat(4,5.5rem)_2.5rem] items-center gap-2">
            <input
              aria-label="Text style name"
              className={`${fieldClass} min-w-0`}
              value={style.name}
              onChange={(e) => setStyles(replaceAt(styles, i, { name: e.target.value }))}
            />
            {(["size", "weight", "line_height", "letter_spacing"] as const).map((key) => (
              <input
                key={key}
                aria-label={`${style.name} ${key.replace("_", " ")}`}
                className={numberField}
                inputMode="decimal"
                defaultValue={style[key]}
                onChange={(e) => numeric(i, key, e.target.value)}
              />
            ))}
            <RemoveButton label={`Remove ${style.name}`} onClick={() => setStyles(styles.filter((_, k) => k !== i))} />
          </div>
        ))}
        <div>
          <button
            type="button"
            className={`${secondaryButtonClass} flex items-center gap-1.5`}
            onClick={() =>
              setStyles([...styles, { id: `style-${Date.now().toString(36)}`, name: "New style", size: 32, weight: 400, line_height: 1.4, letter_spacing: 0 }])
            }
          >
            <PlusIcon className="h-4 w-4" /> Add text style
          </button>
        </div>
      </div>
    </div>
  );
}

function SectionForm({ section, draft, onChange }: { section: Section; draft: DesignSystem; onChange: (next: DesignSystem) => void }) {
  return (
    <>
  {section === "Overview" && (
        <>
          <Heading title="Overview" hint="In your own words: who this is for and how it should feel. The assistant reads it when it makes something with this system." />
          <textarea
            aria-label="Overview"
            className={`${fieldClass} h-56 w-full max-w-2xl py-2`}
            value={draft.overview}
            onChange={(e) => onChange({ ...draft, overview: e.target.value })}
          />
        </>
      )}
  {section === "Colors" && (
        <>
          <Heading title="Colors" hint="Name each color for the job it does, and say when to use it." />
          <Colors colors={draft.colors} onChange={(colors) => onChange({ ...draft, colors })} />
        </>
      )}
  {section === "Typography" && (
        <>
          <Heading title="Typography" hint="The fonts and the named text styles a deck uses." />
          <Typography typography={draft.typography} onChange={(typography) => onChange({ ...draft, typography })} />
        </>
      )}
  {section === "Spacing" && (
        <>
          <Heading title="Spacing" hint="Named gaps, in px on the 1920-wide slide." />
          <NamedValues rows={draft.spacing} what="spacing" valueHint="24" onChange={(spacing) => onChange({ ...draft, spacing })} />
        </>
      )}
  {section === "Corner radius" && (
        <>
          <Heading title="Corner radius" hint="Named roundings for cards and pictures, in px." />
          <NamedValues rows={draft.radius} what="radius" valueHint="16" onChange={(radius) => onChange({ ...draft, radius })} />
        </>
      )}
    </>
  );
}

/** One design system's page: a list of its sections on the left, the form of the chosen one on the right. */
export function DesignSystemEditor({ system, onBack, onSaved }: { system: DesignSystem; onBack: () => void; onSaved: (next: DesignSystem) => void }) {
  const [draft, setDraft] = useState(system);
  const [saved, setSaved] = useState(system);
  const [section, setSection] = useState<Section>("Overview");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);

  const save = async () => {
    setSaving(true);
    setError(null);
    const result = await saveDesignSystem(draft);
    setSaving(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setDraft(result);
    setSaved(result);
    onSaved(result);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="Back to design systems"
          className={`${secondaryButtonClass} !px-2.5`}
          onClick={() => (dirty ? setLeaving(true) : onBack())}
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
        <input
          aria-label="Design system name"
          className={`${fieldClass} w-72 text-[17px] font-medium`}
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
        />
        <div className="flex-1" />
        <button type="button" className={primaryButtonClass} disabled={!dirty || saving} onClick={() => void save()}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {error}
        </p>
      )}
      <div className="flex gap-8">
        <nav aria-label="Sections" className="flex w-40 shrink-0 flex-col gap-0.5">
          {SECTIONS.map((name) => (
            <button
              key={name}
              type="button"
              aria-current={section === name ? "page" : undefined}
              className={`h-9 rounded-lg px-3 text-left text-[15px] ${section === name ? "bg-[var(--card-bg)] font-medium" : "text-[var(--fg)]/80 hover:bg-[var(--card-bg)]"}`}
              onClick={() => setSection(name)}
            >
              {name}
            </button>
          ))}
        </nav>
        <div className="min-w-0 flex-1">
          <SectionForm section={section} draft={draft} onChange={setDraft} />
        </div>
      </div>
      {leaving && (
        <ConfirmDialog
          title="Discard your changes?"
          description="This design system has changes that are not saved."
          confirmLabel="Discard"
          onCancel={() => setLeaving(false)}
          onConfirm={onBack}
        />
      )}
    </div>
  );
}
