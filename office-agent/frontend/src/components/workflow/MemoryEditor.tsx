import { useState } from "react";
import { controlClass, primaryButton, secondaryButton } from "../../lib/formStyles";
import { MEMORY_TYPE_LABEL, memoryFromText, memoryPreview, memoryText } from "../../lib/memoryWords";
import { IDENTIFIER } from "../../lib/workflowEdit";
import type { MemoryEntry, RememberStep } from "../../types/workflow";
import { type EditorProps, ValuesHint } from "./editorParts";
import { AddRowButton, AutoTextarea, FieldLabel, RemoveButton } from "./fields";
import { SelectMenu } from "../SelectMenu";
import { SectionHeading, VarToken } from "./parts";

// What a task keeps from one run to the next (decision 0034): the values it declares, edited
// beside its inputs, and the remember step that keeps one.

interface Row extends MemoryEntry {
  /** The name it had when editing began, to carry references over. */
  original: string | null;
  /** The starting value as typed. */
  text: string;
}

function toRow(entry: MemoryEntry): Row {
  return { ...entry, original: entry.name, text: memoryText(entry.initial, entry.type) };
}

function cleanRow({ original: _original, text, ...entry }: Row): MemoryEntry {
  const initial = memoryFromText(text, entry.type);
  return { ...entry, initial: initial ?? (entry.type === "list" ? [] : null) };
}

