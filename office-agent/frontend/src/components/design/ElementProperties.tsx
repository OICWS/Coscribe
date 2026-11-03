import { useState } from "react";
import { partNote, type ElementChange, type InspectedElement } from "../../lib/boardInspector";

const SECTIONS: [string, [string, string][]][] = [
  [
    "Layout",
    [
      ["display", "Display"],
      ["position", "Position"],
      ["flex-direction", "Direction"],
      ["justify-content", "Justify"],
      ["align-items", "Align"],
      ["gap", "Gap"],
      ["padding", "Padding"],
      ["margin", "Margin"],
    ],
  ],
  [
    "Text",
    [
      ["font-family", "Font"],
      ["font-size", "Size"],
      ["font-weight", "Weight"],
      ["line-height", "Line height"],
      ["color", "Color"],
    ],
  ],
  [
    "Fill",
    [
      ["background-color", "Background"],
      ["border-radius", "Radius"],
      ["opacity", "Opacity"],
    ],
  ],
];

// What the Properties tab writes back by eye; the Code tab writes any property.
const EDITABLE = new Set(["width", "height", "font-size", "font-weight", "color", "background-color", "border-radius", "padding", "gap", "opacity"]);
// Values that say nothing about the element: a reader scans what was set, not every default.
const SAYS_NOTHING = new Set(["", "normal", "none", "0px", "static", "rgba(0, 0, 0, 0)", "1", "auto"]);

const swatchOf = (value: string) => (/^(rgb|#)/.test(value.trim()) ? value.trim() : null);

function ReadRow({ label, value }: { label: string; value: string }) {
  const swatch = swatchOf(value);
  return (
    <div className="flex items-center gap-2 py-1 text-[13px]">
      <span className="w-24 shrink-0 text-[var(--muted)]">{label}</span>
      {swatch && <span className="h-3.5 w-3.5 shrink-0 rounded border border-[var(--border)]" style={{ background: swatch }} />}
      <span className="min-w-0 flex-1 truncate" title={value}>
        {value}
      </span>
    </div>
  );
}

/** A value the person types: written when Enter is pressed or the field is left, if it changed. */
function EditRow({ label, value, onCommit }: { label: string; value: string; onCommit: (value: string) => void }) {
  const [draft, setDraft] = useState(value);
  const swatch = swatchOf(draft);
  const commit = () => draft.trim() !== value && onCommit(draft.trim());
  return (
    <label className="flex items-center gap-2 py-0.5 text-[13px]">
      <span className="w-24 shrink-0 text-[var(--muted)]">{label}</span>
      {swatch && <span className="h-3.5 w-3.5 shrink-0 rounded border border-[var(--border)]" style={{ background: swatch }} />}
      <input
        aria-label={label}
        value={draft}
        className="min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-1.5 py-1 hover:border-[var(--border)] focus:border-[var(--accent)] focus:outline-none"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") setDraft(value);
        }}
      />
    </label>
  );
}

function TextField({ value, onCommit }: { value: string; onCommit: (value: string) => void }) {
  const [draft, setDraft] = useState(value);
  return (
    <textarea
      aria-label="Text"
      value={draft}
      rows={Math.min(6, Math.max(2, Math.ceil(value.length / 34)))}
      className="w-full resize-none rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-[13px] focus:border-[var(--accent)] focus:outline-none"
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => draft !== value && onCommit(draft)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          e.currentTarget.blur();
        }
      }}
    />
  );
}

/** The picked element's size, layout, text and fill. The properties a person changes by eye are
 * fields that write into the page; the others only say what the page sets. */
export function ElementProperties({ element, problem, onEdit }: { element: InspectedElement; problem: string | null; onEdit: (change: ElementChange) => void }) {
  const style = (name: string) => (value: string) => onEdit({ style: { [name]: value } });
  return (
    // Keyed by the element and its values, so a field shows the page again after a save.
    <fieldset
      key={`${element.path}|${JSON.stringify(element.computed)}|${element.content}`}
      disabled={element.part !== null}
      className="min-w-0 divide-y divide-[var(--border)] disabled:[&_input]:opacity-60 disabled:[&_textarea]:opacity-60"
    >
      {problem && (
        <p role="alert" className="px-3 py-2 text-[13px] text-[var(--danger)]">
          {problem}
        </p>
      )}
      {element.part && !problem && <p className="px-3 py-2 text-[13px] text-[var(--muted)]">{partNote(element.part)}</p>}
      {element.content !== null && (
        <section className="px-3 py-2">
          <h3 className="mb-1 text-[13px] font-semibold">Text</h3>
          <TextField value={element.content} onCommit={(text) => onEdit({ text })} />
        </section>
      )}
      <section className="px-3 py-2">
        <h3 className="mb-1 text-[13px] font-semibold">Size</h3>
        <EditRow label="Width" value={`${Math.round(element.box.width)}px`} onCommit={style("width")} />
        <EditRow label="Height" value={`${Math.round(element.box.height)}px`} onCommit={style("height")} />
      </section>
      {SECTIONS.map(([title, fields]) => {
        const shown = fields.filter(([name]) => EDITABLE.has(name) || !SAYS_NOTHING.has(element.computed[name] ?? ""));
        return (
          <section key={title} className="px-3 py-2">
            <h3 className="mb-1 text-[13px] font-semibold">{title}</h3>
            {shown.map(([name, label]) =>
              EDITABLE.has(name) ? (
                <EditRow key={name} label={label} value={element.computed[name] ?? ""} onCommit={style(name)} />
              ) : (
                <ReadRow key={name} label={label} value={element.computed[name]} />
              ),
            )}
          </section>
        );
      })}
    </fieldset>
  );
}
