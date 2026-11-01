import { controlClass } from "../../lib/formStyles";
import { OP_LABEL, operandReference, UNARY_OPS } from "../../lib/workflowLabels";
import type { CheckOp, Condition, Match, Operand } from "../../types/workflow";
import { AddRowButton, RemoveButton } from "./fields";

type OperandMode = "ref" | "count" | "value";
type LiteralType = "text" | "number" | "boolean";

const MODE_LABEL: Record<OperandMode, string> = { ref: "Value of", count: "Count of", value: "Fixed" };
const OPS = Object.keys(OP_LABEL) as CheckOp[];

function modeOf(operand: Operand): OperandMode {
  if ("ref" in operand) return "ref";
  if ("count" in operand) return "count";
  return "value";
}

function literalTypeOf(value: unknown): LiteralType {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  return "text";
}

function OperandEditor({
  operand,
  onChange,
  valuesListId,
  label,
  defaultReference,
}: {
  operand: Operand;
  onChange: (operand: Operand) => void;
  valuesListId: string;
  label: string;
  defaultReference: string;
}) {
  const mode = modeOf(operand);
  const setMode = (next: OperandMode) => {
    if (next === mode) return;
    if (next === "value") {
      onChange({ value: "" });
      return;
    }
    const reference = operandReference(operand) ?? defaultReference;
    onChange(next === "ref" ? { ref: reference } : { count: reference });
  };

  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <select
        aria-label={`${label}: kind`}
        className={`${controlClass} py-1 text-[13px]`}
        value={mode}
        onChange={(e) => setMode(e.target.value as OperandMode)}
      >
        {(Object.keys(MODE_LABEL) as OperandMode[]).map((key) => (
          <option key={key} value={key}>
            {MODE_LABEL[key]}
          </option>
        ))}
      </select>
      {"value" in operand ? (
        <LiteralEditor value={operand.value} label={label} onChange={(value) => onChange({ value })} />
      ) : (
        <input
          aria-label={`${label}: name`}
          list={valuesListId}
          spellCheck={false}
          className={`${controlClass} w-44 py-1 font-mono text-[12.5px]`}
          placeholder="name or name.field"
          value={operandReference(operand) ?? ""}
          onChange={(e) => onChange(mode === "ref" ? { ref: e.target.value.trim() } : { count: e.target.value.trim() })}
        />
      )}
    </span>
  );
}

function LiteralEditor({
  value,
  label,
  onChange,
}: {
  value: unknown;
  label: string;
  onChange: (value: unknown) => void;
}) {
  const type = literalTypeOf(value);
  const setType = (next: LiteralType) => {
    if (next === "boolean") onChange(true);
    else if (next === "number") onChange(Number(value) || 0);
    else onChange(String(value ?? ""));
  };
  return (
    <>
      <select
        aria-label={`${label}: type`}
        className={`${controlClass} py-1 text-[13px]`}
        value={type}
        onChange={(e) => setType(e.target.value as LiteralType)}
      >
        <option value="text">text</option>
        <option value="number">number</option>
        <option value="boolean">yes / no</option>
      </select>
      {type === "boolean" && (
        <select
          aria-label={`${label}: value`}
          className={`${controlClass} py-1 text-[13px]`}
          value={value ? "yes" : "no"}
          onChange={(e) => onChange(e.target.value === "yes")}
        >
          <option value="yes">yes</option>
          <option value="no">no</option>
        </select>
      )}
      {type === "number" && (
        <input
          aria-label={`${label}: value`}
          type="number"
          className={`${controlClass} w-24 py-1`}
          value={String(value)}
          onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
        />
      )}
      {type === "text" && (
        <input
          aria-label={`${label}: value`}
          className={`${controlClass} w-36 py-1`}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </>
  );
}

/** One editable comparison: two operands and how they must relate. */
function ConditionRow({
  condition,
  onChange,
  onRemove,
  valuesListId,
  label,
  defaultReference,
}: {
  condition: Condition;
  onChange: (condition: Condition) => void;
  onRemove?: () => void;
  valuesListId: string;
  label: string;
  defaultReference: string;
}) {
  const setOp = (op: CheckOp) => {
    if (UNARY_OPS.has(op)) onChange({ ...condition, op, right: null });
    else onChange({ ...condition, op, right: condition.right ?? { value: "" } });
  };
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--border)] px-3 py-2">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1.5 text-sm">
        <OperandEditor
          operand={condition.left}
          onChange={(left) => onChange({ ...condition, left })}
          valuesListId={valuesListId}
          label={`${label}, left`}
          defaultReference={defaultReference}
        />
        <select
          aria-label={`${label}: comparison`}
          className={`${controlClass} py-1`}
          value={condition.op}
          onChange={(e) => setOp(e.target.value as CheckOp)}
        >
          {OPS.map((op) => (
            <option key={op} value={op}>
              {OP_LABEL[op]}
            </option>
          ))}
        </select>
        {condition.right && (
          <OperandEditor
            operand={condition.right}
            onChange={(right) => onChange({ ...condition, right })}
            valuesListId={valuesListId}
            label={`${label}, right`}
            defaultReference={defaultReference}
          />
        )}
      </div>
      {onRemove && <RemoveButton label={`Remove ${label.toLowerCase()}`} onClick={onRemove} />}
    </div>
  );
}

/** A list of conditions and whether all must hold or one is enough. */
export function ConditionsEditor({
  conditions,
  match,
  onChange,
  valuesListId,
  defaultReference,
  label,
  addLabel,
  emptyAllowed = false,
}: {
  conditions: Condition[];
  match: Match | undefined;
  onChange: (conditions: Condition[], match: Match) => void;
  valuesListId: string;
  defaultReference: string;
  /** Names each row: "Condition 1". */
  label: string;
  addLabel: string;
  /** May the last one be removed (an approval that always asks, a loop that never stops early)? */
  emptyAllowed?: boolean;
}) {
  const current: Match = match ?? "all";
  const set = (next: Condition[]) => onChange(next, current);
  return (
    <div className="flex flex-col gap-2">
      {conditions.length > 1 && (
        <div role="radiogroup" aria-label={`${label}: how many must hold`} className="flex gap-1 text-[13px]">
          {(["all", "any"] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={current === value}
              className={`rounded-md px-2.5 py-1 ${
                current === value
                  ? "bg-[var(--card-bg)] font-medium text-[var(--fg)]"
                  : "text-[var(--muted)] hover:text-[var(--fg)]"
              }`}
              onClick={() => onChange(conditions, value)}
            >
              {value === "all" ? "All of these" : "Any of these"}
            </button>
          ))}
        </div>
      )}
      {conditions.map((condition, index) => (
        <ConditionRow
          key={index}
          label={`${label} ${index + 1}`}
          condition={condition}
          valuesListId={valuesListId}
          defaultReference={defaultReference}
          onChange={(next) => set(conditions.map((c, i) => (i === index ? next : c)))}
          onRemove={
            conditions.length > 1 || emptyAllowed ? () => set(conditions.filter((_, i) => i !== index)) : undefined
          }
        />
      ))}
      <AddRowButton
        onClick={() => set([...conditions, { left: { ref: defaultReference }, op: "eq", right: { value: "" } }])}
      >
        {addLabel}
      </AddRowButton>
    </div>
  );
}
