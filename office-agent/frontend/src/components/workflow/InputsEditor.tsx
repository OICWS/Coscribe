import { useState } from "react";
import { controlClass, primaryButton, secondaryButton } from "../../lib/formStyles";
import { INPUT_TYPE_LABEL, plainDefault } from "../../lib/inputKinds";
import { IDENTIFIER } from "../../lib/workflowEdit";
import type { WorkflowInput } from "../../types/workflow";
import { AddRowButton, AutoTextarea, RemoveButton } from "./fields";
import { InputValueControl } from "./InputValueControl";
import { SelectMenu } from "../SelectMenu";
import { SectionHeading, VarToken } from "./parts";

interface Row extends WorkflowInput {
  /** The name this input had when editing began, to carry references over. */
  original: string | null;
}

function ReadOnlyInputs({ inputs }: { inputs: WorkflowInput[] }) {
  if (inputs.length === 0) {
    return (
      <p className="text-[13px] text-[var(--muted)]">
        None -- every run uses the same values. Add one for anything that changes run to run, like a file.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {inputs.map((input) => (
        <li
          key={input.name}
          className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-[var(--border)] px-3.5 py-2.5"
        >
          <VarToken name={input.name} isInput />
          <span className="text-[13px] text-[var(--muted)]">
            {input.label || INPUT_TYPE_LABEL[input.type]} ·{" "}
            {input.required === false ? "optional at each run" : "asked at each run"}
          </span>
          <span className="flex-1" />
          {plainDefault(input) !== null && (
            <span className="flex items-center gap-2 text-[13px]">
              <span className="text-[var(--muted)]">Default</span>
              <span className="rounded-md bg-[var(--card-bg)] px-2 py-0.5">{plainDefault(input)}</span>
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

function blankRow(index: number): Row {
  return { name: `input${index + 1}`, label: "", type: "text", default: null, required: true, original: null };
}

interface InputsEditorProps {
  inputs: WorkflowInput[];
  /** Resolves to an error message, or null once saved. */
  onSave: (inputs: WorkflowInput[], renames: [string, string][]) => Promise<string | null>;
}

function cleanRow({ original: _original, ...input }: Row): WorkflowInput {
  const options = input.type === "choice" ? (input.options ?? []).map((o) => o.trim()).filter(Boolean) : undefined;
  return { ...input, default: input.default === "" ? null : input.default, options };
}

function TypeSelect({
  index,
  value,
  onChange,
}: {
  index: number;
  value: WorkflowInput["type"];
  onChange: (type: WorkflowInput["type"]) => void;
}) {
  return (
    <SelectMenu
      ariaLabel={`Input ${index + 1} type`}
      variant="field"
      value={value}
      options={Object.entries(INPUT_TYPE_LABEL).map(([type, label]) => ({ value: type as WorkflowInput["type"], label }))}
      onChange={onChange}
    />
  );
}

export function InputsEditor({ inputs, onSave }: InputsEditorProps) {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startEditing = () => {
    const current: Row[] = inputs.map((input) => ({ ...input, original: input.name }));
    setRows(current.length > 0 ? current : [blankRow(0)]);
    setError(null);
  };
  const update = (index: number, changes: Partial<Row>) =>
    setRows((current) => current?.map((row, i) => (i === index ? { ...row, ...changes } : row)) ?? null);

  const save = async () => {
    if (!rows) return;
    setSaving(true);
    const renames = rows
      .filter((row) => row.original !== null && row.original !== row.name)
      .map((row) => [row.original as string, row.name] as [string, string]);
    const problem = await onSave(rows.map(cleanRow), renames);
    setSaving(false);
    setError(problem);
    if (!problem) setRows(null);
  };

  const invalidName = rows?.some((row) => !IDENTIFIER.test(row.name)) ?? false;

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
              {inputs.length === 0 ? "Add an input" : "Edit"}
            </button>
          )
        }
      >
        Inputs
      </SectionHeading>
      {rows === null ? (
        <ReadOnlyInputs inputs={inputs} />
      ) : (
        <div className="flex flex-col gap-2 rounded-xl border border-[color-mix(in_srgb,var(--accent)_70%,transparent)] p-3">
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_120px_minmax(0,1.2fr)_64px_28px] gap-2 px-1 text-xs text-[var(--muted)]">
            <span>Name</span>
            <span>Shown as</span>
            <span>Type</span>
            <span>Default</span>
            <span>Optional</span>
            <span />
          </div>
          {rows.map((row, index) => (
            <div
              key={index}
              className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_120px_minmax(0,1.2fr)_64px_28px] items-center gap-2"
            >
              <input
                aria-label={`Input ${index + 1} name`}
                aria-invalid={!IDENTIFIER.test(row.name)}
                spellCheck={false}
                className={`${controlClass} min-w-0 font-mono text-[12.5px]`}
                value={row.name}
                onChange={(e) => update(index, { name: e.target.value.trim() })}
              />
              <input
                aria-label={`Input ${index + 1} label`}
                className={`${controlClass} min-w-0`}
                placeholder="e.g. PDF to audit"
                value={row.label}
                onChange={(e) => update(index, { label: e.target.value })}
              />
              <TypeSelect index={index} value={row.type} onChange={(type) => update(index, { type, default: null })} />
              <InputValueControl
                input={row}
                label={`Input ${index + 1} default`}
                value={row.default}
                onChange={(value) => update(index, { default: value })}
              />
              <label className="flex justify-center">
                <input
                  type="checkbox"
                  aria-label={`Input ${row.name || index + 1} may be left blank`}
                  className="h-4 w-4 accent-[var(--accent)]"
                  checked={row.required === false}
                  onChange={(e) => update(index, { required: !e.target.checked })}
                />
              </label>
              <RemoveButton
                label={`Remove input ${row.name || index + 1}`}
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
              />
              {row.type === "choice" && (
                <div className="col-span-full pl-1">
                  <AutoTextarea
                    label={`Input ${index + 1} options`}
                    placeholder="The options, one per line"
                    value={(row.options ?? []).join("\n")}
                    onChange={(text) => update(index, { options: text.split("\n") })}
                  />
                </div>
              )}
            </div>
          ))}
          <AddRowButton onClick={() => setRows([...rows, blankRow(rows.length)])}>Add an input</AddRowButton>
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
              {saving ? "Saving…" : "Save inputs"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
