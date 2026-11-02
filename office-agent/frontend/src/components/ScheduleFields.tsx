import { useState } from "react";
import { everyWords } from "../lib/scheduleLabels";
import { fileInputs, type ScheduleForm } from "../lib/scheduleForm";
import type { ScheduleKind } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { DirBrowserModal } from "./settings/DirBrowserModal";

// When a task runs: the Frequency row of the create/edit form. Besides the clock, a workflow task
// can run every few minutes or when a file arrives in a folder (decision 0034).

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
            <select
              aria-label="Input the file goes to"
              className={control}
              value={form.input || inputs[0]}
              onChange={(e) => onChange({ ...form, input: e.target.value })}
            >
              {inputs.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
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
}: {
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
  workflow: Workflow | null;
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
      <select
        aria-label="Frequency"
        className={control}
        value={form.kind}
        onChange={(e) => set({ kind: e.target.value as ScheduleKind })}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.value === "folder" && inputs.length === 0}>
            {opt.label}
            {opt.value === "folder" && inputs.length === 0 ? " (needs a file input)" : ""}
          </option>
        ))}
      </select>
      {(form.kind === "daily" || form.kind === "weekdays" || form.kind === "weekly") && timeInput}
      {form.kind === "weekly" && (
        <select
          aria-label="Weekday"
          className={control}
          value={form.weekday}
          onChange={(e) => set({ weekday: Number(e.target.value) })}
        >
          {WEEKDAY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}
      {form.kind === "monthly" && (
        <>
          <span className="text-sm text-[var(--muted)]">starts on</span>
          <input type="date" className={control} value={form.date} onChange={(e) => set({ date: e.target.value })} />
          {timeInput}
        </>
      )}
      {form.kind === "every" && (
        <select
          aria-label="How often"
          className={control}
          value={form.minutes}
          onChange={(e) => set({ minutes: Number(e.target.value) })}
        >
          {[...new Set([...EVERY_MINUTES, form.minutes])]
            .sort((a, b) => a - b)
            .map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes === 60 ? "1 hour" : everyWords(minutes)}
              </option>
            ))}
        </select>
      )}
      {form.kind === "every" && (
        <p className="w-full pl-[6.5rem] text-xs text-[var(--muted)]">
          For a task that checks for something new: end it with a check that ends the run quietly when there is nothing,
          so only real runs notify you.
        </p>
      )}
      {form.kind === "folder" && <FolderFields form={form} onChange={onChange} inputs={inputs} />}
    </div>
  );
}
