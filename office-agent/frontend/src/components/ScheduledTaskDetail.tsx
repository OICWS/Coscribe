import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  deleteScheduledTask,
  getEnvironments,
  getTaskNotes,
  pauseScheduledTask,
  resumeScheduledTask,
  saveTaskNotes,
  patchScheduledTask,
} from "../lib/rest";
import { goToThread } from "../lib/nav";
import { capitalize, formatRunTime, RUN_STATUS_LABEL, runDuration, runSourceLabel } from "../lib/runLabels";
import { describeSchedule } from "../lib/scheduleLabels";
import { TriggerNote, WebhookSection } from "./TriggerNote";
import { ThisTask } from "../lib/taskCalls";
import { allSteps } from "../lib/workflowTree";
import type { ScheduledTask } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { ConfirmDialog } from "./ConfirmDialog";
import { DEFAULT_ENVIRONMENT } from "./EnvironmentDialog";
import { ChevronRightIcon, PencilIcon, PlayIcon, TrashIcon } from "./icons";
import { RunStatusIcon } from "./RunStatusIcon";
import { ScheduledTaskSimple } from "./ScheduledTaskSimple";
import { TaskReachProvider, TaskReachSection } from "./TaskReachSection";
import { TaskMemorySection } from "./TaskMemorySection";
import { ToggleSwitch } from "./ToggleSwitch";
import { RunInputsDialog } from "./workflow/RunInputsDialog";
import { TaskSettingsTab } from "./workflow/TaskSettingsTab";
import { ViewToggle } from "./workflow/ViewToggle";
import { WorkflowCanvas } from "./workflow/WorkflowCanvas";
import { WorkflowEditor } from "./workflow/WorkflowEditor";

// Mirrors tools/bookkeeping/scheduled_tasks.py's MAX_NOTES_CHARS.
const MAX_NOTES_CHARS = 4000;

const APPROVAL_LABEL: Record<ScheduledTask["approval_mode"], string> = {
  manual: "Ask before every action",
  auto: "Automatically approve",
  skip: "Never ask",
};

const APPROVAL_DESCRIPTION: Record<ScheduledTask["approval_mode"], string> = {
  manual: "Coscribe pauses and waits for your approval before any action that needs it.",
  auto: "Coscribe creates and edits files on its own, but pauses before running code or using connectors.",
  skip: "Coscribe never pauses for approval, including for running code and using connectors. Your blocking rules still apply.",
};

function formatNextRun(task: ScheduledTask): string {
  if (task.schedule.kind === "manual") return "Runs when you start it";
  if (["folder", "connector", "webhook"].includes(task.schedule.kind)) return describeSchedule(task.schedule);
  if (!task.next_run_at) return "Not scheduled";
  return `Next run: ${new Date(task.next_run_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })}`;
}

function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="mb-1 text-sm text-[var(--muted)]">{children}</div>;
}

const INSTRUCTIONS_COLLAPSED_LINES = 10;

/** Model-drafted instructions run long; collapsed past a screenful so
 * Notes and Runs stay in view. */
function InstructionsSection({ prompt }: { prompt: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = prompt.split("\n").length > INSTRUCTIONS_COLLAPSED_LINES || prompt.length > 900;
  return (
    <div>
      <SectionLabel>Instructions</SectionLabel>
      <div className="relative">
        <div className={`whitespace-pre-wrap text-sm ${long && !expanded ? "max-h-60 overflow-hidden" : ""}`}>
          {prompt}
        </div>
        {long && !expanded && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[var(--bg)] to-transparent" />
        )}
      </div>
      {long && (
        <button
          type="button"
          className="mt-1 text-sm text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : "Show all"}
        </button>
      )}
    </div>
  );
}

type NotesState = "idle" | "saving" | "saved" | "error";

/** The task's memory across runs: shown to every run at its start and
 * rewritten by the run itself, but also the user's to read and correct.
 * Saved on blur rather than with a button -- it's a scratchpad, not a
 * form. */
