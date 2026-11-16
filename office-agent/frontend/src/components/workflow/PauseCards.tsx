import { useState } from "react";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { untilWords } from "../../lib/pauseWords";
import type { WorkflowAskField, WorkflowPause } from "../../types/wire.gen";
import type { StepRecord } from "../../types/workflow";
import { InputValueControl } from "./InputValueControl";

// What a run shows at a step that paused it (decision 0033): the values an ask step waits for, or
// what a wait step waits for, with a way to go on early.

export type AnswerValues = Record<string, unknown>;

/** What the person sent for each value: a pick's items by their place in the list. */
function startingValues(fields: WorkflowAskField[]): AnswerValues {
  return Object.fromEntries(fields.map((f) => [f.name, f.type === "pick" ? [] : (f.default ?? null)]));
}

function missing(fields: WorkflowAskField[], values: AnswerValues): string[] {
  return fields
    .filter((f) => f.required)
    .filter((f) => {
      const value = values[f.name];
      return value === null || value === "" || (Array.isArray(value) && value.length === 0);
    })
    .map((f) => f.label || f.name);
}

function PickList({
  field,
  value,
  onChange,
}: {
  field: WorkflowAskField;
  value: number[];
  onChange: (value: number[]) => void;
}) {
  const items = field.items ?? [];
  const all = items.length > 0 && value.length === items.length;
  return (
    <div className="flex flex-col gap-1">
      <div className="max-h-56 overflow-y-auto rounded-md border border-[var(--border)] bg-[var(--bg)]">
        {items.map((item) => (
          <label
            key={item.index}
            className="flex items-center gap-2.5 border-b border-[var(--border)] px-2.5 py-1.5 text-sm last:border-b-0"
          >
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--accent)]"
              checked={value.includes(item.index)}
              onChange={(e) =>
                onChange(e.target.checked ? [...value, item.index] : value.filter((i) => i !== item.index))
              }
            />
            <span className="min-w-0 truncate">{item.label}</span>
          </label>
        ))}
        {items.length === 0 && <p className="px-2.5 py-2 text-sm text-[var(--muted)]">The list is empty.</p>}
      </div>
      {items.length > 1 && (
        <button
          type="button"
          className="self-start text-xs text-[var(--muted)] hover:text-[var(--fg)]"
          onClick={() => onChange(all ? [] : items.map((i) => i.index))}
        >
          {all ? "Clear" : `Pick all ${items.length}`} · {value.length} picked
        </button>
      )}
    </div>
  );
}

export function AskCard({
  record,
  pause,
  onAnswer,
}: {
  record: StepRecord | undefined;
  pause: WorkflowPause;
  onAnswer: (approved: boolean, note: string, values?: AnswerValues) => Promise<string | null>;
}) {
  const fields = pause.fields ?? [];
  const [values, setValues] = useState<AnswerValues>(() => startingValues(fields));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const gaps = missing(fields, values);
  const send = async (approved: boolean) => {
    setBusy(true);
    setError(await onAnswer(approved, "", approved ? values : undefined));
    setBusy(false);
  };
  return (
    <div className="flex flex-col gap-3" data-testid="ask-card">
      {typeof record?.output === "string" && <p className="whitespace-pre-wrap text-sm leading-relaxed">{record.output}</p>}
      <div className="flex flex-col gap-3">
        {fields.map((field) => (
          <label key={field.name} className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium">
              {field.label || field.name}
              {!field.required && <span className="font-normal text-[var(--muted)]"> · optional</span>}
            </span>
            {field.type === "pick" ? (
              <PickList
                field={field}
                value={(values[field.name] as number[]) ?? []}
                onChange={(next) => setValues({ ...values, [field.name]: next })}
              />
            ) : (
              <InputValueControl
                input={{ ...field, type: field.type, default: null }}
                label={field.label || field.name}
                value={(values[field.name] ?? null) as string | number | boolean | null}
                forRun
                onChange={(value) => setValues({ ...values, [field.name]: value })}
              />
            )}
          </label>
        ))}
      </div>
      {pause.until && (
        <p className="text-[13px] text-[var(--muted)]">
          If no one answers by {untilWords(pause.until)}, the run{" "}
          {pause.on_timeout === "defaults" ? "goes on with the defaults" : "stops"}.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" disabled={busy || gaps.length > 0} className={`${primaryButton} whitespace-nowrap`} onClick={() => send(true)}>
          Continue
        </button>
        <button type="button" disabled={busy} className={`${secondaryButton} whitespace-nowrap`} onClick={() => send(false)}>
          Stop the run
        </button>
        {gaps.length > 0 && <span className="text-xs text-[var(--muted)]">Still needed: {gaps.join(", ")}</span>}
      </div>
      {error && (
        <p role="alert" className="text-[13px] text-[var(--danger)]">
          {error}
        </p>
      )}
    </div>
  );
}

export function WaitCard({
  pause,
  onAnswer,
}: {
  pause: WorkflowPause;
  onAnswer: (approved: boolean, note: string) => Promise<string | null>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const goOn = async () => {
    setBusy(true);
    setError(await onAnswer(true, ""));
    setBusy(false);
  };
  return (
    <div className="flex flex-col gap-3" data-testid="wait-card">
      {pause.path ? (
        <p className="text-sm">
          Waiting for <span className="break-all font-mono text-[12.5px]">{pause.path}</span> to appear
          {pause.until ? `, until ${untilWords(pause.until)}` : ""}.
        </p>
      ) : (
        <p className="text-sm">Waiting until {pause.until ? untilWords(pause.until) : "it’s time"}.</p>
      )}
      <p className="text-[13px] text-[var(--muted)]">
        The run holds nothing while it waits. If Coscribe is closed, it goes on when it next starts.
      </p>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy} className={`${secondaryButton} whitespace-nowrap`} onClick={goOn}>
          {pause.path ? "Check now" : "Go on now"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-[13px] text-[var(--danger)]">
          {error}
        </p>
      )}
    </div>
  );
}
