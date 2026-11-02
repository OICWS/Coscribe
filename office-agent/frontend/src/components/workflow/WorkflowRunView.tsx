import { useEffect, useState, type ReactNode } from "react";
import { capitalize, formatRunTime, runDuration, runSourceLabel } from "../../lib/runLabels";
import {
  describeCheckResult,
  formatValue,
  agentUsage,
  KIND_COLOR,
  KIND_LABEL,
  stepDuration,
  summarizeOutput,
} from "../../lib/workflowLabels";
import type { ScheduledRun, ScheduledTask } from "../../types/settings";
import {
  loopProgress,
  passStatus,
  recordKey,
  recordMap,
  stoppedInside,
  type LoopProgress,
} from "../../lib/workflowProgress";
import { passShowing } from "../../lib/workflowRunMap";
import { canRecover, everyStep, placeSteps } from "../../lib/workflowTree";
import type { LoopStep, StepRecord, Workflow, WorkflowStep } from "../../types/workflow";
import { CheckIcon, ChevronDownIcon, ClockIcon, SparkIcon, StopIcon } from "../icons";
import { VarToken } from "./parts";
import { Screenshot } from "./Screenshot";
import { InvestigationLink, WAITING_FOR_BROWSER } from "./InvestigationLink";
import { StepOutput } from "./StepOutput";
import { AgentToolsUsed } from "./AgentActivity";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { WaitingCard } from "./WaitingCard";
import { FailedCard, type FailedContext } from "./FailedCard";
import { RunReportCard } from "./RunReportCard";
import { StatusDot } from "./StatusDot";
import { ViewToggle } from "./ViewToggle";
import { WorkflowCanvas } from "./WorkflowCanvas";

type RowStatus = StepRecord["status"] | "not_reached" | "stopped" | "recovered";

const RUNNING_LABEL: Partial<Record<WorkflowStep["kind"], string>> = {
  llm: "Asking the model…",
  agent: "Working on it…",
};

interface RunContext extends FailedContext {
  run: ScheduledRun;
  records: Map<string, StepRecord>;
  onAnswer: (approved: boolean, note: string) => Promise<string | null>;
  /** The step picked on the run's canvas: loops open on a pass it ran in. */
  focus: string | null;
}

function branchArm(record: StepRecord | undefined): "then" | "otherwise" | null {
  const arm = (record?.output as { arm?: string } | null | undefined)?.arm;
  return arm === "then" || arm === "otherwise" ? arm : null;
}

function triesWords(record: StepRecord | undefined): string {
  const attempts = record?.attempts ?? 1;
  return attempts > 1 ? ` · after ${attempts} tries` : "";
}

const RECOVERED_SUMMARY: Record<NonNullable<StepRecord["recovered"]>, string> = {
  skipped: "Failed, skipped",
  fallback: "Failed, ran other steps in its place",
  item_skipped: "Failed, this item was skipped",
};

function rowSummary(step: WorkflowStep, record: StepRecord | undefined, status: RowStatus): string {
  if (status === "recovered" && record?.recovered) return `${RECOVERED_SUMMARY[record.recovered]}${triesWords(record)}`;
  if (status === "not_reached") return "Not reached";
  if (status === "pending") return "Up next";
  if (status === "stopped") return "Stopped here";
  if (step.kind === "loop") {
    const progress = loopProgress(record);
    if (!progress) return status === "running" ? "Starting…" : "";
    const items = `${progress.total} ${progress.total === 1 ? "item" : "items"}`;
    const skipped = progress.skipped.length ? ` · ${progress.skipped.length} skipped` : "";
    if (status === "done") return `Went through ${items}${skipped}`;
    if (status === "failed") return `Stopped at item ${progress.done + 1} of ${progress.total}`;
    if (status === "waiting") return `Waiting at item ${progress.done + 1} of ${progress.total}`;
    return `${progress.done} of ${items} done`;
  }
  if (status === "running" && record?.error) return `${record.error} · trying again`;
  if (status === "running" && (record?.attempts ?? 1) > 1) return `Try ${record?.attempts}…`;
  if (status === "running") return RUNNING_LABEL[step.kind] ?? "Running…";
  if (status === "failed") return "Stopped inside";
  if (status === "waiting") return "Waiting inside";
  if (status === "skipped") return "Skipped · its condition didn't hold";
  if (step.kind === "branch" && record?.checks?.length) {
    const first = record.checks[0];
    const arm = branchArm(record) === "then" ? "Took Then" : "Took Otherwise";
    return `${arm} · ${describeCheckResult(step.conditions[0].op, first.held, first.left, first.right)}`;
  }
  if (step.kind === "choice") {
    const arm = (record?.output as { arm?: string } | null | undefined)?.arm ?? "";
    const index = arm.startsWith("case:") ? Number(arm.slice(5)) : -1;
    return index >= 0 && step.cases[index] ? `Took path ${index + 1} · “${step.cases[index].is}”` : "Took Otherwise";
  }
  if (step.kind === "check" && record?.checks?.length) {
    const first = record.checks[0];
    return `Passed · ${describeCheckResult(step.conditions[0].op, true, first.left, first.right)}`;
  }
  if (step.kind === "approval") return record?.note ? `Approved · “${record.note}”` : "Approved";
  const usage = step.kind === "agent" ? agentUsage(record?.agent) : null;
  const summary = usage ? `${usage} · ${summarizeOutput(record?.output)}` : summarizeOutput(record?.output);
  const attempts = record?.attempts ?? 1;
  return attempts > 1 ? `Worked on try ${attempts} · ${summary}` : summary;
}

