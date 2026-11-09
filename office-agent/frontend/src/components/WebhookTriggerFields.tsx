import { useState } from "react";
import { matchingField } from "../lib/itemFields";
import type { ScheduleForm } from "../lib/scheduleForm";
import type { Workflow } from "../types/workflow";
import { InputsFromItem, PerHour } from "./ItemInputs";
import { WebhookAddress } from "./WebhookAddress";

/** The controls a "webhook" schedule needs, under the Frequency row (decision 0040): where events
 * go once the task is saved, the hourly limit, and which of the workflow's inputs each event's
 * fields fill in. */
export function WebhookTriggerFields({
  form,
  onChange,
  workflow,
  taskId,
}: {
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
  workflow: Workflow | null;
  /** The task being edited; a new one has no address until it is saved. */
  taskId?: string;
}) {
  const [fields, setFields] = useState<Record<string, unknown>>({});
  const inputs = workflow?.inputs ?? [];
  const sampled = (found: Record<string, unknown>) => {
    setFields(found);
    // A sample names the fields: an input not picked yet takes the one named like it.
    const paths = Object.keys(found);
    if (paths.length === 0) return;
    const picked = Object.fromEntries(inputs.map((input) => [input.name, matchingField(input, paths)]));
    onChange({ ...form, inputsFrom: { ...picked, ...form.inputsFrom } });
  };
  return (
    <div className="flex w-full flex-col gap-2.5 pl-[6.5rem]">
      {taskId ? (
        <WebhookAddress taskId={taskId} inputs={inputs} onInfo={(info) => sampled(info.fields ?? {})} />
      ) : (
        <p className="text-sm text-[var(--muted)]">
          Save the task to get its address and key. A program on this computer, such as a PowerShell script or a Power
          Automate flow, then sends it events as JSON.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <PerHour form={form} onChange={onChange} />
      </div>
      {inputs.length > 0 && (
        <InputsFromItem what="event" inputs={inputs} fields={fields} form={form} onChange={onChange} />
      )}
      <p className="text-xs text-[var(--muted)]">
        Each event starts one run. At most 3 run at once; an event over the limits, or one that doesn't fit the inputs,
        is refused and the program is told why.
      </p>
    </div>
  );
}