function NotesSection({ task, onChanged }: { task: ScheduledTask; onChanged: () => void }) {
  const [notes, setNotes] = useState("");
  const savedNotesRef = useRef("");
  const [status, setStatus] = useState<NotesState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Re-read after every run too: the run itself rewrites the notes.
  const lastRunFinishedAt = task.runs[task.runs.length - 1]?.finished_at ?? null;
  useEffect(() => {
    if (focused) return;
    getTaskNotes(task.trigger_id).then((result) => {
      if ("notes" in result) {
        setNotes(result.notes);
        savedNotesRef.current = result.notes;
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.trigger_id, lastRunFinishedAt]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [notes]);

  const save = async () => {
    setFocused(false);
    if (notes.trim() === savedNotesRef.current.trim()) return;
    setStatus("saving");
    const result = await saveTaskNotes(task.trigger_id, notes);
    if ("error" in result) {
      setStatus("error");
      setError(result.error);
      return;
    }
    savedNotesRef.current = result.notes;
    setNotes(result.notes);
    setError(null);
    setStatus("saved");
  };

  const toggleNotes = async () => {
    await patchScheduledTask(task.trigger_id, { notes_enabled: !task.notes_enabled });
    onChanged();
  };

  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-3">
        <span className="text-sm text-[var(--muted)]">Notes</span>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-[var(--muted)]">
          Remember between runs
          <ToggleSwitch on={task.notes_enabled} onClick={toggleNotes} label="Remember between runs" />
        </label>
      </div>
      <textarea
        ref={textareaRef}
        rows={2}
        value={notes}
        maxLength={MAX_NOTES_CHARS}
        disabled={!task.notes_enabled}
        placeholder={
          task.notes_enabled
            ? "Each run writes what the next one should know here -- progress, where it left off, what changed."
            : "Runs start without notes."
        }
        onFocus={() => {
          setFocused(true);
          setStatus("idle");
        }}
        onBlur={save}
        onChange={(e) => setNotes(e.target.value)}
        className="-mx-2 block w-[calc(100%+1rem)] resize-none overflow-hidden rounded-md border border-transparent bg-transparent px-2 py-1.5 text-sm leading-relaxed outline-none transition-colors placeholder:text-[var(--muted)] hover:border-[var(--border)] focus:border-[var(--border-hover)] disabled:cursor-not-allowed disabled:opacity-50"
      />
      <div className="mt-1 h-4 text-xs text-[var(--muted)]" aria-live="polite">
        {status === "saving" && "Saving…"}
        {status === "saved" && "Saved"}
        {status === "error" && <span className="text-[var(--danger)]">{error}</span>}
        {status === "idle" && focused && `${notes.length} / ${MAX_NOTES_CHARS}`}
      </div>
    </div>
  );
}

// The simple view lists the latest runs; older ones are a click away.
const RECENT_RUNS = 5;

/** A task's runs, newest first. `onShowAll` makes it the overview's short list of the latest
 * few, which opens the Runs tab for the rest, under what the task keeps between runs. */
function RunsSection({ task, onShowAll }: { task: ScheduledTask; onShowAll?: () => void }) {
  const recent = Boolean(onShowAll);
  const newestFirst = [...task.runs].reverse();
  const runs = recent ? newestFirst.slice(0, RECENT_RUNS) : newestFirst;
  return (
    <>
      {recent && <TaskMemorySection task={task} refresh={`${task.last_run_at}:${task.last_run_status}`} />}
      <div>
        {recent && <h2 className="mb-2 text-sm font-medium">Recent runs</h2>}
        <TriggerNote task={task} />
        {runs.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No runs yet -- use Run now to try it out.</p>
        ) : (
          <ul className="-mx-2 flex flex-col">
            {runs.map((run) => {
              const duration = runDuration(run);
              return (
                <li key={run.run_id}>
                  <button
                    type="button"
                    className="group flex w-full items-center gap-3 rounded-md px-2 py-2 text-left text-sm hover:bg-[var(--card-bg)]"
                    onClick={() => goToThread(run.thread_id)}
                    title={run.error ?? undefined}
                  >
                    <RunStatusIcon status={run.status} />
                    <span className="min-w-0 flex-1 truncate">
                      {capitalize(formatRunTime(run.started_at))}
                      <span className="text-[var(--muted)]">
                        {" "}
                        · {runSourceLabel(run)}
                        {duration && ` · ${duration}`}
                        {run.versions?.length ? ` · version ${run.versions.join(" → ")}` : ""}
                      </span>
                    </span>
                    {run.status !== "completed" && (
                      <span className="shrink-0 text-xs text-[var(--muted)]">{RUN_STATUS_LABEL[run.status]}</span>
                    )}
                    {run.status === "completed" && run.quiet ? (
                      <span className="shrink-0 text-xs text-[var(--muted)]" title="A check found nothing to do">
                        Nothing new{run.quiet > 1 ? ` · ${run.quiet} checks` : ""}
                      </span>
                    ) : null}
                    <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)] opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {runs.length < newestFirst.length && (
          <button
            type="button"
            className="mt-1 text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
            onClick={onShowAll}
          >
            Show all {newestFirst.length} runs
          </button>
        )}
      </div>
    </>
  );
}

interface ScheduledTaskDetailProps {
  task: ScheduledTask;
  onEdit: () => void;
  onRunNow: (inputs?: Record<string, unknown>) => void;
  onDeleted: () => void;
  onChanged: () => void;
  /** Opens this workflow step for editing (from a run's "Edit step"). */
  focusStepId?: string | null;
}

/** The name of the environment a task's runs use; it is edited from the picker below a message. */
function EnvironmentName({
  id,
  className = "block break-all text-sm font-medium",
}: {
  id: string;
  className?: string;
}) {
  const [name, setName] = useState(id === DEFAULT_ENVIRONMENT ? "Default" : "");
  useEffect(() => {
    let cancelled = false;
    getEnvironments()
      .then(({ environments }) => !cancelled && setName(environments.find((e) => e.id === id)?.name ?? "Default"))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [id]);
  return <span className={className}>{name}</span>;
}

/** Whether the task is on and when it runs next. */
function StatusRow({ task, onToggle }: { task: ScheduledTask; onToggle: () => void }) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <ToggleSwitch on={task.enabled} onClick={onToggle} label={task.enabled ? "Pause task" : "Resume task"} />
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          task.enabled
            ? "bg-green-500/15 text-green-600 dark:text-green-400"
            : "bg-[var(--card-bg)] text-[var(--muted)]"
        }`}
      >
        {task.enabled ? "Active" : "Paused"}
      </span>
      <span className="text-sm text-[var(--muted)]">{formatNextRun(task)}</span>
    </div>
  );
}

/** A task that runs from instructions rather than steps: everything on one page. */
function InstructionsBody({ task, onChanged }: { task: ScheduledTask; onChanged: () => void }) {
  return (
    <div className="mt-6 flex flex-col gap-6">
      <InstructionsSection prompt={task.prompt} />
      <div>
        <SectionLabel>Repeats</SectionLabel>
        <div className="text-sm font-medium">{describeSchedule(task.schedule)}</div>
      </div>
      <div className="flex flex-col gap-3">
        <div>
          <SectionLabel>Workspace</SectionLabel>
          <EnvironmentName id={task.environment ?? DEFAULT_ENVIRONMENT} />
        </div>
        <TaskReachSection
          taskId={task.trigger_id}
          changed={JSON.stringify([task.environment, task.permissions?.folders])}
          onChanged={onChanged}
        />
      </div>
      <div>
        <SectionLabel>Permissions</SectionLabel>
        <div className="text-sm font-medium">{APPROVAL_LABEL[task.approval_mode]}</div>
        <div className="text-sm text-[var(--muted)]">{APPROVAL_DESCRIPTION[task.approval_mode]}</div>
        <div className="text-sm text-[var(--muted)]">A run stops after {task.max_steps ?? 150} steps.</div>
      </div>
      <NotesSection task={task} onChanged={onChanged} />
      <TaskMemorySection task={task} refresh={`${task.last_run_at}:${task.last_run_status}`} />
      <WebhookSection task={task} />
      <RunsSection task={task} />
    </div>
  );
}

type Tab = "overview" | "steps" | "runs" | "settings";

/** The workflow task page's tabs, as one row under the header. */
function TaskTabs({ tab, onTab, runs, steps }: { tab: Tab; onTab: (tab: Tab) => void; runs: number; steps: number }) {
  const tabs: { tab: Tab; label: string; count?: number }[] = [
    { tab: "overview", label: "Overview" },
    { tab: "steps", label: "Steps", count: steps },
    { tab: "runs", label: "Runs", count: runs },
    { tab: "settings", label: "Settings" },
  ];
  return (
    <div role="tablist" aria-label="Task page" className="mt-4 flex gap-5 border-b border-[var(--border)]">
      {tabs.map((item) => (
        <button
          key={item.tab}
          type="button"
          role="tab"
          aria-selected={tab === item.tab}
          className={`-mb-px flex cursor-pointer items-center gap-1.5 border-b-2 pb-2 pt-1 text-sm transition-colors ${
            tab === item.tab
              ? "border-[var(--fg)] font-medium text-[var(--fg)]"
              : "border-transparent text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
          onClick={() => onTab(item.tab)}
        >
          {item.label}
          {item.count ? (
            <span className="rounded-full bg-[var(--card-bg)] px-1.5 text-[11px] text-[var(--muted)]">{item.count}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

/** The steps to edit, or the same steps as a flowchart; a step clicked on the chart opens in the list. */
function StepsTab({
  taskId,
  workflow,
  persist,
  focus,
  onFocus,
}: {
  taskId: string;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  focus: string | null;
  onFocus: (stepId: string) => void;
}) {
  const [chart, setChart] = useState(false);
  return (
    <ThisTask.Provider value={taskId}>
      <div className="flex flex-col gap-3">
        <ViewToggle
          label="Steps view"
          views={[
            { view: "list", label: "List" },
            { view: "chart", label: "Flowchart" },
          ]}
          value={chart ? "chart" : "list"}
          onChange={(view) => setChart(view === "chart")}
        />
        {chart ? (
          <WorkflowCanvas
            workflow={workflow}
            onOpenStep={(stepId) => {
              onFocus(stepId);
              setChart(false);
            }}
          />
        ) : (
          <WorkflowEditor workflow={workflow} persist={persist} focusStepId={focus} />
        )}
      </div>
    </ThisTask.Provider>
  );
}

/** Which tab the page shows, and the step the Steps tab's editor opens on. */
function useTab(focusStepId: string | null | undefined) {
  const [tab, setTab] = useState<Tab>(focusStepId ? "steps" : "overview");
  // A run's "Edit step" opens the step while the page is open.
  const [seenFocus, setSeenFocus] = useState(focusStepId);
  if (focusStepId !== seenFocus) {
    setSeenFocus(focusStepId);
    if (focusStepId) setTab("steps");
  }
  const [openedStep, setOpenedStep] = useState<string | null>(null);
  const openStep = (stepId: string) => {
    setOpenedStep(stepId);
    setTab("steps");
  };
  return { tab, setTab, focus: openedStep ?? focusStepId ?? null, openStep };
}

/** A workflow task's tabs and the one that is open. */
function WorkflowTaskBody({
  task,
  workflow,
  persist: saveWorkflow,
  focusStepId,
  onEdit,
  onChanged,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  focusStepId?: string | null;
  onEdit: () => void;
  onChanged: () => void;
}) {
  const { tab, setTab, focus, openStep } = useTab(focusStepId);
  return (
    <>
      <TaskTabs tab={tab} onTab={setTab} runs={task.runs.length} steps={allSteps(workflow).length} />
      <div className="mt-6">
        {tab === "overview" && (
          <ScheduledTaskSimple
            task={task}
            workflow={workflow}
            persist={saveWorkflow}
            onEditSteps={() => setTab("steps")}
            onOpenStep={openStep}
            onShowSettings={() => setTab("settings")}
            onShowRuns={() => setTab("runs")}
            runs={<RunsSection task={task} onShowAll={() => setTab("runs")} />}
            environment={<EnvironmentName id={task.environment ?? DEFAULT_ENVIRONMENT} className="inline" />}
          />
        )}
        {tab === "steps" && (
          <StepsTab
            taskId={task.trigger_id}
            workflow={workflow}
            persist={saveWorkflow}
            focus={focus}
            onFocus={openStep}
          />
        )}
        {tab === "runs" && (
          <div className="flex flex-col gap-6">
            <RunsSection task={task} />
          </div>
        )}
        {tab === "settings" && (
          <TaskSettingsTab task={task} workflow={workflow} persist={saveWorkflow} onEdit={onEdit} onChanged={onChanged} />
        )}
      </div>
    </>
  );
}

export function ScheduledTaskDetail({
  task,
  onEdit,
  onRunNow,
  onDeleted,
  onChanged,
  focusStepId,
}: ScheduledTaskDetailProps) {
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [starting, setStarting] = useState(false);
  const [askingInputs, setAskingInputs] = useState(false);
  const workflow = task.workflow;

  const start = (inputs?: Record<string, unknown>) => {
    setAskingInputs(false);
    setStarting(true);
    onRunNow(inputs);
  };

  const toggleEnabled = async () => {
    await (task.enabled ? pauseScheduledTask : resumeScheduledTask)(task.trigger_id);
    onChanged();
  };
  const saveWorkflow = async (next: Workflow) => {
    const result = await patchScheduledTask(task.trigger_id, { workflow: next });
    if ("error" in result) return result.error;
    onChanged();
    return null;
  };

  const confirmDelete = async () => {
    setDeleteConfirm(false);
    await deleteScheduledTask(task.trigger_id);
    onDeleted();
  };

  return (
    <TaskReachProvider taskId={task.trigger_id} onChanged={onChanged}>
      <div className="flex-1 overflow-y-auto p-6 md:[body[data-quick-edit]_&]:pr-[440px]">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between gap-4">
          <h1
            className="min-w-0 truncate text-2xl font-semibold"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            {task.name}
          </h1>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              aria-label="Edit"
              title="Rename or change when it runs"
              className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
              onClick={onEdit}
            >
              <PencilIcon className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Delete"
              title="Delete"
              className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--danger)]"
              onClick={() => setDeleteConfirm(true)}
            >
              <TrashIcon className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={starting || workflow?.steps.length === 0}
              title={workflow?.steps.length === 0 ? "Add steps before running it" : undefined}
              className="flex items-center gap-1.5 rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm font-medium text-[var(--primary-fg)] hover:bg-[var(--primary-hover)] disabled:opacity-60"
              onClick={() => (workflow && workflow.inputs.length > 0 ? setAskingInputs(true) : start())}
            >
              <PlayIcon className="h-3.5 w-3.5" /> Run now
            </button>
          </div>
        </div>

        <StatusRow task={task} onToggle={toggleEnabled} />

        {workflow ? (
          <WorkflowTaskBody
            task={task}
            workflow={workflow}
            persist={saveWorkflow}
            focusStepId={focusStepId}
            onEdit={onEdit}
            onChanged={onChanged}
          />
        ) : (
          <>
            <div className="mt-4 border-t border-[var(--border)]" />
            <InstructionsBody task={task} onChanged={onChanged} />
          </>
        )}
      </div>

      {askingInputs && workflow && (
        <RunInputsDialog
          taskName={task.name}
          inputs={workflow.inputs}
          onCancel={() => setAskingInputs(false)}
          onRun={start}
        />
      )}
      {deleteConfirm && (
        <ConfirmDialog
          title="Delete scheduled task?"
          description={`"${task.name}" and the conversations of its runs will be permanently removed.`}
          onCancel={() => setDeleteConfirm(false)}
          onConfirm={confirmDelete}
        />
      )}
      </div>
    </TaskReachProvider>
  );
}
