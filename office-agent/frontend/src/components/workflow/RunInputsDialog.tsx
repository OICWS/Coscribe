import { useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { startingValue } from "../../lib/inputKinds";
import type { WorkflowInput } from "../../types/workflow";
import { PlayIcon } from "../icons";
import { InputValueControl } from "./InputValueControl";
import { VarToken } from "./parts";

interface RunInputsDialogProps {
  taskName: string;
  inputs: WorkflowInput[];
  onCancel: () => void;
  onRun: (values: Record<string, unknown>) => void;
}

/** Run now for a workflow with inputs: the defaults, confirmed or changed
 * for this one run. */
export function RunInputsDialog({ taskName, inputs, onCancel, onRun }: RunInputsDialogProps) {
  const [values, setValues] = useState<Record<string, WorkflowInput["default"]>>(() =>
    Object.fromEntries(
      inputs.map((input) => {
        const start = startingValue(input);
        return [input.name, input.type === "yes_no" ? (start === "" ? null : start === "yes") : start];
      }),
    ),
  );
  const blank = (value: WorkflowInput["default"]) => value === null || String(value).trim() === "";
  const missing = inputs.filter((input) => input.required !== false && blank(values[input.name]));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (missing.length > 0) return;
    onRun(
      Object.fromEntries(
        inputs.map((input) => {
          const value = values[input.name];
          return [input.name, typeof value === "string" ? value.trim() : (value ?? "")];
        }),
      ),
    );
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <form
        className="w-[min(460px,100vw-2rem)] rounded-[16px] border border-[var(--border)] bg-[var(--panel-bg)] p-5 shadow-[var(--shadow)]"
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
      >
        <h2 className="text-base font-semibold">Run {taskName}</h2>
        <p className="mt-0.5 text-sm text-[var(--muted)]">These values are used for this run only.</p>
        <div className="mt-4 flex flex-col gap-3.5">
          {inputs.map((input) => (
            <label key={input.name} className="flex flex-col gap-1.5">
              {/* A long label pushes the name onto its own line instead of truncating it. */}
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                <span>{input.label || input.name}</span>
                <span className="shrink-0">
                  <VarToken name={input.name} isInput />
                </span>
                {input.required === false && <span className="text-xs text-[var(--muted)]">Optional</span>}
              </span>
              <InputValueControl
                input={input}
                forRun
                label={input.label || input.name}
                value={values[input.name] ?? null}
                onChange={(value) => setValues((prev) => ({ ...prev, [input.name]: value }))}
              />
            </label>
          ))}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            className="h-8 rounded-md border border-[var(--border)] px-3 text-sm hover:bg-[var(--card-bg)]"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={missing.length > 0}
            className="flex h-8 items-center gap-1.5 rounded-md bg-[var(--primary)] px-3 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
          >
            <PlayIcon className="h-3.5 w-3.5" /> Run
          </button>
        </div>
      </form>
    </div>,
    document.body,
  );
}
