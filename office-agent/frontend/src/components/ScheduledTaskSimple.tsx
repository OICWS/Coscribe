import { type ReactNode, useState } from "react";
import { capitalize, formatRunTime, latestRun } from "../lib/runLabels";
import { plainDefault } from "../lib/inputKinds";
import { waitsForYou } from "../lib/plainOutline";
import { plainDetail } from "../lib/plainSteps";
import { describeSchedule } from "../lib/scheduleLabels";
import { neededAutonomy } from "../lib/workflowLabels";
import { allSteps } from "../lib/workflowTree";
import type { ScheduledTask } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { ChevronRightIcon, PencilIcon } from "./icons";
import { RunStatusIcon } from "./RunStatusIcon";
import { PLAIN_LABEL } from "./workflow/AutonomySetting";
import { PlainStepList, PlainText } from "./workflow/PlainStepList";
import { InputQuickPanel, QuickEditPanel } from "./workflow/QuickEditPanel";
import { TaskOverviewLine } from "./workflow/TaskOverviewLine";
import { WorkflowCanvas } from "./workflow/WorkflowCanvas";
import { WorkflowPermissions } from "./workflow/WorkflowPermissions";

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--border)] px-4 pb-4 pt-3">
      <div className="mb-2 flex min-h-8 items-center justify-between gap-3">
        <h2 className="text-sm font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

// Looks like a button so a person can tell it does something: plain gray text read as a label.
const linkButton =
  "inline-flex h-7 cursor-pointer items-center gap-1 rounded-md border border-[var(--border)] px-2 text-[13px] text-[var(--fg)] transition-colors hover:bg-[var(--card-bg)]";

/** What fills an input by itself when the task starts on something new: a folder task's file
 * (decision 0034), a connector item's or an event's field (decisions 0039, 0040). Nothing to
 * change there. */
function filledBy(task: ScheduledTask): Record<string, string> {
  const rule = task.schedule;
  if (rule.kind === "folder" && rule.input) return { [rule.input]: "the new file that arrived in the folder" };
  if (rule.kind !== "connector" && rule.kind !== "webhook") return {};
  const what = rule.kind === "webhook" ? "event" : "new item";
  const filled: Record<string, string> = {};
  for (const [name, path] of Object.entries(rule.inputs_from ?? {})) {
    if (path) filled[name] = path === "*" ? `the whole ${what}` : `the ${what}'s ${path}`;
  }
  return filled;
}

