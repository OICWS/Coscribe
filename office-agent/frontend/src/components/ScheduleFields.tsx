import { useState } from "react";
import { everyWords } from "../lib/scheduleLabels";
import { fileInputs, type ScheduleForm } from "../lib/scheduleForm";
import type { ScheduleKind } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { ConnectorTriggerFields } from "./ConnectorTriggerFields";
import { SelectMenu } from "./SelectMenu";
import { DirBrowserModal } from "./settings/DirBrowserModal";
import { WebhookTriggerFields } from "./WebhookTriggerFields";

// When a task runs: the Frequency row of the create/edit form. Besides the clock, a workflow task
// can run every few minutes or when a file arrives in a folder (decision 0034), when something
// new shows up in a connector (decision 0039), or when a program sends it an event (decision 0040).

const FREQUENCY_OPTIONS: { value: ScheduleKind; label: string }[] = [
  { value: "manual", label: "Manual" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekdays", label: "Weekdays" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const WORKFLOW_OPTIONS: { value: ScheduleKind; label: string }[] = [
  { value: "every", label: "Every few minutes" },
  { value: "folder", label: "When a file arrives in a folder" },
  { value: "connector", label: "When something new shows up in a connector" },
  { value: "webhook", label: "When a program sends it an event" },
];

const EVERY_MINUTES = [5, 10, 15, 30, 60, 120, 240, 480, 720, 1440];

// Display order is Sunday first (JS Date.getDay() order); `value` is ScheduleRule.weekday's own
// convention (0=Monday..6=Sunday), so this table bridges the two.
const WEEKDAY_OPTIONS: { label: string; value: number }[] = [
  { label: "Sunday", value: 6 },
  { label: "Monday", value: 0 },
  { label: "Tuesday", value: 1 },
  { label: "Wednesday", value: 2 },
  { label: "Thursday", value: 3 },
  { label: "Friday", value: 4 },
  { label: "Saturday", value: 5 },
];

const control = "rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-sm outline-none";

function FolderFields({
  form,
  onChange,
  inputs,
}: {
  form: ScheduleForm;
  onChange: (f: ScheduleForm) => void;
  inputs: string[];
}) {
  const [browsing, setBrowsing] = useState(false);
  return (
    <div className="flex w-full flex-col gap-2 pl-[6.5rem]">
      <div className="flex gap-2">
        <input
          aria-label="Folder to watch"
          className={`${control} min-w-0 flex-1`}
          placeholder="C:\Users\you\Downloads\Invoices"
          value={form.folder}
          onChange={(e) => onChange({ ...form, folder: e.target.value })}
        />
        <button
          type="button"
          className="rounded-md border border-[var(--border)] px-3 text-sm hover:bg-[var(--card-bg)]"
          onClick={() => setBrowsing(true)}
        >
          Choose…
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-[var(--muted)]">Only files named like</span>
        <input
          aria-label="File name pattern"
          className={`${control} w-28 font-mono text-[12.5px]`}
          placeholder="*.pdf"
          value={form.pattern}
          onChange={(e) => onChange({ ...form, pattern: e.target.value })}
        />
        {inputs.length > 1 && (
          <>
            <span className="text-[var(--muted)]">given to</span>
            <SelectMenu
              ariaLabel="Input the file goes to"
              variant="field"
              className="w-40"
              value={form.input || inputs[0]}
              options={inputs.map((name) => ({ value: name, label: name }))}
              onChange={(input) => onChange({ ...form, input })}
            />
          </>
        )}
      </div>
      <p className="text-xs text-[var(--muted)]">
        Each new file starts one run, once it has finished writing. Files already there are left alone; ones that arrive
        while Coscribe is closed run when it starts.
      </p>
      {browsing && (
        <DirBrowserModal
          onSelect={(folder) => {
            onChange({ ...form, folder });
            setBrowsing(false);
          }}
          onClose={() => setBrowsing(false)}
        />
      )}
    </div>
  );
}

/** Frequency and the controls that kind of schedule needs. */
export function FrequencyRow({
  form,
  onChange,
  workflow,
  taskId,
}: {
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
  workflow: Workflow | null;
  /** The task being edited, for what only a saved task has (a webhook's address). */
  taskId?: string;
}) {
  const inputs = fileInputs(workflow);
  const options = [...FREQUENCY_OPTIONS, ...(workflow ? WORKFLOW_OPTIONS : [])];
  const set = (changes: Partial<ScheduleForm>) => onChange({ ...form, ...changes });
  const timeInput = (
    <input type="time" className={control} value={form.time} onChange={(e) => set({ time: e.target.value })} />
  );
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* w-24 keeps the Frequency and Permissions controls' left edges aligned. */}
      <label className="w-24 shrink-0 text-sm font-medium">Frequency</label>
      <SelectMenu
        ariaLabel="Frequency"
        variant="field"
        className="w-72"
        value={form.kind}
        options={options.map((opt) => {
          const needsInput = opt.value === "folder" && inputs.length === 0;
          return { ...opt, disabled: needsInput, label: needsInput ? `${opt.label} (needs a file input)` : opt.label };
        })}
        onChange={(kind) => set({ kind })}
      />
      {(form.kind === "daily" || form.kind === "weekdays" || form.kind === "weekly") && timeInput}
      {form.kind === "weekly" && (
        <SelectMenu
          ariaLabel="Weekday"
          variant="field"
          className="w-36"
          value={form.weekday}
          options={WEEKDAY_OPTIONS}
          onChange={(weekday) => set({ weekday })}
        />
      )}
      {form.kind === "monthly" && (
        <>
          <span className="text-sm text-[var(--muted)]">starts on</span>
          <input type="date" className={control} value={form.date} onChange={(e) => set({ date: e.target.value })} />
          {timeInput}
        </>
      )}
      {(form.kind === "every" || form.kind === "connector") && (
        <SelectMenu
          ariaLabel="How often"
          variant="field"
          className="w-36"
          value={form.minutes}
          options={[...new Set([...EVERY_MINUTES, form.minutes])]
            .sort((a, b) => a - b)
            .map((minutes) => ({ value: minutes, label: minutes === 60 ? "1 hour" : everyWords(minutes) }))}
          onChange={(minutes) => set({ minutes })}
        />
      )}
      {form.kind === "every" && (
        <p className="w-full pl-[6.5rem] text-xs text-[var(--muted)]">
          For a task that checks for something new: end it with a check that ends the run quietly when there is nothing,
          so only real runs notify you.
        </p>
      )}
      {form.kind === "folder" && <FolderFields form={form} onChange={onChange} inputs={inputs} />}
      {form.kind === "connector" && <ConnectorTriggerFields form={form} onChange={onChange} workflow={workflow} />}
      {form.kind === "webhook" && (
        <WebhookTriggerFields form={form} onChange={onChange} workflow={workflow} taskId={taskId} />
      )}
    </div>
  );
}