function Nested({
  label,
  color,
  note,
  children,
}: {
  label: string;
  color: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <section
      aria-label={label}
      className="rounded-lg border-l-2 py-2 pl-3 pr-2"
      style={{
        borderLeftColor: `color-mix(in srgb, ${color} 55%, transparent)`,
        backgroundColor: `color-mix(in srgb, ${color} 4%, transparent)`,
      }}
    >
      <div className="mb-2 flex items-baseline gap-2 text-xs">
        <span className="font-semibold uppercase tracking-[0.08em]" style={{ color }}>
          {label}
        </span>
        {note && <span className="min-w-0 truncate text-[var(--muted)]">{note}</span>}
      </div>
      {children}
    </section>
  );
}

function stepCount(steps: WorkflowStep[]): string {
  const count = placeSteps(steps).length;
  return `${count} ${count === 1 ? "step" : "steps"}`;
}

interface RunArm {
  arm: string;
  label: string;
  steps: WorkflowStep[];
}

/** The lists under a branch, a choice or a step with steps in its place, by the record's arm. */
function runArms(
  step: WorkflowStep,
  record: StepRecord | undefined,
): { arms: RunArm[]; taken: string | null; color: string; idle: string } | null {
  const arm = (record?.output as { arm?: string } | null | undefined)?.arm ?? null;
  const decided = record?.status === "done" ? arm : null;
  if (step.kind === "branch") {
    return {
      arms: [
        { arm: "then", label: "Then", steps: step.then },
        { arm: "otherwise", label: "Otherwise", steps: step.otherwise },
      ],
      taken: decided,
      color: KIND_COLOR.branch,
      idle: decided ? "not taken" : "not decided yet",
    };
  }
  if (step.kind === "choice") {
    return {
      arms: [
        ...step.cases.map((c, index) => ({ arm: `case:${index}`, label: `Is “${c.is}”`, steps: c.steps })),
        { arm: "otherwise", label: "Anything else", steps: step.otherwise },
      ],
      taken: decided,
      color: KIND_COLOR.choice,
      idle: decided ? "not taken" : "not decided yet",
    };
  }
  if (canRecover(step) && step.on_failure?.then === "steps") {
    const ran = record?.recovered === "fallback";
    return {
      arms: [{ arm: "fallback", label: "If it fails", steps: step.on_failure.steps }],
      taken: ran ? "fallback" : null,
      color: "var(--warning)",
      idle: record?.status === "done" ? "not needed" : "only if it fails",
    };
  }
  return null;
}

function RunArms({
  step,
  record,
  path,
  ctx,
}: {
  step: WorkflowStep;
  record: StepRecord | undefined;
  path: number[];
  ctx: RunContext;
}) {
  const shape = runArms(step, record);
  if (!shape) return null;
  return (
    <div className="flex flex-col gap-2">
      {shape.arms.map(({ arm, label, steps }) => {
        if (shape.taken === arm) {
          return (
            <Nested key={arm} label={label} color={shape.color}>
              {steps.length > 0 ? (
                <RunList steps={steps} path={path} ctx={ctx} />
              ) : (
                <p className="text-[13px] text-[var(--muted)]">Nothing to do here.</p>
              )}
            </Nested>
          );
        }
        return (
          <p key={arm} className="flex items-baseline gap-2 pl-3.5 text-[13px] text-[var(--muted)]">
            <span className="text-xs font-semibold uppercase tracking-[0.08em]">{label}</span>
            <span>
              {stepCount(steps)} · {shape.idle}
            </span>
          </p>
        );
      })}
    </div>
  );
}