function Inputs({
  workflow,
  filled,
  onChange,
}: {
  workflow: Workflow;
  filled: Record<string, string>;
  onChange: (name: string) => void;
}) {
  if (workflow.inputs.length === 0) return null;
  const onlyTheFile = workflow.inputs.every((input) => input.name in filled);
  return (
    <div>
      <div className="mb-1 text-[13px] text-[var(--muted)]">
        {onlyTheFile ? "Works on" : "You fill in, each time it runs"}
      </div>
      <ul className="flex flex-col gap-1 text-sm">
        {workflow.inputs.map((input) => {
          if (input.name in filled)
            return (
              <li key={input.name} className="flex min-h-8 items-center justify-between gap-3">
                <span className="min-w-0">
                  {input.label || input.name}
                  <span className="text-[var(--muted)]"> · {filled[input.name]}</span>
                </span>
              </li>
            );
          const usual = plainDefault(input);
          return (
            <li key={input.name} className="flex min-h-8 items-center justify-between gap-3">
              <span className="min-w-0">
                {input.label || input.name}
                {input.required === false && <span className="text-[var(--muted)]"> (optional)</span>}
                {usual !== null && (
                  <span className="text-[var(--muted)]">
                    {" "}
                    · usually <span className="break-all">{usual}</span>
                  </span>
                )}
              </span>
              <button type="button" className={`${linkButton} shrink-0`} onClick={() => onChange(input.name)}>
                Change
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** The steps a run stops at for the person: their OK, or an answer. */
function Waits({ workflow }: { workflow: Workflow }) {
  const waits = waitsForYou(workflow);
  if (waits.length === 0) return null;
  return (
    <div>
      <div className="mb-1 text-[13px] text-[var(--muted)]">It stops and waits for you</div>
      <ul className="flex flex-col gap-1 text-sm">
        {waits.map((step) => (
          <li key={step.id}>
            {step.kind === "approval" ? "Your OK" : "Your answer"} at <span className="font-medium">{step.title}</span>
            {step.kind === "ask" && (
              <span className="text-[var(--muted)]">
                {" "}
                · <PlainText text={plainDetail(step, workflow.inputs) ?? ""} inputs={workflow.inputs} />
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The steps in plain words, each opening its quick edit; the flowchart behind a link. */
function WhatItDoes({
  workflow,
  persist,
  onShowDetails,
  onOpenStep,
}: {
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onShowDetails: () => void;
  onOpenStep: (stepId: string) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [chart, setChart] = useState(false);
  const editingStep = editing ? allSteps(workflow).find((step) => step.id === editing) : undefined;
  return (
    <>
      <Section
        title="What it does"
        action={
          <button type="button" className={linkButton} onClick={onShowDetails}>
            <PencilIcon className="h-3 w-3" />
            Edit the steps
          </button>
        }
      >
        <PlainStepList workflow={workflow} onOpenStep={setEditing} openStepId={editing} />
        <button type="button" className={`${linkButton} mt-3`} onClick={() => setChart(!chart)}>
          {chart ? "Hide the flowchart" : "Show the flowchart"}
        </button>
        {chart && (
          <div className="mt-3">
            <WorkflowCanvas workflow={workflow} plain onOpenStep={setEditing} openStepId={editing} />
          </div>
        )}
      </Section>
      {editingStep && (
        <QuickEditPanel
          key={editingStep.id}
          workflow={workflow}
          step={editingStep}
          persist={persist}
          onClose={() => setEditing(null)}
          onOpenEditor={() => onOpenStep(editingStep.id)}
        />
      )}
    </>
  );
}

/** What the person gives a run and what it may reach: what they fill in, where it waits for
 * them, and the folders and sites it may touch. */
function NeedsFromYou({
  task,
  workflow,
  persist,
  onShowDetails,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onShowDetails: () => void;
}) {
  const [editingInput, setEditingInput] = useState<string | null>(null);
  const input = workflow.inputs.find((i) => i.name === editingInput);

  return (
    <Section title="What it needs from you">
      <div className="flex flex-col gap-4">
        <Inputs workflow={workflow} filled={filledBy(task)} onChange={setEditingInput} />
        <Waits workflow={workflow} />
        <div>
          <div className="mb-1 text-[13px] text-[var(--muted)]">It may touch</div>
          <WorkflowPermissions
            workflow={workflow}
            triggerId={task.trigger_id}
            version={JSON.stringify(task.permissions ?? {})}
            className=""
            simple
          />
        </div>
      </div>
      {input && (
        <InputQuickPanel
          key={input.name}
          workflow={workflow}
          input={input}
          persist={persist}
          onClose={() => setEditingInput(null)}
          onOpenEditor={onShowDetails}
        />
      )}
    </Section>
  );
}

/** How the task is set up, one tile per question; each opens the tab that changes it. */
function Glance({
  task,
  workflow,
  environment,
  onShowSettings,
  onShowRuns,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  environment: ReactNode;
  onShowSettings: () => void;
  onShowRuns: () => void;
}) {
  const last = latestRun(task);
  const tiles: { label: string; value: ReactNode; open: () => void; title: string }[] = [
    {
      label: "When it runs",
      value: task.schedule.kind === "manual" ? "When you start it" : describeSchedule(task.schedule),
      open: onShowSettings,
      title: "Change when it runs",
    },
    {
      label: "Last run",
      value: last ? (
        <span className="flex min-w-0 items-center gap-1.5">
          <RunStatusIcon status={last.status} />
          <span className="truncate">{capitalize(formatRunTime(last.started_at))}</span>
        </span>
      ) : (
        "Not run yet"
      ),
      open: onShowRuns,
      title: "See its runs",
    },
    {
      label: "If a step stops working",
      value: PLAIN_LABEL[workflow.autonomy ?? neededAutonomy(workflow)],
      open: onShowSettings,
      title: "Change what happens when a step stops working",
    },
    { label: "Workspace", value: environment, open: onShowSettings, title: "See what it may touch" },
  ];
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="task-glance">
      {tiles.map((tile) => (
        <button
          key={tile.label}
          type="button"
          title={tile.title}
          className="group flex min-w-0 cursor-pointer flex-col gap-1 rounded-xl border border-[var(--border)] px-3 py-2.5 text-left transition-colors hover:border-[var(--border-hover)] hover:bg-[var(--card-bg)]"
          onClick={tile.open}
        >
          <span className="flex items-center justify-between gap-2 text-[12px] text-[var(--muted)]">
            {tile.label}
            <ChevronRightIcon className="h-3.5 w-3.5 shrink-0 opacity-50 transition-opacity group-hover:opacity-100" />
          </span>
          <span className="line-clamp-2 min-w-0 text-sm">{tile.value}</span>
        </button>
      ))}
    </div>
  );
}

/** A workflow task's overview, for someone who uses it rather than builds it: one sentence on
 * what it does, how it is set up at a glance, its steps in plain words, what it needs from them
 * and its latest runs. Every control here changes the same settings the other tabs show. */
export function ScheduledTaskSimple({
  task,
  workflow,
  persist,
  onEditSteps,
  onOpenStep,
  onShowSettings,
  onShowRuns,
  runs,
  environment,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onEditSteps: () => void;
  /** Opens a step in the Steps tab's editor, from its quick edit. */
  onOpenStep: (stepId: string) => void;
  onShowSettings: () => void;
  onShowRuns: () => void;
  runs: ReactNode;
  environment: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4" data-testid="task-simple-view">
      <div className="flex flex-col gap-4">
        <TaskOverviewLine triggerId={task.trigger_id} version={task.version ?? 1} />
        <Glance
          task={task}
          workflow={workflow}
          environment={environment}
          onShowSettings={onShowSettings}
          onShowRuns={onShowRuns}
        />
      </div>
      <WhatItDoes workflow={workflow} persist={persist} onShowDetails={onEditSteps} onOpenStep={onOpenStep} />
      <NeedsFromYou task={task} workflow={workflow} persist={persist} onShowDetails={onEditSteps} />
      <section className="rounded-xl border border-[var(--border)] px-4 pb-3 pt-3">{runs}</section>
    </div>
  );
}
