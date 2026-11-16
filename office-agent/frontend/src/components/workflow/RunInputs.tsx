import { formatValue } from "../../lib/workflowLabels";
import type { ScheduledRun } from "../../types/settings";
import type { Workflow } from "../../types/workflow";
import { VarToken } from "./parts";
import { RunEvent } from "./RunEvent";

/** The values this run was given. */
export function RunInputs({ workflow, run }: { workflow: Workflow; run: ScheduledRun }) {
  return (
    <>
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
      <RunEvent run={run} />
    </>
  );
}

/** The sites the run opened, once it is over. */
export function Sites({ run }: { run: ScheduledRun }) {
  if (!run.sites?.length || run.status === "running") return null;
  return (
    <div className="text-[13px] text-[var(--muted)]" data-testid="run-sites">
      Opened: <span className="text-[var(--fg)]">{run.sites.join(", ")}</span>
    </div>
  );
}
