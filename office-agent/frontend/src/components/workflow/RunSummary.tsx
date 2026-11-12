import { lazy, Suspense, useState, type ReactNode } from "react";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { type PlainGroup, type PlainRow, plainOutline } from "../../lib/plainOutline";
import { openThreadFile } from "../../lib/rest";
import { runDuration } from "../../lib/runLabels";
import { fileParts, plainError, runAt, runNotes, runResultText } from "../../lib/runResult";
import { runStepTitle } from "../../lib/calledRun";
import { useTaskNames } from "../../lib/taskCalls";
import { stepDuration } from "../../lib/workflowLabels";
import { type NodeRunState, runMap } from "../../lib/workflowRunMap";
import type { ScheduledRun } from "../../types/settings";
import type { StepRecord, WorkflowInput } from "../../types/workflow";
import { CopyButton } from "../CopyButton";
import { CheckIcon, ClockIcon, FileTextIcon, SparkIcon, StopIcon, XCircleIcon } from "../icons";
import { FailedCard, type FailedContext } from "./FailedCard";
import { InvestigationLink } from "./InvestigationLink";
import type { AnswerValues } from "./PauseCards";
import { PlainText } from "./PlainStepList";
import { StatusDot } from "./StatusDot";
import { WaitingCard } from "./WaitingCard";

const Markdown = lazy(() => import("../Markdown").then((m) => ({ default: m.Markdown })));

export interface SummaryContext extends FailedContext {
  run: ScheduledRun;
  onAnswer: (approved: boolean, note: string, values?: AnswerValues) => Promise<string | null>;
  onStop: () => Promise<string | null>;
  onInvestigate: (model: string | null) => Promise<string | null>;
}

function scrollToStep(stepId: string) {
  document
    .querySelector(`[data-run-row="${CSS.escape(stepId)}"]`)
    ?.scrollIntoView({ block: "center", behavior: "smooth" });
}

/** A button that runs `action` and shows the error it resolves to. */
function useAct() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const act = async (action: () => Promise<string | null>) => {
    setBusy(true);
    setError(await action());
    setBusy(false);
  };
  return { busy, error, act };
}

const TONE: Record<string, string> = {
  done: "var(--success)",
  waiting: "var(--warning)",
  failed: "var(--danger)",
};

const SPINNER = (
  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] motion-reduce:animate-none" />
);

function StopButton({ busy, onStop }: { busy: boolean; onStop: () => void }) {
  return (
    <button type="button" className={secondaryButton} disabled={busy} onClick={onStop}>
      <span className="flex items-center gap-1.5">
        <StopIcon className="h-3.5 w-3.5" />
        Stop
      </span>
    </button>
  );
}

/** The card's first line: how the run ended, or what it is at, and what can be done now. */
function StatusLine({ ctx }: { ctx: SummaryContext }) {
  const { run, workflow } = ctx;
  const { busy, error, act } = useAct();
  const at = runAt(run);
  const title = at ? runStepTitle(workflow, run, at.step_id) : null;
  const duration = runDuration(run);
  let tone = "";
  let icon: ReactNode = null;
  let words: ReactNode;
  let actions: ReactNode = null;
  let why: string | null = null;
  let live = false;
  let plain = "";
  if (run.status === "completed") {
    tone = run.quiet ? "" : "done";
    icon = <CheckIcon className="h-4 w-4" strokeWidth={3} />;
    const ended = run.quiet ? run.steps.find((record) => record.note?.startsWith("Nothing to do")) : undefined;
    const found = ended ? `“${runStepTitle(workflow, run, ended.step_id)}” found` : "a check found";
    words = run.quiet ? `Nothing new: ${found} nothing to do` : duration ? `Done in ${duration}` : "Done";
  } else if (run.status === "needs_approval") {
    tone = "waiting";
    icon = <ClockIcon className="h-4 w-4" />;
    words = (
      <>
        {at?.pause ? "Waiting for your answer at" : "Waiting for your OK at"} <b className="font-medium">{title}</b>
      </>
    );
    if (at)
      actions = (
        <button type="button" className={primaryButton} onClick={() => scrollToStep(at.step_id)}>
          Answer it
        </button>
      );
  } else if (run.status === "failed") {
    tone = "failed";
    icon = <XCircleIcon className="h-4 w-4" />;
    words = title ? (
      <>
        Stopped at <b className="font-medium">{title}</b>
      </>
    ) : (
      "Stopped before it finished"
    );
    why = plainError(at?.error ?? run.error);
    actions = (
      <>
        <button
          type="button"
          className={secondaryButton}
          disabled={busy}
          onClick={() => act(() => ctx.onRetry(at?.step_id))}
        >
          Try again
        </button>
        <InvestigationLink run={run} buttonClass={secondaryButton} />
        <button
          type="button"
          className={secondaryButton}
          disabled={busy}
          onClick={() => act(() => ctx.onInvestigate(null))}
        >
          <span className="flex items-center gap-1.5">
            <SparkIcon className="h-3.5 w-3.5" />
            {run.investigation ? "Look into it again" : "Let AI look into it"}
          </span>
        </button>
      </>
    );
  } else if (run.status === "stopped") {
    words = title ? `Stopped at ${title}. Nothing after that ran.` : "Stopped. Nothing after that ran.";
  } else {
    icon = SPINNER;
    words = plain =
      run.status === "waiting"
        ? `${title ?? "A step"} is waiting; it goes on by itself`
        : `Running${title ? `: ${title}` : ""}`;
    live = true;
    actions = <StopButton busy={busy} onStop={() => act(ctx.onStop)} />;
  }
  return (
    <div className="flex flex-col gap-2">
      <div className={`flex items-center gap-x-3 gap-y-2 ${live ? "" : "flex-wrap"}`}>
        <span className="flex min-w-0 flex-1 items-center gap-2 text-[15px]" style={{ color: TONE[tone] }}>
          <span className="flex shrink-0 items-center">{icon}</span>
          {/* A running run's line changes with each step: one line, so the page doesn't jump. */}
          <span className={`min-w-0 text-[var(--fg)] ${live ? "truncate" : ""}`} title={live ? plain : undefined}>
            {words}
          </span>
        </span>
        {actions && <span className="flex shrink-0 flex-wrap items-center gap-2">{actions}</span>}
      </div>
      {why && <p className="text-[13px] text-[var(--muted)]">{why}</p>}
      {error && <p className="text-[13px] text-[var(--danger)]">{error}</p>}
    </div>
  );
}

