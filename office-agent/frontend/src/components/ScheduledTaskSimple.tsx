import type { ReactNode } from "react";
import { patchScheduledTask } from "../lib/rest";
import { describeSchedule } from "../lib/scheduleLabels";
import type { ScheduledTask } from "../types/settings";
import type { Workflow } from "../types/workflow";
import { AutonomyChoice } from "./workflow/AutonomySetting";
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

function Inputs({ workflow }: { workflow: Workflow }) {
  if (workflow.inputs.length === 0) return null;
  return (
    <Section title="Asks you for, each time it runs">
      <ul className="flex flex-col gap-1 text-sm">
        {workflow.inputs.map((input) => (
          <li key={input.name}>
            {input.label || input.name}
            {input.required === false && <span className="text-[var(--muted)]"> (optional)</span>}
            {input.default !== null && input.default !== "" && (
              <span className="text-[var(--muted)]">
                {" "}
                · usually <span className="break-all">{String(input.default)}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}

/** A workflow task's page for someone who uses it rather than builds it: what it does in its
 * steps' own titles, when it runs, what happens when a step stops working and what it may touch.
 * Every control here changes the same settings the detailed view shows. */
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
  /** Opens a step of the canvas in the detailed view's editor. */
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
      <Section
        title="What it does"
        action={
          <button type="button" className={linkButton} onClick={onShowDetails}>
            See or edit the steps
          </button>
        }
      >
        <WorkflowCanvas workflow={workflow} plain onOpenStep={onOpenStep} />
      </Section>
      <Inputs workflow={workflow} />
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
    </div>
  );
}