const PASS_TINT: Record<string, string> = {
  done: "var(--success)",
  failed: "var(--danger)",
  waiting: "var(--warning)",
  running: "var(--accent)",
  recovered: "var(--warning)",
};

function defaultPass(step: LoopStep, path: number[], progress: LoopProgress, ctx: RunContext): number {
  let latest = 0;
  for (let index = 0; index < progress.total; index++) {
    const status = passStatus(step, [...path, index], ctx.records);
    if (status === "failed" || status === "waiting") return index;
    if (status !== "not_reached") latest = index;
  }
  return latest;
}

function LoopPasses({
  step,
  record,
  path,
  ctx,
}: {
  step: LoopStep;
  record: StepRecord | undefined;
  path: number[];
  ctx: RunContext;
}) {
  const progress = loopProgress(record);
  const [chosen, setChosen] = useState<number | null>(null);
  if (!progress || progress.total === 0) {
    return (
      <p className="pl-3.5 text-[13px] text-[var(--muted)]">
        {progress ? "The list was empty, so nothing ran." : `${stepCount(step.steps)} for each ${step.item}`}
      </p>
    );
  }
  const focused = ctx.focus === null ? null : passShowing(ctx.run, ctx.focus, path);
  const selected = Math.min(chosen ?? focused ?? defaultPass(step, path, progress, ctx), progress.total - 1);
  const label = progress.items[selected];
  return (
    <Nested
      label={`Item ${selected + 1} of ${progress.total}`}
      color="var(--kind-loop)"
      note={label ? `${step.item} = ${label}` : undefined}
    >
      <div role="tablist" aria-label={`Items of ${step.title}`} className="mb-3 flex flex-wrap gap-1">
        {Array.from({ length: progress.total }, (_, index) => {
          const status = passStatus(step, [...path, index], ctx.records);
          const tint = PASS_TINT[status];
          const active = index === selected;
          const strength = active ? 18 : 10;
          const style = tint
            ? { color: tint, backgroundColor: `color-mix(in srgb, ${tint} ${strength}%, transparent)` }
            : { color: "var(--muted)" };
          return (
            <button
              key={index}
              type="button"
              role="tab"
              aria-selected={active}
              title={progress.items[index]}
              className={`h-6 min-w-6 rounded-md px-1.5 text-xs tabular-nums transition-colors ${
                active ? "font-semibold ring-1 ring-[var(--fg)]" : "hover:bg-[var(--card-bg)]"
              }`}
              style={style}
              onClick={() => setChosen(index)}
            >
              {index + 1}
            </button>
          );
        })}
      </div>
      <RunList steps={step.steps} path={[...path, selected]} ctx={ctx} />
    </Nested>
  );
}