function Files({ run }: { run: ScheduledRun }) {
  const [error, setError] = useState<string | null>(null);
  if (!run.files?.length) return null;
  return (
    <ul className="flex flex-col gap-1" data-testid="run-files">
      {run.files.map((file) => {
        const { name, folder } = fileParts(file.path);
        return (
          <li key={file.path} className="flex min-w-0 items-center gap-2 text-sm">
            <FileTextIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
            <span className="min-w-0 truncate" title={file.path}>
              <span className="font-medium">{name}</span>
              {folder && <span className="text-[var(--muted)]"> in {folder}</span>}
            </span>
            <button
              type="button"
              className="ml-auto shrink-0 text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
              onClick={() => void openThreadFile(run.thread_id, file.path, false).then(setError)}
            >
              Open
            </button>
          </li>
        );
      })}
      {error && <li className="text-[13px] text-[var(--danger)]">{error}</li>}
    </ul>
  );
}

/** What the run wrote for the person, a few lines of it until they ask for all. */
function ResultText({ text, partial }: { text: string; partial: boolean }) {
  const [all, setAll] = useState(false);
  const long = text.length > 600 || text.split("\n").length > 8;
  return (
    <div className="flex flex-col gap-1.5" data-testid="run-result-text">
      {partial && <div className="text-xs font-medium text-[var(--muted)]">Before it stopped</div>}
      <div className={`text-sm ${long && !all ? "line-clamp-6" : ""}`}>
        <Suspense fallback={<p className="whitespace-pre-wrap">{text}</p>}>
          <Markdown text={text} />
        </Suspense>
      </div>
      <div className="flex items-center gap-3 text-[13px] text-[var(--muted)]">
        {long && (
          <button type="button" className="hover:text-[var(--fg)] hover:underline" onClick={() => setAll((v) => !v)}>
            {all ? "Show less" : "Show all"}
          </button>
        )}
        <CopyButton getText={() => text} title="Copy the text" className="hover:text-[var(--fg)]" />
      </div>
    </div>
  );
}

