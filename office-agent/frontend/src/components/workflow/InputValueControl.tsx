import { controlClass } from "../../lib/formStyles";
import { isRelativeDate, RELATIVE_DATES, resolveDate } from "../../lib/inputKinds";
import type { WorkflowInput } from "../../types/workflow";
import { SelectMenu } from "../SelectMenu";

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
      <SelectMenu
        ariaLabel={label}
        variant="field"
        value={choice}
        options={[
          { value: "", label: blank },
          ...RELATIVE_DATES.map(([id, text]) => ({ value: id, label: text, group: "Worked out each run" })),
          { value: FIXED, label: "A fixed date" },
        ]}
        onChange={(picked) => onChange(picked === FIXED ? resolveDate("today") : picked || null)}
      />
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
      <SelectMenu
        ariaLabel={label}
        variant="field"
        className="w-full"
        value={String(value ?? "")}
        options={[{ value: "", label: forRun ? "Choose…" : blank }, ...(input.options ?? []).map((option) => ({ value: option, label: option }))]}
        onChange={(picked) => onChange(picked || null)}
      />
    );
  }
  if (input.type === "yes_no") {
    const current = value === null || value === "" ? "" : value === true ? "yes" : "no";
    return (
      <SelectMenu
        ariaLabel={label}
        variant="field"
        className="w-full"
        value={current}
        options={[...(forRun ? [] : [{ value: "", label: blank }]), { value: "yes", label: "Yes" }, { value: "no", label: "No" }]}
        onChange={(picked) => onChange(picked === "" ? null : picked === "yes")}
      />
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
