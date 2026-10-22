import { lazy, Suspense } from "react";
import type { ProgressItem } from "../lib/workflowProgress";
import { useDockPanel } from "./dock/dockContext";
import { TaskList } from "./TaskList";

const Markdown = lazy(() => import("./Markdown").then((m) => ({ default: m.Markdown })));

/** The plan in a panel of its own, like Browser: the plan the model last
 * proposed, rendered, and the task list it is working through. */
export function PlanPanel({ tasks, plan, busy }: { tasks: ProgressItem[]; plan: string | null; busy: boolean }) {
  const dock = useDockPanel();
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-12 shrink-0 items-center gap-2 px-3" {...dock.headerProps}>
        <span className="min-w-0 flex-1 truncate px-1 text-[15px]">Plan</span>
        {dock.controls}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6 pt-2">
        {plan !== null && (
          <section className="mb-6">
            <Suspense fallback={<p className="whitespace-pre-wrap text-sm">{plan}</p>}>
              <div className="plan-doc">
                <Markdown text={plan} />
              </div>
            </Suspense>
          </section>
        )}
        {tasks.length > 0 && (
          <section>
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Tasks</h2>
            <TaskList tasks={tasks} strike live={busy} />
          </section>
        )}
        {plan === null && tasks.length === 0 && <p className="text-sm text-[var(--muted)]">No plan in this conversation yet.</p>}
      </div>
    </div>
  );
}
