import type { ReactNode } from "react";
import { patchScheduledTask } from "../../lib/rest";
import { describeSchedule } from "../../lib/scheduleLabels";
import type { ScheduledTask } from "../../types/settings";
import type { Workflow } from "../../types/workflow";
import { TaskReachSection } from "../TaskReachSection";
import { TaskVersionsSection } from "../TaskVersionsSection";
import { WebhookSection } from "../TriggerNote";
import { ToggleSwitch } from "../ToggleSwitch";
import { AutonomySetting } from "./AutonomySetting";
import { WorkflowPermissions } from "./WorkflowPermissions";

const linkButton = "text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline";

function Card({
  title,
  hint,
  action,
  children,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border)] p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-medium">{title}</h2>
          {hint && <p className="mt-0.5 text-[13px] text-[var(--muted)]">{hint}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/** Whether a failed run starts a conversation that looks into it. */
function InvestigateRow({ task, onChanged }: { task: ScheduledTask; onChanged: () => void }) {
  const toggle = async () => {
    await patchScheduledTask(task.trigger_id, { auto_investigate: !task.auto_investigate });
    onChanged();
  };
  return (
    <div className="mt-4 flex items-start justify-between gap-4 border-t border-[var(--border)] pt-4">
      <div className="text-sm">
        Look into a failed run automatically
        <span className="block text-[13px] text-[var(--muted)]">
          {task.auto_investigate
            ? "Coscribe reproduces the failure and drafts a fix for you to review. It never saves the fix itself."
            : "The run stops and you get a notification. You can still ask Coscribe to look into it from the run's page."}
        </span>
      </div>
      <ToggleSwitch on={task.auto_investigate ?? false} onClick={toggle} label="Look into failures automatically" />
    </div>
  );
}

/** Every setting of a workflow task in one place, grouped by the question each answers. */
export function TaskSettingsTab({
  task,
  workflow,
  persist,
  onEdit,
  onChanged,
}: {
  task: ScheduledTask;
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
  onEdit: () => void;
  onChanged: () => void;
}) {
  return (
    <div className="flex flex-col gap-4" data-testid="task-settings">
      <Card
        title="When it runs"
        action={
          <button type="button" className={linkButton} onClick={onEdit}>
            Change
          </button>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="text-sm">
            {task.schedule.kind === "manual" ? "Only when you start it" : describeSchedule(task.schedule)}
          </div>
          <WebhookSection task={task} />
        </div>
      </Card>
      <Card title="If a step stops working" hint="How much AI may decide when this task runs.">
        <AutonomySetting workflow={workflow} persist={persist} />
        <InvestigateRow task={task} onChanged={onChanged} />
      </Card>
      <Card
        title="Where it runs and what it may touch"
        hint="Steps run as saved, without asking each time. A run pauses at approval steps, and at anything not allowed here."
      >
        <div className="flex flex-col gap-4">
          <TaskReachSection
            taskId={task.trigger_id}
            changed={JSON.stringify([task.environment, task.permissions?.folders])}
            onChanged={onChanged}
          />
          <WorkflowPermissions
            workflow={workflow}
            triggerId={task.trigger_id}
            version={JSON.stringify(task.permissions ?? {})}
            className=""
          />
        </div>
      </Card>
      <Card title="Versions" hint="Each save keeps the one before, so you can compare or go back.">
        <TaskVersionsSection task={task} onChanged={onChanged} />
      </Card>
    </div>
  );
}
