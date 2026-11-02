import { controlClass, inputClass } from "../../lib/formStyles";
import { FIELD_TYPE_LABEL, hasEveryDefault, TIMEOUTS } from "../../lib/pauseWords";
import { duration } from "../../lib/plainSteps";
import { IDENTIFIER } from "../../lib/workflowEdit";
import type { AskField, AskStep, WaitStep } from "../../types/workflow";
import type { EditorProps } from "./editorParts";
import { ValuesHint } from "./editorParts";
import { AddRowButton, AutoTextarea, FieldLabel, RemoveButton } from "./fields";
import { InputValueControl } from "./InputValueControl";

// The full editor for the steps that pause a run (decision 0033).

const GRID = "grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_150px_minmax(0,1.2fr)_64px_28px] gap-2";

/** Where a pick's items come from, and which field of each it shows. */
function PickFrom({
  field,
  index,
  lists,
  onChange,
}: {
  field: AskField;
  index: number;
  lists: string[];
  onChange: (field: AskField) => void;
}) {
  return (
    <div className="col-span-full flex flex-wrap items-center gap-2 pl-1 text-sm">
      <span className="text-[var(--muted)]">From the list</span>
      <select
        aria-label={`Value ${index + 1} list`}
        className={`${controlClass} min-w-[10rem]`}
        value={field.items ?? ""}
        onChange={(e) => onChange({ ...field, items: e.target.value })}
      >
        {field.items && !lists.includes(field.items) && <option value={field.items}>{field.items}</option>}
        {lists.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <span className="text-[var(--muted)]">showing each item’s</span>
      <input
        aria-label={`Value ${index + 1} shown field`}
        spellCheck={false}
        placeholder="whole item"
        className={`${controlClass} w-32 font-mono text-[12.5px]`}
        value={field.show ?? ""}
        onChange={(e) => onChange({ ...field, show: e.target.value.trim() })}
      />
    </div>
  );
}

function FieldRow({
  field,
  index,
  lists,
  onChange,
  onRemove,
}: {
  field: AskField;
  index: number;
  lists: string[];
  onChange: (field: AskField) => void;
  onRemove: () => void;
}) {
  const setType = (type: AskField["type"]) =>
    onChange({
      ...field,
      type,
      default: null,
      options: type === "choice" ? (field.options ?? []) : undefined,
      items: type === "pick" ? (field.items ?? lists[0] ?? "") : undefined,
    });
  return (
    <div className={`${GRID} items-center`}>
      <input
        aria-label={`Value ${index + 1} name`}
        aria-invalid={!IDENTIFIER.test(field.name)}
        spellCheck={false}
        className={`${controlClass} min-w-0 font-mono text-[12.5px]`}
        value={field.name}
        onChange={(e) => onChange({ ...field, name: e.target.value.trim() })}
      />
      <input
        aria-label={`Value ${index + 1} label`}
        className={`${controlClass} min-w-0`}
        placeholder="e.g. Send it to"
        value={field.label}
        onChange={(e) => onChange({ ...field, label: e.target.value })}
      />
      <select
        aria-label={`Value ${index + 1} type`}
        className={`${controlClass} min-w-0`}
        value={field.type}
        onChange={(e) => setType(e.target.value as AskField["type"])}
      >
        {Object.entries(FIELD_TYPE_LABEL).map(([type, label]) => (
          <option key={type} value={type}>
            {label}
          </option>
        ))}
      </select>
      {field.type === "pick" ? (
        <span className="text-xs text-[var(--muted)]">None picked to begin with</span>
      ) : (
        <InputValueControl
          input={{ ...field, type: field.type, default: field.default ?? null }}
          label={`Value ${index + 1} default`}
          value={field.default ?? null}
          blank="No default"
          onChange={(value) => onChange({ ...field, default: value })}
        />
      )}
      <label className="flex justify-center">
        <input
          type="checkbox"
          aria-label={`${field.name || `Value ${index + 1}`} may be left blank`}
          className="h-4 w-4 accent-[var(--accent)]"
          checked={field.required === false}
          onChange={(e) => onChange({ ...field, required: !e.target.checked })}
        />
      </label>
      <RemoveButton label={`Remove value ${field.name || index + 1}`} onClick={onRemove} />
      {field.type === "choice" && (
        <div className="col-span-full pl-1">
          <AutoTextarea
            label={`Value ${index + 1} options`}
            placeholder="The options, one per line"
            value={(field.options ?? []).join("\n")}
            onChange={(text) => onChange({ ...field, options: text.split("\n") })}
          />
        </div>
      )}
      {field.type === "pick" && <PickFrom field={field} index={index} lists={lists} onChange={onChange} />}
    </div>
  );
}

function TimeoutFields({ step, onChange }: Omit<EditorProps<AskStep>, "context">) {
  const hours = step.timeout_hours ?? 0;
  const defaults = hasEveryDefault(step);
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <FieldLabel htmlFor={`${step.id}-timeout`}>If no one answers, wait</FieldLabel>
        <select
          id={`${step.id}-timeout`}
          className={inputClass}
          value={hours}
          onChange={(e) => {
            const next = Number(e.target.value);
            onChange(
              next > 0 ? { ...step, timeout_hours: next } : { ...step, timeout_hours: null, on_timeout: "fail" },
            );
          }}
        >
          {TIMEOUTS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
          {!TIMEOUTS.some((t) => t.value === hours) && <option value={hours}>{duration(hours * 60)}</option>}
        </select>
      </div>
      {hours > 0 && (
        <div>
          <FieldLabel htmlFor={`${step.id}-on-timeout`}>Then</FieldLabel>
          <select
            id={`${step.id}-on-timeout`}
            className={inputClass}
            value={step.on_timeout ?? "fail"}
            onChange={(e) => onChange({ ...step, on_timeout: e.target.value === "defaults" ? "defaults" : "fail" })}
          >
            <option value="fail">Stop the run</option>
            <option value="defaults" disabled={!defaults}>
              Go on with the defaults
            </option>
          </select>
        </div>
      )}
      <p className="basis-full text-xs text-[var(--muted)]">
        {hours > 0 && !defaults
          ? "Going on needs a default for every value that can’t be left blank."
          : "While it waits, the run holds nothing, and the app reminds you once a day."}
      </p>
    </div>
  );
}

export function AskEditor({ step, onChange, context }: EditorProps<AskStep>) {
  const lists = context.suggestions;
  const setField = (index: number, field: AskField) =>
    onChange({ ...step, fields: step.fields.map((f, i) => (i === index ? field : f)) });
  const invalid = step.fields.some((f) => !IDENTIFIER.test(f.name)) || !IDENTIFIER.test(step.save_as);
  return (
    <>
      <div>
        <FieldLabel htmlFor={`${step.id}-message`}>What to ask you</FieldLabel>
        <AutoTextarea
          id={`${step.id}-message`}
          placeholder="e.g. Who should this month’s summary go to?"
          value={step.message}
          onChange={(message) => onChange({ ...step, message })}
        />
        <ValuesHint context={context} />
      </div>
      <div className="flex flex-col gap-2 rounded-xl border border-[var(--border)] p-3">
        <div className={`${GRID} px-1 text-xs text-[var(--muted)]`}>
          <span>Name</span>
          <span>Shown as</span>
          <span>Kind</span>
          <span>Default</span>
          <span>Optional</span>
          <span />
        </div>
        {step.fields.map((field, index) => (
          <FieldRow
            key={index}
            field={field}
            index={index}
            lists={lists}
            onChange={(next) => setField(index, next)}
            onRemove={() => onChange({ ...step, fields: step.fields.filter((_, i) => i !== index) })}
          />
        ))}
        {step.fields.length < 12 && (
          <AddRowButton
            onClick={() =>
              onChange({
                ...step,
                fields: [...step.fields, { name: `value${step.fields.length + 1}`, label: "", type: "text" }],
              })
            }
          >
            Add a value
          </AddRowButton>
        )}
      </div>
      <div className="max-w-xs">
        <FieldLabel htmlFor={`${step.id}-save-as`}>Save the answers as</FieldLabel>
        <input
          id={`${step.id}-save-as`}
          spellCheck={false}
          className={`${inputClass} font-mono text-[12.5px]`}
          value={step.save_as}
          aria-invalid={!IDENTIFIER.test(step.save_as)}
          onChange={(e) => onChange({ ...step, save_as: e.target.value.trim() })}
        />
        <p className="mt-1 text-xs text-[var(--muted)]">
          Later steps read each one as <span className="font-mono">{`{{${step.save_as || "answers"}.name}}`}</span>.
        </p>
      </div>
      {invalid && (
        <p className="-mt-2 text-xs text-[var(--danger)]">
          Names use lowercase letters, digits and _, starting with a letter.
        </p>
      )}
      <TimeoutFields step={step} onChange={onChange} />
    </>
  );
}

const UNTIL_LABEL: Record<WaitStep["until"], string> = {
  duration: "For a while",
  time: "Until a time",
  file: "Until a file appears",
};

function WaitUntilFile({ step, onChange, context }: EditorProps<WaitStep>) {
  const max = step.max_minutes ?? 1440;
  return (
    <>
      <div>
        <FieldLabel htmlFor={`${step.id}-path`}>File</FieldLabel>
        <input
          id={`${step.id}-path`}
          spellCheck={false}
          className={`${inputClass} font-mono text-[12.5px]`}
          placeholder="e.g. shared/approved/{{month}}.xlsx"
          value={step.path ?? ""}
          onChange={(e) => onChange({ ...step, path: e.target.value })}
        />
        <ValuesHint context={context} />
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <FieldLabel htmlFor={`${step.id}-max`}>Wait at most (hours)</FieldLabel>
          <input
            id={`${step.id}-max`}
            type="number"
            min={0.5}
            max={168}
            step={0.5}
            className={`${inputClass} w-32`}
            value={max / 60}
            onChange={(e) => onChange({ ...step, max_minutes: minutesOf(e.target.value) })}
          />
        </div>
        <div>
          <FieldLabel htmlFor={`${step.id}-missing`}>If it doesn’t come</FieldLabel>
          <select
            id={`${step.id}-missing`}
            className={inputClass}
            value={step.if_missing ?? "fail"}
            onChange={(e) => onChange({ ...step, if_missing: e.target.value === "continue" ? "continue" : "fail" })}
          >
            <option value="fail">Stop the run</option>
            <option value="continue">Go on without it</option>
          </select>
        </div>
        <div>
          <FieldLabel htmlFor={`${step.id}-save-as`}>Save as</FieldLabel>
          <input
            id={`${step.id}-save-as`}
            spellCheck={false}
            placeholder="not saved"
            className={`${inputClass} w-40 font-mono text-[12.5px]`}
            value={step.save_as ?? ""}
            onChange={(e) => onChange({ ...step, save_as: e.target.value.trim() || null })}
          />
        </div>
      </div>
      <p className="-mt-2 text-xs text-[var(--muted)]">
        {duration(max)} at most. It goes on once the file is there and has stopped changing.
        {step.save_as && (
          <>
            {" "}
            Later steps read <span className="font-mono">{`{{${step.save_as}.found}}`}</span> and{" "}
            <span className="font-mono">{`{{${step.save_as}.path}}`}</span>.
          </>
        )}
      </p>
    </>
  );
}

/** Hours typed as minutes, within a week. */
function minutesOf(hours: string): number {
  return Math.max(1, Math.min(10080, Math.round((Number(hours) || 0) * 60)));
}

const SWITCH: Record<WaitStep["until"], Partial<WaitStep>> = {
  duration: { minutes: 10, at: null, on: null, path: null, save_as: null },
  time: { at: "17:00", minutes: null, path: null, save_as: null },
  file: { path: "", minutes: null, at: null, on: null, max_minutes: 1440 },
};

export function WaitEditor({ step, onChange, context }: EditorProps<WaitStep>) {
  return (
    <>
      <div role="radiogroup" aria-label="Wait" className="flex flex-wrap gap-1.5">
        {(Object.keys(UNTIL_LABEL) as WaitStep["until"][]).map((until) => (
          <button
            key={until}
            type="button"
            role="radio"
            aria-checked={step.until === until}
            className={`rounded-full border px-3 py-1 text-sm ${
              step.until === until
                ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--fg)]"
                : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
            onClick={() => step.until !== until && onChange({ ...step, ...SWITCH[until], until })}
          >
            {UNTIL_LABEL[until]}
          </button>
        ))}
      </div>
      {step.until === "duration" && (
        <div>
          <FieldLabel htmlFor={`${step.id}-minutes`}>Minutes</FieldLabel>
          <input
            id={`${step.id}-minutes`}
            type="number"
            min={1}
            max={10080}
            className={`${inputClass} w-32`}
            value={step.minutes ?? 10}
            onChange={(e) => onChange({ ...step, minutes: Math.max(1, Math.min(10080, Number(e.target.value) || 1)) })}
          />
          <p className="mt-1 text-xs text-[var(--muted)]">{duration(step.minutes ?? 10)}, at most a week.</p>
        </div>
      )}
      {step.until === "time" && (
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <FieldLabel htmlFor={`${step.id}-at`}>Time</FieldLabel>
            <input
              id={`${step.id}-at`}
              type="time"
              className={`${inputClass} w-32`}
              value={step.at ?? ""}
              onChange={(e) => onChange({ ...step, at: e.target.value })}
            />
          </div>
          <div>
            <FieldLabel htmlFor={`${step.id}-on`}>On</FieldLabel>
            <input
              id={`${step.id}-on`}
              spellCheck={false}
              list={context.listId}
              placeholder="the next time it comes"
              className={`${inputClass} w-56 font-mono text-[12.5px]`}
              value={step.on ?? ""}
              onChange={(e) => onChange({ ...step, on: e.target.value.trim() || null })}
            />
          </div>
          <p className="basis-full text-xs text-[var(--muted)]">
            Blank waits for the next time it’s that time. A day can be a date, “today”, or a date the run has, like an
            input.
          </p>
        </div>
      )}
      {step.until === "file" && <WaitUntilFile step={step} onChange={onChange} context={context} />}
      <p className="text-xs text-[var(--muted)]">
        While it waits, the run holds nothing. If Coscribe is closed, the run goes on when it next starts.
      </p>
    </>
  );
}