/** How the run went and what it got, above its steps (decision 0038). */
function ResultCard({ ctx }: { ctx: SummaryContext }) {
  const { run, workflow } = ctx;
  const result = run.status === "running" ? null : runResultText(workflow, run);
  const notes = runNotes(run, (stepId) => runStepTitle(workflow, run, stepId));
  const got = Boolean(result || run.files?.length);
  return (
    <section
      className="flex flex-col gap-3 rounded-xl border border-[var(--border)] px-4 py-3.5"
      data-testid="run-result"
      aria-label="How the run went"
    >
      <StatusLine ctx={ctx} />
      {got && <div className="h-px bg-[var(--border)]" />}
      <Files run={run} />
      {result && <ResultText text={result.text} partial={run.status !== "completed"} />}
      {notes.length > 0 && (
        <ul className="flex flex-col gap-0.5 text-[13px] text-[var(--muted)]" data-testid="run-notes">
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

// -- The steps --------------------------------------------------------------------------

interface ListContext {
  ctx: SummaryContext;
  states: Map<string, NodeRunState>;
  inputs: WorkflowInput[];
  /** Each step's last record, for its time and its card. */
  last: Map<string, StepRecord>;
  count: Map<string, number>;
}

const MUTED = new Set(["not_reached", "not_taken", "skipped"]);

function sideWords(state: NodeRunState | undefined, record: StepRecord | undefined, runs: number): string | null {
  const passes = state?.passes;
  if (passes && passes.total) return `${passes.done} of ${passes.total} done`;
  if (state?.status === "not_taken") return "Not this time";
  if (state?.status === "skipped") return "Skipped";
  if (runs !== 1 || !record) return null;
  return stepDuration(record.started_at, record.finished_at);
}

const RECOVERED: Record<NonNullable<StepRecord["recovered"]>, string> = {
  skipped: "Failed, skipped",
  fallback: "Failed, other steps ran instead",
  item_skipped: "Failed on an item, skipped it",
  added: "Failed, the run added steps for it",
};

function Row({ row, number, list }: { row: PlainRow; number: number | null; list: ListContext }) {
  const { step } = row;
  const state = list.states.get(step.id);
  const status = state?.status ?? "not_reached";
  const record = list.last.get(step.id);
  const at = runAt(list.ctx.run);
  // The step the run stopped or waits at opens its card here, as in the detailed view.
  const open = at?.step_id === step.id && (status === "failed" || status === "waiting") ? at : undefined;
  const side = sideWords(state, record, list.count.get(step.id) ?? 0);
  return (
    <li data-run-row={step.id} data-run-status={status}>
      <div className="flex items-start gap-3 px-2 py-1.5">
        {number !== null && (
          <span className="mt-0.5 w-5 shrink-0 text-right text-[13px] tabular-nums text-[var(--muted)]">{number}</span>
        )}
        <StatusDot status={status === "not_taken" ? "not_reached" : status} />
        <span className="min-w-0 flex-1">
          <span
            className={`line-clamp-2 text-sm leading-snug ${MUTED.has(status) ? "text-[var(--muted)]" : ""}`}
            title={step.title}
          >
            {step.title}
          </span>
          {row.detail && status !== "not_taken" && (
            <span
              className="mt-0.5 line-clamp-2 text-[13px] leading-snug text-[var(--muted)] [overflow-wrap:anywhere]"
              title={row.detail ?? undefined}
            >
              <PlainText text={row.detail} inputs={list.inputs} />
            </span>
          )}
          {state?.recovered && (
            <span className="mt-0.5 block text-[13px] text-[var(--warning)]">{RECOVERED[state.recovered]}</span>
          )}
        </span>
        {side && <span className="mt-0.5 shrink-0 text-xs tabular-nums text-[var(--muted)]">{side}</span>}
      </div>
      {open && (
        <div className={`${number !== null ? "ml-9" : "ml-2"} mb-2 mt-1`}>
          {status === "failed" ? (
            <FailedCard step={step} record={open} ctx={list.ctx} />
          ) : (
            <WaitingCard step={step} record={open} onAnswer={list.ctx.onAnswer} />
          )}
        </div>
      )}
      {row.groups.map((group, index) => (
        <Group key={index} group={group} list={list} indent={number !== null} />
      ))}
    </li>
  );
}

function Group({ group, list, indent }: { group: PlainGroup; list: ListContext; indent: boolean }) {
  const margin = indent ? "ml-9" : "ml-6";
  const idle = group.rows.every((row) => list.states.get(row.step.id)?.status === "not_taken");
  if (idle)
    return (
      <div className={`${margin} border-l border-[var(--border)] px-4 py-1 text-xs text-[var(--muted)]`}>
        {group.label ?? "When it holds"} · not this time
      </div>
    );
  return (
    <div className={`${margin} border-l border-[var(--border)] pl-2`}>
      {group.label && <div className="px-2 pt-1 text-xs font-medium text-[var(--muted)]">{group.label}</div>}
      <ul>
        {group.rows.map((row) => (
          <Row key={row.step.id} row={row} number={null} list={list} />
        ))}
      </ul>
    </div>
  );
}

/** The task's steps in the task page's words, each with how it went in this run. */
function RunChecklist({ ctx }: { ctx: SummaryContext }) {
  const { run, workflow } = ctx;
  const outline = plainOutline(workflow, useTaskNames());
  const last = new Map<string, StepRecord>();
  const count = new Map<string, number>();
  for (const record of run.steps) {
    last.set(record.step_id, record);
    count.set(record.step_id, (count.get(record.step_id) ?? 0) + 1);
  }
  const list: ListContext = { ctx, states: runMap(workflow, run), inputs: workflow.inputs, last, count };
  return (
    <section className="flex flex-col gap-1" aria-label="Steps">
      <h2 className="text-sm font-medium">Steps</h2>
      <ol className="-mx-2 flex flex-col" data-testid="run-checklist">
        {outline.map((row, index) => (
          <Row key={row.step.id} row={row} number={index + 1} list={list} />
        ))}
      </ol>
    </section>
  );
}

/** A run as most people read it: how it went and what it got, then its steps in plain words.
 * Every detail stays one click away, below it. */
export function RunSummary({ ctx }: { ctx: SummaryContext }) {
  return (
    <>
      <ResultCard ctx={ctx} />
      <RunChecklist ctx={ctx} />
    </>
  );
}

/** What the simple view leaves out of its summary -- the run's inputs and sites -- folded under it. */
export function RunDetails({ children }: { children: ReactNode }) {
  return (
    <details data-testid="run-details">
      <summary className="cursor-pointer text-sm font-medium text-[var(--muted)] hover:text-[var(--fg)]">
        Details
      </summary>
      <div className="mt-3 flex flex-col gap-3">{children}</div>
    </details>
  );
}
