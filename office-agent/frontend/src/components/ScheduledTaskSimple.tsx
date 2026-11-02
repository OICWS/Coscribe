import { type ReactNode, useState } from "react";
import { patchScheduledTask } from "../lib/rest";
import { plainDefault } from "../lib/inputKinds";
import { describeSchedule } from "../lib/scheduleLabels";
import { allSteps } from "../lib/workflowTree";
import type { ScheduledTask } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { AutonomyChoice } from "./workflow/AutonomySetting";
import { InputQuickPanel, QuickEditPanel } from "./workflow/QuickEditPanel";
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

/** `fromFile` names the input a folder task fills with the file that arrived: nothing to change. */
function Inputs({
  workflow,
  fromFile,
  onChange,
}: {
  workflow: Workflow;
  fromFile: string | null;
  onChange: (name: string) => void;
}) {
  if (workflow.inputs.length === 0) return null;
  const onlyTheFile = workflow.inputs.every((input) => input.name === fromFile);
  return (
    <Section title={onlyTheFile ? "Works on" : "Asks you for, each time it runs"}>
      <ul className="flex flex-col gap-1 text-sm">
        {workflow.inputs.map((input) => {
          if (input.name === fromFile)
            return (
              <li key={input.name} className="flex items-baseline gap-3">
                <span className="min-w-0">
                  {input.label || input.name}
                  <span className="text-[var(--muted)]"> · the new file that arrived in the folder</span>
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
    </Section>
  );
}

/** A workflow task's page for someone who uses it rather than builds it: what it does in its
 * steps' own titles, when it runs, what happens when a step stops working and what it may touch.
 * Every control here changes the same settings the detailed view shows. */
/** The steps and what they ask for, each opening its quick edit. */
function WhatItDoes({
  workflow,
  fromFile,
  persist,
  onShowDetails,
  onOpenStep,
}: {
  workflow: Workflow;
  fromFile: string | null;
  persist: (next: Workflow) => Promise<string | null>;
  onShowDetails: () => void;
  onOpenStep: (stepId: string) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [editingInput, setEditingInput] = useState<string | null>(null);
  const input = workflow.inputs.find((i) => i.name === editingInput);
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
        <WorkflowCanvas workflow={workflow} plain onOpenStep={setEditing} openStepId={editing} />
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
      <Inputs workflow={workflow} fromFile={fromFile} onChange={setEditingInput} />
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
    </>
  );
}

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
  const toggleInvestigate = async () => {
    await patchScheduledTask(task.trigger_id, { auto_investigate: !task.auto_investigate });
    onChanged();
  };
  return (
    <div className="flex flex-col gap-7" data-testid="task-simple-view">
      <WhatItDoes
        workflow={workflow}
        fromFile={task.schedule.kind === "folder" ? task.schedule.input || null : null}
        persist={persist}
        onShowDetails={onShowDetails}
        onOpenStep={onOpenStep}
      />
      {runs}
      <Section
        title="When it runs"
        action={
          <button type="button" className={linkButton} onClick={onEdit}>
            Change
          </button>
        }
      >
        <div className="text-sm">
          {task.schedule.kind === "manual" ? "Only when you start it" : describeSchedule(task.schedule)}
        </div>
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
      <Section title="What it may touch">
        <WorkflowPermissions
          workflow={workflow}
          triggerId={task.trigger_id}
          version={JSON.stringify(task.permissions ?? {})}
          className=""
          simple
        />
        <div className="mt-2 flex items-center gap-1.5 text-[13px] text-[var(--muted)]">
          Uses the environment {environment}
        </div>
      </Section>
      {(task.version ?? 1) > 1 && (
        <Section
          title="Versions"
          action={
            <button type="button" className={linkButton} onClick={onShowDetails}>
              Compare or restore
            </button>
          }
        >
          <div className="text-sm">Version {task.version} · each save keeps the one before, so you can go back</div>
        </Section>
      )}
    </div>
  );
}
