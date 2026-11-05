import { inputClass } from "../../lib/formStyles";
import { givenInputs, useCallableTasks } from "../../lib/taskCalls";
import { IDENTIFIER } from "../../lib/workflowEdit";
import type { RunTaskStep } from "../../types/workflow";
import { type EditorProps, ValuesHint } from "./editorParts";
import { AutoTextarea, FieldLabel } from "./fields";
import { SelectMenu } from "../SelectMenu";

/** Which task a run-task step runs (decision 0035), the values it gives it, and the name its
 * results are read by. */
export function RunTaskEditor({ step, onChange, context }: EditorProps<RunTaskStep>) {
  const tasks = useCallableTasks();
  const task = tasks.find((t) => t.trigger_id === step.task);
  const saveAs = step.save_as ?? "";
  const nameInvalid = saveAs !== "" && !IDENTIFIER.test(saveAs);
  return (
    <>
      <div className="max-w-md">
        <FieldLabel htmlFor={`${step.id}-task`} hint="It runs as a whole, with its own approvals and memory">
          Task to run
        </FieldLabel>
        <SelectMenu
          id={`${step.id}-task`}
          variant="field"
          invalid={!task}
          value={step.task}
          placeholder={step.task ? "A task that's gone" : "Choose a task"}
          options={tasks.map((t) => ({ value: t.trigger_id, label: `${t.name} · version ${t.version ?? 1}` }))}
          onChange={(trigger) => onChange({ ...step, task: trigger, inputs: {} })}
        />
        {tasks.length === 0 && (
          <p className="mt-1 text-xs text-[var(--muted)]">Save another task with steps first; it shows up here.</p>
        )}
      </div>
      {task && givenInputs(step, task).length > 0 && (
        <div className="flex flex-col gap-2.5">
          {givenInputs(step, task).map(([name, label, value]) => {
            const asked = task.workflow?.inputs.find((input) => input.name === name);
            const optional = !asked || asked.required === false || (asked.default ?? "") !== "";
            return (
              <div key={name}>
                <FieldLabel htmlFor={`${step.id}-in-${name}`} hint={optional ? "Blank: its default" : undefined}>
                  {label}
                </FieldLabel>
                <AutoTextarea
                  id={`${step.id}-in-${name}`}
                  value={value}
                  onChange={(text) => {
                    const inputs = { ...step.inputs, [name]: text };
                    if (text === "") delete inputs[name];
                    onChange({ ...step, inputs });
                  }}
                />
              </div>
            );
          })}
          <ValuesHint context={context} />
        </div>
      )}
      <div className="max-w-xs">
        <FieldLabel htmlFor={`${step.id}-save-as`}>Save its results as</FieldLabel>
        <input
          id={`${step.id}-save-as`}
          spellCheck={false}
          className={`${inputClass} font-mono text-[12.5px]`}
          value={saveAs}
          aria-invalid={nameInvalid}
          placeholder="not saved"
          onChange={(e) => onChange({ ...step, save_as: e.target.value.trim() || null })}
        />
        <p className={`mt-1 text-xs ${nameInvalid ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>
          {nameInvalid
            ? "Lowercase letters, digits and _, starting with a letter."
            : task?.results?.length && saveAs
              ? `Later steps read ${task.results.map((r) => `{{${saveAs}.${r}}}`).join(", ")}`
              : "Renaming it updates the later steps that read it."}
        </p>
      </div>
    </>
  );
}
