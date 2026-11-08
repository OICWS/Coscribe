import { type ReactNode, useState } from "react";
import { patchScheduledTask } from "../lib/rest";
import { plainDefault } from "../lib/inputKinds";
import { waitsForYou } from "../lib/plainOutline";
import { plainDetail } from "../lib/plainSteps";
import { describeSchedule } from "../lib/scheduleLabels";
import { neededAutonomy } from "../lib/workflowLabels";
import { allSteps } from "../lib/workflowTree";
import type { ScheduledTask } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { AutonomyChoice, PLAIN_LABEL } from "./workflow/AutonomySetting";
import { PlainStepList, PlainText } from "./workflow/PlainStepList";
import { InputQuickPanel, QuickEditPanel } from "./workflow/QuickEditPanel";
import { TaskOverviewLine } from "./workflow/TaskOverviewLine";
import { WorkflowCanvas } from "./workflow/WorkflowCanvas";
import { WorkflowPermissions } from "./workflow/WorkflowPermissions";

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

const linkButton = "text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline";

/** What fills an input by itself when the task starts on something new: a folder task's file
 * (decision 0034), a connector item's field (decision 0039). Nothing to change there. */
function filledBy(task: ScheduledTask): Record<string, string> {
  const rule = task.schedule;
  if (rule.kind === "folder" && rule.input) return { [rule.input]: "the new file that arrived in the folder" };
  if (rule.kind !== "connector") return {};
  const filled: Record<string, string> = {};
  for (const [name, path] of Object.entries(rule.inputs_from ?? {})) {
    if (path) filled[name] = path === "*" ? "the whole new item" : `the new item's ${path}`;
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
              <li key={input.name} className="flex items-baseline gap-3">
                <span className="min-w-0">
                  {input.label || input.name}
                  <span className="text-[var(--muted)]"> · {filled[input.name]}</span>
                </span>
              </li>
            );
          const usual = plainDefault(input);
          return (
            <li key={input.name} className="flex items-baseline gap-3">
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
              <button type="button" className={linkButton} onClick={() => onChange(input.name)}>
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
            See or edit the steps
          </button>
        }
      >
        <PlainStepList workflow={workflow} onOpenStep={setEditing} openStepId={editing} />
        <button type="button" className={`${linkButton} mt-2`} onClick={() => setChart(!chart)}>
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

/** How the task is set up rather than what it does, folded under one line that sums it up. */
function Settings({
  task,
  workflow,
  persist,
  onEdit,
  onShowDetails,
  onChanged,
  environment,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onEdit: () => void;
  onShowDetails: () => void;
  onChanged: () => void;
  environment: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const when = task.schedule.kind === "manual" ? "Only when you start it" : describeSchedule(task.schedule);
  const failing = PLAIN_LABEL[workflow.autonomy ?? neededAutonomy(workflow)];
  const toggleInvestigate = async () => {
    await patchScheduledTask(task.trigger_id, { auto_investigate: !task.auto_investigate });
    onChanged();
  };
  return (
    <section data-testid="task-settings">
      <button
        type="button"
        aria-expanded={open}
        className="flex w-full items-baseline gap-2 text-left"
        onClick={() => setOpen(!open)}
      >
        <span className={`text-xs text-[var(--muted)] transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
        <h2 className="text-sm font-medium">Settings</h2>
        {!open && (
          <span className="min-w-0 truncate text-[13px] text-[var(--muted)]">
            {when} · When a step stops working: {failing.toLowerCase()} · Version {task.version ?? 1}
          </span>
        )}
      </button>
      {open && (
        <div className="mt-4 flex flex-col gap-6 pl-4">
          <Section
            title="When it runs"
            action={
              <button type="button" className={linkButton} onClick={onEdit}>
                Change
              </button>
            }
          >
            <div className="text-sm">{when}</div>
          </Section>
          <Section title="If a step stops working">
            <AutonomyChoice workflow={workflow} persist={persist} />
            <label className="mt-3 flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={task.auto_investigate ?? false}
                onChange={() => void toggleInvestigate()}
              />
              <span>
                When a run fails, have Coscribe look into it and suggest a fix
                <span className="block text-[13px] text-[var(--muted)]">It never saves the fix without you.</span>
              </span>
            </label>
          </Section>
          <Section title="Where it runs">
            <div className="flex items-center gap-1.5 text-sm">Uses the environment {environment}</div>
          </Section>
          <Section
            title="Versions"
            action={
              (task.version ?? 1) > 1 && (
                <button type="button" className={linkButton} onClick={onShowDetails}>
                  Compare or restore
                </button>
              )
            }
          >
            <div className="text-sm">
              Version {task.version ?? 1} · each save keeps the one before, so you can go back
            </div>
          </Section>
        </div>
      )}
    </section>
  );
}

/** A workflow task's page for someone who uses it rather than builds it: one sentence on what it
 * does, its steps in plain words, what it needs from them and its runs, with how it is set up
 * folded away. Every control here changes the same settings the detailed view shows. */
export function ScheduledTaskSimple({
  task,
  workflow,
  persist,
  onEdit,
  onShowDetails,
  onOpenStep,
  onChanged,
  runs,
  environment,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onEdit: () => void;
  onShowDetails: () => void;
  /** Opens a step in the detailed view's editor, from its quick edit. */
  onOpenStep: (stepId: string) => void;
  onChanged: () => void;
  runs: ReactNode;
  environment: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-7" data-testid="task-simple-view">
      <TaskOverviewLine triggerId={task.trigger_id} version={task.version ?? 1} />
      <WhatItDoes workflow={workflow} persist={persist} onShowDetails={onShowDetails} onOpenStep={onOpenStep} />
      <NeedsFromYou task={task} workflow={workflow} persist={persist} onShowDetails={onShowDetails} />
      {runs}
      <Settings
        task={task}
        workflow={workflow}
        persist={persist}
        onEdit={onEdit}
        onShowDetails={onShowDetails}
        onChanged={onChanged}
        environment={environment}
      />
    </div>
  );
}
