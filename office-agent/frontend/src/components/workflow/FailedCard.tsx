import { useState } from "react";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { describeCheckResult, modelStepsRead, stepConditions } from "../../lib/workflowLabels";
import type { CheckResult, StepRecord, Workflow, WorkflowStep } from "../../types/workflow";
import { ConditionText } from "./parts";

// A step that stopped the run: what failed, where its bad values came from, and how to go on.

export interface FailedContext {
  workflow: Workflow;
  numbers: Map<string, number>;
  inputNames: Set<string>;
  onRetry: (stepId?: string) => Promise<string | null>;
  onEditStep: (stepId: string) => void;
}

function CheckLines({
  step,
  checks,
  inputNames,
}: {
  step: WorkflowStep;
  checks: CheckResult[];
  inputNames: Set<string>;
}) {
  const conditions = stepConditions(step);
  return (
    <ul className="flex flex-col gap-1.5 text-[13.5px]">
      {checks.map((check, index) => (
        <li key={index} className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <span
            aria-label={check.held ? "Held" : "Failed"}
            className="w-3 shrink-0 font-semibold"
            style={{ color: check.held ? "var(--success)" : "var(--danger)" }}
          >
            {check.held ? "✓" : "✕"}
          </span>
          {conditions[index] && <ConditionText condition={conditions[index]} inputNames={inputNames} />}
          {conditions[index] && (
            <span
              className={`tabular-nums ${check.held ? "text-[var(--muted)]" : "font-medium"}`}
              style={check.held ? undefined : { color: "var(--danger)" }}
            >
              {describeCheckResult(conditions[index].op, check.held, check.left, check.right)}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

function failureLabel(step: WorkflowStep): string {
  if (step.kind === "approval") return "Not approved";
  if (step.kind === "check") return "Check failed";
  return "Failed";
}

export function FailedCard({
  step,
  record,
  ctx,
}: {
  step: WorkflowStep;
  record: StepRecord | undefined;
  ctx: FailedContext;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const number = ctx.numbers.get(step.id) ?? 0;
  const source =
    step.kind === "check"
      ? modelStepsRead(ctx.workflow, step.conditions)
          .filter((s) => (ctx.numbers.get(s.id) ?? 0) < number)
          .pop()
      : undefined;
  const sourceNumber = source ? (ctx.numbers.get(source.id) ?? null) : null;
  const declined = step.kind === "approval";
  // A step of a task another step ran (decision 0035) is changed on that task's own page.
  const elsewhere = step.id.includes("/");
  const pass = record?.iteration?.length ? ` on item ${record.iteration[record.iteration.length - 1] + 1}` : "";

  const retry = async (stepId?: string) => {
    setBusy(true);
    setError(await ctx.onRetry(stepId));
    setBusy(false);
  };

  return (
    <div
      className="flex flex-col gap-3 rounded-xl border px-4 py-3.5"
      style={{
        borderColor: "color-mix(in srgb, var(--danger) 35%, transparent)",
        backgroundColor: "color-mix(in srgb, var(--danger) 6%, var(--bg))",
      }}
    >
      <div className="flex flex-wrap items-baseline gap-x-2.5">
        <span className="text-sm font-medium">{step.title}</span>
        <span className="text-[13px] font-medium" style={{ color: "var(--danger)" }}>
          {failureLabel(step)}
          {pass}
        </span>
      </div>
      {record?.checks && record.checks.length > 0 ? (
        <CheckLines step={step} checks={record.checks} inputNames={ctx.inputNames} />
      ) : (
        record?.error && (
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-[var(--fg)]">
            {record.error}
          </pre>
        )
      )}
      <p className="text-[13px] text-[var(--muted)]">
        {source
          ? `Those values came from step ${sourceNumber}, "${source.title}". Nothing after this check ran.`
          : "Nothing after this step ran."}
      </p>
      <div className="flex flex-wrap gap-2">
        {source && sourceNumber !== null ? (
          <>
            <button type="button" disabled={busy} className={primaryButton} onClick={() => retry(source.id)}>
              Retry from step {sourceNumber}
            </button>
            <button type="button" className={secondaryButton} onClick={() => ctx.onEditStep(source.id)}>
              Edit step {sourceNumber}
            </button>
            <button type="button" className={secondaryButton} onClick={() => ctx.onEditStep(step.id)}>
              Edit this check
            </button>
          </>
        ) : (
          <>
            <button type="button" disabled={busy} className={primaryButton} onClick={() => retry(step.id)}>
              {declined ? "Ask again" : "Retry this step"}
            </button>
            {elsewhere ? (
              <span className="self-center text-[13px] text-[var(--muted)]">
                To change it, open the task it belongs to.
              </span>
            ) : (
              <button type="button" className={secondaryButton} onClick={() => ctx.onEditStep(step.id)}>
                Edit step {number}
              </button>
            )}
          </>
        )}
      </div>
      {error && (
        <p role="alert" className="text-[13px] text-[var(--danger)]">
          {error}
        </p>
      )}
    </div>
  );
}