function StepRow({
  step,
  path,
  last,
  upNext,
  ctx,
}: {
  step: WorkflowStep;
  path: number[];
  last: boolean;
  upNext: boolean;
  ctx: RunContext;
}) {
  const record = ctx.records.get(recordKey(step.id, path));
  const stopped = record?.status === "running" && ctx.run.status !== "running";
  const status: RowStatus = stopped
    ? "stopped"
    : record?.status === "failed" && record.recovered
      ? "recovered"
      : (record?.status ?? (upNext ? "pending" : "not_reached"));
  const [open, setOpen] = useState(step.kind === "llm" || step.kind === "agent");
  const duration = stepDuration(record?.started_at ?? null, record?.finished_at ?? null);
  const blockStopped = stoppedInside(step, ctx.run);
  const hasOutput =
    status === "done" &&
    record?.output !== null &&
    record?.output !== undefined &&
    step.kind !== "approval" &&
    step.kind !== "branch" &&
    step.kind !== "loop";
  const muted = status === "not_reached" || status === "pending" || status === "skipped";
  const showCard = !blockStopped && (status === "failed" || status === "waiting");

  return (
    <li className="flex gap-3.5" data-run-step={step.id}>
      <div className="flex w-[22px] shrink-0 flex-col items-center">
        <StatusDot status={status} />
        {!last && <span className="min-h-3.5 w-px flex-1 bg-[var(--border)]" />}
      </div>
      <div className={`flex min-w-0 flex-1 flex-col gap-2.5 ${last ? "pb-1" : "pb-4"}`}>
        {showCard && status === "failed" && <FailedCard step={step} record={record} ctx={ctx} />}
        {showCard && status === "waiting" && <WaitingCard step={step} record={record} onAnswer={ctx.onAnswer} />}
        {!showCard && (
          <>
            <div className="flex min-w-0 items-baseline gap-2.5">
              <span className={`shrink-0 text-sm ${muted ? "text-[var(--muted)]" : "font-medium"}`}>{step.title}</span>
              {(step.kind === "llm" || step.kind === "agent") && status === "done" && (
                <span
                  className="shrink-0 rounded-full px-2 py-px text-xs"
                  style={{
                    color: KIND_COLOR[step.kind],
                    backgroundColor: `color-mix(in srgb, ${KIND_COLOR[step.kind]} 13%, transparent)`,
                  }}
                >
                  {KIND_LABEL[step.kind]}
                </span>
              )}
              <span className="min-w-0 truncate text-[13px] text-[var(--muted)]">
                {rowSummary(step, record, status)}
              </span>
              <span className="flex-1" />
              {duration && <span className="shrink-0 text-xs tabular-nums text-[var(--muted)]">{duration}</span>}
              {hasOutput && (
                <button
                  type="button"
                  aria-expanded={open}
                  aria-label={open ? `Hide output of ${step.title}` : `Show output of ${step.title}`}
                  className="flex h-6 w-6 shrink-0 items-center justify-center self-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
                  onClick={() => setOpen((v) => !v)}
                >
                  <ChevronDownIcon
                    className={`h-3.5 w-3.5 transition-transform motion-reduce:transition-none ${open ? "rotate-180" : ""}`}
                  />
                </button>
              )}
            </div>
            {hasOutput && open && <StepOutput value={record?.output} />}
            {hasOutput && open && step.kind === "agent" && <AgentToolsUsed activity={record?.agent} />}
          </>
        )}
        <RunArms step={step} record={record} path={path} ctx={ctx} />
        {step.kind === "loop" && <LoopPasses key={ctx.focus ?? ""} step={step} record={record} path={path} ctx={ctx} />}
      </div>
    </li>
  );
}

function RunList({ steps, path, ctx }: { steps: WorkflowStep[]; path: number[]; ctx: RunContext }) {
  const firstOpen =
    ctx.run.status === "running" ? steps.findIndex((step) => !ctx.records.has(recordKey(step.id, path))) : -1;
  const previousDone = firstOpen > 0 && ctx.records.get(recordKey(steps[firstOpen - 1].id, path))?.status !== "running";
  return (
    <ol className="flex flex-col">
      {steps.map((step, index) => (
        <StepRow
          key={step.id}
          step={step}
          path={path}
          last={index === steps.length - 1}
          upNext={index === firstOpen && (index === 0 ? path.length === 0 : previousDone)}
          ctx={ctx}
        />
      ))}
    </ol>
  );
}

type RunViewMode = "steps" | "canvas";

const RUN_VIEWS: { view: RunViewMode; label: string }[] = [
  { view: "steps", label: "Steps" },
  { view: "canvas", label: "Overview" },
];

interface WorkflowRunViewProps {
  task: ScheduledTask;
  run: ScheduledRun;
  workflow: Workflow;
  onRetry: (stepId?: string) => Promise<string | null>;
  onAnswer: (approved: boolean, note: string) => Promise<string | null>;
  onEditStep: (stepId: string) => void;
  onStop: () => Promise<string | null>;
  /** Opens a conversation looking into this failed run, with `model`
   * (null: the default); resolves to an error message, or null. */
  onInvestigate: (model: string | null) => Promise<string | null>;
}

function stepTitle(workflow: Workflow, stepId: string | undefined): string {
  if (!stepId) return "a step";
  return placeSteps(everyStep(workflow)).find((placed) => placed.step.id === stepId)?.step.title ?? stepId;
}

function useModels(enabled: boolean): string[] {
  const [models, setModels] = useState<string[]>([]);
  useEffect(() => {
    if (!enabled) return;
    fetch("/api/providers")
      .then((res) => res.json())
      .then((providers: Record<string, { default_model?: string }>) =>
        setModels(
          Object.entries(providers)
            .filter(([, info]) => info.default_model)
            .map(([key, info]) => `${key}:${info.default_model}`),
        ),
      )
      .catch(() => setModels([]));
  }, [enabled]);
  return models;
}

