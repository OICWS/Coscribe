import { inputClass } from "../../lib/formStyles";
import type { ApprovalStep, BranchStep, CheckStep, ChoiceStep, LoopStep } from "../../types/workflow";
import { ToggleSwitch } from "../ToggleSwitch";
import { ConditionsEditor } from "./ConditionRow";
import { type EditorProps, ValuesHint } from "./editorParts";
import { AddRowButton, AutoTextarea, FieldLabel, RemoveButton } from "./fields";
import { SelectMenu } from "../SelectMenu";

// The editors of the steps that decide something: a check, an approval's "only when", a branch, a
// choice and a loop that may stop early.

export function CheckEditor({ step, onChange, context }: EditorProps<CheckStep>) {
  const ends = step.otherwise === "end";
  return (
    <div className="flex flex-col gap-2">
      <FieldLabel
        hint={ends ? "If they don't hold, the run ends here as done" : "If they don't hold, the run stops here"}
      >
        Checks
      </FieldLabel>
      <ConditionsEditor
        conditions={step.conditions}
        match={step.match}
        onChange={(conditions, match) => onChange({ ...step, conditions, match })}
        valuesListId={context.listId}
        defaultReference={context.suggestions[0] ?? ""}
        label="Check"
        addLabel="Add a check"
      />
      {(context.topLevel || ends) && (
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          <label htmlFor={`${step.id}-otherwise`} className="text-[var(--muted)]">
            If they don't hold
          </label>
          <SelectMenu
            id={`${step.id}-otherwise`}
            variant="field"
            className="w-auto"
            value={step.otherwise ?? "fail"}
            options={[
              { value: "fail", label: "Stop the run (it failed)" },
              { value: "end", label: "End the run quietly (nothing to do)" },
            ]}
            onChange={(otherwise) => onChange({ ...step, otherwise })}
          />
          {ends && (
            <span className="text-xs text-[var(--muted)]">
              No notification; a row of such runs shows as one on the task page.
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function ApprovalEditor({ step, onChange, context }: EditorProps<ApprovalStep>) {
  const defaultReference = context.suggestions[0] ?? "";
  const conditional = step.when.length > 0;
  return (
    <>
      <div>
        <FieldLabel htmlFor={`${step.id}-message`}>What to show you</FieldLabel>
        <AutoTextarea
          id={`${step.id}-message`}
          value={step.message}
          onChange={(message) => onChange({ ...step, message })}
        />
        <ValuesHint context={context} />
      </div>
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2.5 text-sm">
          <ToggleSwitch
            on={conditional}
            label="Only pause when a condition holds"
            onClick={() =>
              onChange({
                ...step,
                when: conditional ? [] : [{ left: { ref: defaultReference }, op: "eq", right: { value: true } }],
              })
            }
          />
          Only pause when…
        </label>
        {conditional && (
          <ConditionsEditor
            conditions={step.when}
            match={step.match}
            onChange={(when, match) => onChange({ ...step, when, match })}
            valuesListId={context.listId}
            defaultReference={defaultReference}
            label="Condition"
            addLabel="Add a condition"
            emptyAllowed
          />
        )}
      </div>
    </>
  );
}

export function BranchEditor({ step, onChange, context }: EditorProps<BranchStep>) {
  return (
    <div className="flex flex-col gap-2">
      <FieldLabel hint="Its Then steps run when it holds; the Otherwise steps when it doesn't">
        {step.conditions.length > 1 ? "Conditions" : "Condition"}
      </FieldLabel>
      <ConditionsEditor
        conditions={step.conditions}
        match={step.match}
        onChange={(conditions, match) => onChange({ ...step, conditions, match })}
        valuesListId={context.listId}
        defaultReference={context.suggestions[0] ?? ""}
        label="Condition"
        addLabel="Add a condition"
      />
    </div>
  );
}

export function ChoiceEditor({ step, onChange, context }: EditorProps<ChoiceStep>) {
  const setCase = (index: number, is: string) =>
    onChange({ ...step, cases: step.cases.map((c, i) => (i === index ? { ...c, is } : c)) });
  return (
    <div className="flex flex-col gap-3">
      <div>
        <FieldLabel htmlFor={`${step.id}-value`} hint="The first path whose value it equals runs">
          Go by
        </FieldLabel>
        <input
          id={`${step.id}-value`}
          list={context.listId}
          spellCheck={false}
          aria-invalid={!step.value}
          className={`${inputClass} font-mono text-[12.5px]`}
          placeholder="a value, e.g. claim.category"
          value={step.value}
          onChange={(e) => onChange({ ...step, value: e.target.value.trim() })}
        />
      </div>
      <div className="flex flex-col gap-2">
        <FieldLabel>Paths</FieldLabel>
        {step.cases.map((c, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className="w-14 shrink-0 text-[13px] text-[var(--muted)]">Path {index + 1}</span>
            <span className="text-[13px] text-[var(--muted)]">when it is</span>
            <input
              aria-label={`Path ${index + 1} value`}
              className={`${inputClass} min-w-0 flex-1`}
              value={c.is}
              onChange={(e) => setCase(index, e.target.value)}
            />
            <RemoveButton
              label={`Remove path ${index + 1}`}
              onClick={() =>
                step.cases.length > 1 && onChange({ ...step, cases: step.cases.filter((_, i) => i !== index) })
              }
            />
          </div>
        ))}
        <AddRowButton onClick={() => onChange({ ...step, cases: [...step.cases, { is: "", steps: [] }] })}>
          Add a path
        </AddRowButton>
        <p className="text-xs text-[var(--muted)]">Anything else takes the Otherwise path.</p>
      </div>
    </div>
  );
}

export function LoopUntilEditor({ step, onChange, context }: EditorProps<LoopStep>) {
  const until = step.until ?? [];
  const defaultReference = context.suggestions[0] ?? "";
  return (
    <div className="flex flex-col gap-2">
      <label className="flex items-center gap-2.5 text-sm">
        <ToggleSwitch
          on={until.length > 0}
          label="Stop early when a condition holds"
          onClick={() =>
            onChange({
              ...step,
              until: until.length > 0 ? [] : [{ left: { ref: defaultReference }, op: "eq", right: { value: true } }],
            })
          }
        />
        Stop early when…
      </label>
      {until.length > 0 && (
        <ConditionsEditor
          conditions={until}
          match={step.match}
          onChange={(next, match) => onChange({ ...step, until: next, match })}
          valuesListId={context.listId}
          defaultReference={defaultReference}
          label="Stop condition"
          addLabel="Add a condition"
          emptyAllowed
        />
      )}
    </div>
  );
}
