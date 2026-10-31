import { useEffect, useState } from "react";
import type { ScheduledRun } from "../../types/settings";
import type { RunReport } from "../../types/workflow";
import { AUTONOMY_LABEL } from "./AutonomySetting";

function where(iteration: number[]): string {
  return iteration.length
    ? ` · item ${iteration.map((i) => i + 1).join(".")}`
    : "";
}

/** What a finished run did (decision 0030), so a run is trusted by its result. */
export function RunReportCard({
  triggerId,
  run,
}: {
  triggerId: string;
  run: ScheduledRun;
}) {
  const [report, setReport] = useState<RunReport | null>(null);
  useEffect(() => {
    if (run.status === "running") return;
    let live = true;
    fetch(`/api/scheduled-tasks/${triggerId}/runs/${run.run_id}/report`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data: RunReport | null) => live && setReport(data))
      .catch(() => live && setReport(null));
    return () => {
      live = false;
    };
  }, [triggerId, run.run_id, run.status]);
  if (!report) return null;
  const usage = [
    report.tool_calls ? `${report.tool_calls} agent tool calls` : null,
    report.tokens ? `${report.tokens.toLocaleString()} tokens` : null,
  ].filter(Boolean);
  return (
    <section
      className="flex flex-col gap-2 rounded-xl border border-[var(--border)] px-4 py-3 text-sm"
      data-testid="run-report"
    >
      <div className="text-[13px] text-[var(--muted)]">
        Report · {AUTONOMY_LABEL[report.autonomy]}
        {usage.length > 0 && ` · ${usage.join(" · ")}`}
      </div>
      {report.loops.map((loop) => (
        <div key={loop.step_id}>
          {loop.title}: {loop.done} of {loop.total} done
        </div>
      ))}
      {report.not_done.length > 0 && (
        <div>
          <div className="font-medium">Not done</div>
          {report.not_done.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}
              {item.error && (
                <span className="text-[var(--muted)]"> -- {item.error}</span>
              )}
            </div>
          ))}
        </div>
      )}
      {report.assumed.length > 0 && (
        <div>
          <div className="font-medium">Decided by the agent</div>
          {report.assumed.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}: {item.values.join("; ")}
            </div>
          ))}
        </div>
      )}
      {report.irreversible.length > 0 && (
        <div>
          <div className="font-medium">Done, can't be undone</div>
          {report.irreversible.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
