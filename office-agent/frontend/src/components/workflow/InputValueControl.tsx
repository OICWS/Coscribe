import { controlClass } from "../../lib/formStyles";
import { isRelativeDate, RELATIVE_DATES, resolveDate } from "../../lib/inputKinds";
import type { WorkflowInput } from "../../types/workflow";

type Value = WorkflowInput["default"];

const FIXED = "fixed";

/** A date that is either worked out each run ("First day of last month") or a fixed day. */
function DateValue({
  value,
  onChange,
  label,
  blank,
}: {
  value: Value;
  onChange: (v: Value) => void;
  label: string;
  blank: string;
}) {
  const relative = isRelativeDate(value);
  const choice = value === null || value === "" ? "" : relative ? String(value) : FIXED;
  return (
    <div className="flex min-w-0 flex-wrap gap-2">
      <select
        aria-label={label}
        className={`${controlClass} min-w-0`}
        value={choice}
        onChange={(e) => onChange(e.target.value === FIXED ? resolveDate("today") : e.target.value || null)}
      >
        <option value="">{blank}</option>
        <optgroup label="Worked out each run">
          {RELATIVE_DATES.map(([id, text]) => (
            <option key={id} value={id}>
              {text}
            </option>
          ))}
        </optgroup>
        <option value={FIXED}>A fixed date</option>
      </select>
      {choice === FIXED && (
        <input
          type="date"
          aria-label={`${label}, fixed date`}
          className={`${controlClass} min-w-0`}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </div>
  );
}

function placeholderFor(input: WorkflowInput, forRun: boolean, blank: string): string | undefined {
  if (forRun && input.required === false) return "Can be left blank";
  if (input.type === "file") return "A path in the workspace, e.g. reports/march.pdf";
  if (input.type === "folder") return "A folder in the workspace, e.g. reports/2026";
  return forRun ? undefined : blank;
}

/** The control for an input's value, by its kind: its default in the editor, its value for a run. */
export function InputValueControl({
  input,
  value,
  onChange,
  label,
  forRun = false,
  blank = "Asked each run",
}: {
  input: WorkflowInput;
  value: Value;
  onChange: (value: Value) => void;
  label: string;
  /** A run needs a value, so a date is a date, not "worked out each run". */
  forRun?: boolean;
  /** What no default is called. */
  blank?: string;
}) {
  const className = `${controlClass} w-full min-w-0`;
  if (input.type === "date" && !forRun) return <DateValue value={value} onChange={onChange} label={label} blank={blank} />;
  if (input.type === "date") {
    return (
      <input
        type="date"
        aria-label={label}
        className={className}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (input.type === "choice") {
    return (
      <select
        aria-label={label}
        className={className}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value || null)}
      >
        <option value="">{forRun ? "Choose…" : blank}</option>
        {(input.options ?? []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  if (input.type === "yes_no") {
    const current = value === null || value === "" ? "" : value === true ? "yes" : "no";
    return (
      <select
        aria-label={label}
        className={className}
        value={current}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value === "yes")}
      >
        {!forRun && <option value="">{blank}</option>}
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    );
  }
  return (
    <input
      aria-label={label}
      className={className}
      type={input.type === "number" ? "number" : "text"}
      value={value === null ? "" : String(value)}
      placeholder={placeholderFor(input, forRun, blank)}
      onChange={(e) =>
        onChange(input.type === "number" && e.target.value !== "" ? Number(e.target.value) : e.target.value)
      }
    />
  );
}