/** How the run stands, and what can be done about it, above the steps. */
function RunBanner({
  run,
  workflow,
  onStop,
  onInvestigate,
}: Pick<WorkflowRunViewProps, "run" | "workflow" | "onStop" | "onInvestigate">) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState("");
  const failedRecord = run.steps.findLast((r) => r.status === "failed");
  const models = useModels(run.status === "failed" && failedRecord !== undefined);
  const act = async (action: () => Promise<string | null>) => {
    setBusy(true);
    setError(await action());
    setBusy(false);
  };
  const box = "flex flex-col gap-2.5 rounded-xl border px-4 py-3 text-sm";

  if (run.status === "running") {
    const current = run.steps.findLast((r) => r.status === "running");
    return (
      <div className={`${box} border-[var(--border)]`} data-testid="run-banner">
        <div className="flex items-center gap-3">
          <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] motion-reduce:animate-none" />
          <span className="min-w-0 flex-1 truncate">
            {run.queued ? WAITING_FOR_BROWSER : `Running${current ? ` · ${stepTitle(workflow, current.step_id)}` : ""}`}
          </span>
          <button type="button" className={secondaryButton} disabled={busy} onClick={() => act(onStop)}>
            <span className="flex items-center gap-1.5">
              <StopIcon className="h-3.5 w-3.5" />
              Stop run
            </span>
          </button>
        </div>
        {error && <p className="text-[13px] text-[var(--danger)]">{error}</p>}
      </div>
    );
  }
  if (run.status === "needs_approval") {
    const waiting = run.steps.findLast((r) => r.status === "waiting");
    return (
      <div
        className={`${box} border-[color-mix(in_srgb,var(--warning)_45%,transparent)] bg-[color-mix(in_srgb,var(--warning)_8%,transparent)]`}
        data-testid="run-banner"
      >
        <div className="flex items-center gap-2.5">
          <ClockIcon className="h-4 w-4 shrink-0 text-[var(--warning)]" />
          <span>
            {waiting?.permission ? "Needs your OK" : "Waiting for you"} at{" "}
            <span className="font-medium">{stepTitle(workflow, waiting?.step_id)}</span> -- answer it below to go on.
          </span>
        </div>
      </div>
    );
  }
  if (run.status === "stopped") {
    const at = run.steps.findLast((r) => r.status === "running");
    return (
      <div className={`${box} border-[var(--border)] text-[var(--muted)]`} data-testid="run-banner">
        Stopped{at ? ` at ${stepTitle(workflow, at.step_id)}` : ""}. Nothing after that ran.
      </div>
    );
  }
  if (run.status === "completed" && run.files?.length) {
    return (
      <div
        className={`${box} border-[color-mix(in_srgb,var(--success)_40%,transparent)] bg-[color-mix(in_srgb,var(--success)_5%,transparent)]`}
        data-testid="run-banner"
      >
        <div className="flex items-center gap-2 font-medium">
          <CheckIcon className="h-4 w-4 text-[var(--success)]" strokeWidth={3} />
          Completed
        </div>
        <ul className="flex flex-col gap-1">
          {run.files.map((file) => (
            <li key={file.path} className="flex min-w-0 gap-2 text-[13px]">
              <span className="min-w-0 truncate" title={file.path}>
                {file.path}
              </span>
              {file.rows !== undefined && file.columns !== undefined && (
                <span className="shrink-0 tabular-nums text-[var(--muted)]">
                  {file.rows} rows × {file.columns} columns
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (run.status === "failed" && failedRecord) {
    return (
      <div
        className={`${box} border-[color-mix(in_srgb,var(--danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--danger)_5%,transparent)]`}
        data-testid="run-banner"
      >
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="font-medium">Failed at {stepTitle(workflow, failedRecord.step_id)}</div>
            {failedRecord.error && (
              <div className="mt-0.5 line-clamp-4 break-words text-[13px] text-[var(--muted)]">
                {failedRecord.error}
              </div>
            )}
            <div className="mt-1 text-[13px] text-[var(--muted)]">
              The run stopped there, so nothing after this step produced data.
            </div>
          </div>
          {run.screenshot && <Screenshot name={run.screenshot} alt="The page when the step failed" />}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <InvestigationLink run={run} buttonClass={primaryButton} />
          <button
            type="button"
            className={run.investigation ? secondaryButton : primaryButton}
            disabled={busy}
            onClick={() => act(() => onInvestigate(model || null))}
          >
            <span className="flex items-center gap-1.5">
              <SparkIcon className="h-3.5 w-3.5" />
              {run.investigation ? "Look into it again" : "Let AI look into it"}
            </span>
          </button>
          <select
            aria-label="Model to look into it"
            className="h-8 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-[13px]"
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            <option value="">Default model</option>
            {models.map((m) => (
              <option key={m} value={m}>
                {m.split(":", 2)[1] ?? m}
              </option>
            ))}
          </select>
          <span className="text-[13px] text-[var(--muted)]">
            Opens a new conversation that reproduces it and drafts a fix for you to review.
          </span>
        </div>
        {error && <p className="text-[13px] text-[var(--danger)]">{error}</p>}
      </div>
    );
  }
  return null;
}

/** One workflow run, step by step (the Run artboard of
 * https://claude.ai/artifact/4G5JyZ3r4tMPF6QcFG3Vj1): what each step did,
 * where it stopped and why, and the way on from there. A branch shows the
 * arm it took; a loop shows one item's pass at a time. */
export function WorkflowRunView({
  task,
  run,
  workflow,
  onRetry,
  onAnswer,
  onEditStep,
  onStop,
  onInvestigate,
}: WorkflowRunViewProps) {
  const duration = runDuration(run);
  const crashed = run.status === "failed" && !run.steps.some((record) => record.status === "failed");
  const [retrying, setRetrying] = useState(false);
  const [crashError, setCrashError] = useState<string | null>(null);
  const [view, setView] = useState<RunViewMode>("steps");
  const [focus, setFocus] = useState<string | null>(null);
  const ctx: RunContext = {
    workflow,
    run,
    records: recordMap(run),
    numbers: new Map(placeSteps(everyStep(workflow)).map((placed) => [placed.step.id, placed.number])),
    inputNames: new Set(workflow.inputs.map((input) => input.name)),
    onRetry,
    onAnswer,
    onEditStep,
    focus,
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[760px] flex-col gap-6 px-4 pb-16 pt-5">
        <div className="flex flex-col gap-2">
          <div className="text-[13px] text-[var(--muted)]">
            Run · {capitalize(formatRunTime(run.started_at))} · {runSourceLabel(run)}
            {duration && ` · ${duration}`}
            <span className="sr-only"> of {task.name}</span>
          </div>
          {workflow.inputs.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
              {workflow.inputs.map((input) => (
                <span key={input.name} className="inline-flex items-center gap-2">
                  <VarToken name={input.name} isInput />
                  <span className="rounded-md bg-[var(--card-bg)] px-2 py-0.5 text-[13px]">
                    {formatValue(run.inputs?.[input.name] ?? input.default)}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>

        <RunBanner run={run} workflow={workflow} onStop={onStop} onInvestigate={onInvestigate} />
        <InvestigationLink run={run} />
        <RunReportCard triggerId={task.trigger_id} run={run} onInvestigate={onInvestigate} />
        {run.sites && run.sites.length > 0 && run.status !== "running" && (
          <div className="text-[13px] text-[var(--muted)]" data-testid="run-sites">
            Opened: <span className="text-[var(--fg)]">{run.sites.join(", ")}</span>
          </div>
        )}

        {crashed && (
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[var(--border)] px-4 py-3 text-sm">
            <span className="min-w-0 flex-1">{run.error ?? "This run stopped before it finished."}</span>
            <button
              type="button"
              disabled={retrying}
              className={primaryButton}
              onClick={async () => {
                setRetrying(true);
                setCrashError(await onRetry());
                setRetrying(false);
              }}
            >
              Continue the run
            </button>
            {crashError && <p className="w-full text-[13px] text-[var(--danger)]">{crashError}</p>}
          </div>
        )}

        <ViewToggle label="Run view" views={RUN_VIEWS} value={view} onChange={setView} />
        {view === "steps" ? (
          <RunList steps={workflow.steps} path={[]} ctx={ctx} />
        ) : (
          <WorkflowCanvas
            workflow={workflow}
            run={run}
            onOpenStep={(stepId) => {
              setView("steps");
              setFocus(stepId);
              // The list is drawn by the time the next frame paints.
              requestAnimationFrame(() =>
                document.querySelector(`[data-run-step="${CSS.escape(stepId)}"]`)?.scrollIntoView({ block: "center" }),
              );
            }}
          />
        )}
      </div>
    </div>
  );
}