function ReadOnlyMemory({ memory }: { memory: MemoryEntry[] }) {
  if (memory.length === 0) {
    return (
      <p className="text-[13px] text-[var(--muted)]">
        Nothing -- each run starts fresh. Add a value for a task that should only handle what is new since the last run.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {memory.map((entry) => (
        <li
          key={entry.name}
          className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-[var(--border)] px-3.5 py-2.5"
        >
          <VarToken name={`memory.${entry.name}`} isInput={false} />
          <span className="text-[13px] text-[var(--muted)]">
            {entry.label || MEMORY_TYPE_LABEL[entry.type]} · {MEMORY_TYPE_LABEL[entry.type].toLowerCase()}
          </span>
          <span className="flex-1" />
          <span className="flex items-center gap-2 text-[13px]">
            <span className="text-[var(--muted)]">First run reads</span>
            <span className="rounded-md bg-[var(--card-bg)] px-2 py-0.5">{memoryPreview(entry.initial)}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

interface MemorySectionProps {
  memory: MemoryEntry[];
  /** Resolves to an error message, or null once saved. */
  onSave: (memory: MemoryEntry[], renames: [string, string][]) => Promise<string | null>;
}

const GRID = "grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_100px_minmax(0,1.2fr)_28px] gap-2";

function MemoryRowFields({
  row,
  index,
  onChange,
  onRemove,
}: {
  row: Row;
  index: number;
  onChange: (changes: Partial<Row>) => void;
  onRemove: () => void;
}) {
  return (
    <div className={`${GRID} items-start`}>
      <input
        aria-label={`Remembered value ${index + 1} name`}
        aria-invalid={!IDENTIFIER.test(row.name)}
        spellCheck={false}
        className={`${controlClass} min-w-0 font-mono text-[12.5px]`}
        value={row.name}
        onChange={(e) => onChange({ name: e.target.value.trim() })}
      />
      <input
        aria-label={`Remembered value ${index + 1} label`}
        className={`${controlClass} min-w-0`}
        placeholder="e.g. Invoices already filed"
        value={row.label}
        onChange={(e) => onChange({ label: e.target.value })}
      />
      <SelectMenu
        ariaLabel={`Remembered value ${index + 1} type`}
        variant="field"
        value={row.type}
        options={Object.entries(MEMORY_TYPE_LABEL).map(([type, label]) => ({ value: type as MemoryEntry["type"], label }))}
        onChange={(type) => onChange({ type, text: "" })}
      />
      <AutoTextarea
        label={`Remembered value ${index + 1} starting value`}
        placeholder={row.type === "list" ? "Empty, or one item per line" : "Empty"}
        value={row.text}
        onChange={(text) => onChange({ text })}
      />
      <RemoveButton label={`Remove remembered value ${row.name || index + 1}`} onClick={onRemove} />
    </div>
  );
}

function blankRow(index: number): Row {
  return {
    name: index === 0 ? "seen" : `value${index + 1}`,
    label: index === 0 ? "Already handled" : "",
    type: index === 0 ? "list" : "text",
    original: null,
    text: "",
  };
}

/** The workflow's "Remembered between runs" section. */
export function MemorySection({ memory, onSave }: MemorySectionProps) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const update = (index: number, changes: Partial<Row>) =>
    setRows((current) => current?.map((row, i) => (i === index ? { ...row, ...changes } : row)) ?? null);
  const save = async () => {
    if (!rows) return;
    setSaving(true);
    const renames = rows
      .filter((row) => row.original !== null && row.original !== row.name)
      .map((row) => [`memory.${row.original}`, `memory.${row.name}`] as [string, string]);
    const problem = await onSave(rows.map(cleanRow), renames);
    setSaving(false);
    setError(problem);
    if (!problem) setRows(null);
  };
  const invalidName = rows?.some((row) => !IDENTIFIER.test(row.name)) ?? false;
  const startEditing = () => {
    setRows(memory.length > 0 ? memory.map(toRow) : [blankRow(0)]);
    setError(null);
  };

  return (
    <section>
      <SectionHeading
        aside={
          rows === null && (
            <button
              type="button"
              className="rounded-md px-2 py-0.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={startEditing}
            >
              {memory.length === 0 ? "Add a value" : "Edit"}
            </button>
          )
        }
      >
        Remembered between runs
      </SectionHeading>
      {rows === null ? (
        <ReadOnlyMemory memory={memory} />
      ) : (
        <div className="flex flex-col gap-2 rounded-xl border border-[color-mix(in_srgb,var(--accent)_70%,transparent)] p-3">
          <div className={`${GRID} px-1 text-xs text-[var(--muted)]`}>
            <span>Name</span>
            <span>Shown as</span>
            <span>Type</span>
            <span>First run reads</span>
            <span />
          </div>
          {rows.map((row, index) => (
            <MemoryRowFields
              key={index}
              row={row}
              index={index}
              onChange={(changes) => update(index, changes)}
              onRemove={() => setRows(rows.filter((_, i) => i !== index))}
            />
          ))}
          <AddRowButton onClick={() => setRows([...rows, blankRow(rows.length)])}>Add a value</AddRowButton>
          <p className="text-xs text-[var(--muted)]">
            Steps read each as <span className="font-mono">{"{{memory.name}}"}</span>, and when the run started as{" "}
            <span className="font-mono">{"{{run.started_at}}"}</span>. A Remember step keeps a new value, only once the
            run finishes.
          </p>
          {invalidName && (
            <p className="text-xs text-[var(--danger)]">
              Names use lowercase letters, digits and _, starting with a letter.
            </p>
          )}
          {error && (
            <p role="alert" className="text-sm text-[var(--danger)]">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={() => setRows(null)}>
              Cancel
            </button>
            <button type="button" disabled={saving || invalidName} className={primaryButton} onClick={save}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

export function RememberEditor({ step, onChange, context }: EditorProps<RememberStep>) {
  const memory = context.memory ?? [];
  return (
    <>
      <div className="max-w-xs">
        <FieldLabel htmlFor={`${step.id}-name`}>Keep as</FieldLabel>
        <SelectMenu
          id={`${step.id}-name`}
          variant="field"
          invalid={!memory.some((m) => m.name === step.name)}
          value={step.name}
          placeholder="Choose a value"
          options={memory.map((m) => ({ value: m.name, label: m.label || m.name }))}
          onChange={(name) => onChange({ ...step, name })}
        />
        {memory.length === 0 && (
          <p className="mt-1 text-xs text-[var(--danger)]">Add a value under “Remembered between runs” first.</p>
        )}
      </div>
      <div>
        <FieldLabel
          htmlFor={`${step.id}-value`}
          hint="Kept only once the run finishes; later steps still read the old one"
        >
          What to keep
        </FieldLabel>
        <AutoTextarea id={`${step.id}-value`} value={step.value} onChange={(value) => onChange({ ...step, value })} />
        <ValuesHint context={context} />
      </div>
    </>
  );
}
