import { useEffect, useState } from "react";
import type { ScheduledRun } from "../../types/settings";
import type { RunReport } from "../../types/workflow";
import { memoryPreview } from "../../lib/memoryWords";
import { AUTONOMY_LABEL } from "./AutonomySetting";
import { HealFixesSection } from "./HealFixesSection";

function where(iteration: number[]): string {
  return iteration.length
    ? ` · item ${iteration.map((i) => i + 1).join(".")}`
    : "";
}

/** Cached input is billed far below new tokens, so a total alone overstates the cost. */
export function tokenLine(tokens: number, cached?: number): string {
  if (!cached) return `${tokens.toLocaleString()} tokens`;
  return `${(tokens - cached).toLocaleString()} new tokens (+${cached.toLocaleString()} cached)`;
}

/** The steps an agent healed while running, and how to keep their fixes (decision 0030). */
function HealedSection({
  report,
  triggerId,
  run,
  onSaved,
  onInvestigate,
}: {
  report: RunReport;
  triggerId: string;
  run: ScheduledRun;
  onSaved: () => void;
  onInvestigate?: (model: string | null) => Promise<string | null>;
}) {
  return (
    <div>
      <div className="font-medium">Healed while running</div>
      {report.healed.map((item, index) => (
        <div key={index} className="text-[13px]">
          {item.title}
          {where(item.iteration)}: {item.did}
          <span className="text-[var(--muted)]">
            {item.carried ? " -- the same fix as an earlier item" : ` -- it had failed: ${item.error}`}
          </span>
        </div>
      ))}
      <HealFixesSection
        triggerId={triggerId}
        fixes={report.fixes}
        onSaved={onSaved}
        revising={Boolean(run.investigation)}
        onRevise={onInvestigate && (() => onInvestigate(null))}
      />
    </div>
  );
}

const HOW: Record<NonNullable<RunReport["recovered"]>[number]["how"], string> = {
  skipped: "skipped",
  fallback: "ran the steps in its place",
  item_skipped: "skipped the item",
};

/** What went wrong without stopping the run, and what ran because it stopped (decision 0032). */
function FailuresSection({ report }: { report: RunReport }) {
  const recovered = report.recovered ?? [];
  const retried = report.retried ?? [];
  const after = report.after_failure ?? [];
  const tries = new Map(retried.map((item) => [`${item.step_id}:${item.iteration.join(".")}`, item.attempts]));
  const triesOf = (item: { step_id: string; iteration: number[] }) => {
    const count = tries.get(`${item.step_id}:${item.iteration.join(".")}`);
    return count ? ` after ${count} tries` : "";
  };
  const worked = retried.filter((item) => item.worked);
  return (
    <>
      {recovered.length > 0 && (
        <div data-testid="report-recovered">
          <div className="font-medium">Failed without stopping the run</div>
          {recovered.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}: {HOW[item.how]}
              {triesOf(item)}
              {item.error && <span className="text-[var(--muted)]"> -- {item.error}</span>}
            </div>
          ))}
        </div>
      )}
      {worked.length > 0 && (
        <div>
          <div className="font-medium">Worked when tried again</div>
          {worked.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}: on try {item.attempts}
            </div>
          ))}
        </div>
      )}
      {after.length > 0 && (
        <div>
          <div className="font-medium">Ran because the run failed</div>
          {after.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {item.status === "failed" ? (
                <span className="text-[var(--danger)]"> -- it failed too: {item.error}</span>
              ) : (
                <span className="text-[var(--muted)]"> -- done</span>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** The values no person gave: what an agent assumed, and the asks that went on with their
 * defaults because no one answered (decision 0033). */
function DecidedSection({ report }: { report: RunReport }) {
  return (
    <>
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
      {report.unanswered.length > 0 && (
        <div>
          <div className="font-medium">No one answered, went on with the defaults</div>
          {report.unanswered.map((item, index) => (
            <div key={index} className="text-[13px]">
              {item.title}
              {where(item.iteration)}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

const TASK_ENDED: Record<string, string> = { done: "done", failed: "stopped", running: "not finished" };

/** The tasks its steps ran, and the version of each it ran (decision 0035). */
function TasksSection({ report }: { report: RunReport }) {
  const tasks = report.tasks ?? [];
  if (tasks.length === 0) return null;
  return (
    <div data-testid="report-tasks">
      <div className="font-medium">Tasks it ran</div>
      {tasks.map((item) => (
        <div key={item.step_id} className="text-[13px]">
          “{item.name}”{item.version ? ` · version ${item.version}` : ""}
          <span className="text-[var(--muted)]"> -- {TASK_ENDED[item.status ?? ""] ?? "not reached"}</span>
        </div>
      ))}
    </div>
  );
}

/** What the run keeps for the next one (decision 0034): only a run that finished keeps it. */
function RememberedSection({ report, kept }: { report: RunReport; kept: boolean }) {
  const remembered = report.remembered ?? [];
  if (remembered.length === 0) return null;
  return (
    <div>
      <div className="font-medium">{kept ? "Kept for the next run" : "Not kept: the run didn't finish"}</div>
      {remembered.map((item) => (
        <div key={item.step_id} className="min-w-0 truncate text-[13px]">
          {item.label || item.name}: <span className="text-[var(--muted)]">{memoryPreview(item.value)}</span>
        </div>
      ))}
    </div>
  );
}

/** What a finished run did (decision 0030), so a run is trusted by its result. */
export function RunReportCard({
  triggerId,
  run,
  onInvestigate,
}: {
  triggerId: string;
  run: ScheduledRun;
  onInvestigate?: (model: string | null) => Promise<string | null>;
}) {
  const [report, setReport] = useState<RunReport | null>(null);
  const [loads, setLoads] = useState(0);
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
  }, [triggerId, run.run_id, run.status, loads]);
  if (!report) return null;
  const versions = report.versions ?? [];
  const usage = [
    versions.length ? `version ${versions.join(", ")}` : null,
    report.tool_calls ? `${report.tool_calls} agent tool calls` : null,
    report.tokens ? tokenLine(report.tokens, report.cached_tokens) : null,
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
          {loop.skipped ? `, ${loop.skipped} skipped` : ""}
        </div>
      ))}
      {report.ended ? (
        <div>Ended at “{report.ended.title}”: nothing to do this time.</div>
      ) : (
        report.not_done.length === 0 && (report.recovered ?? []).length === 0 && <div>Every step was done.</div>
      )}
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
      <TasksSection report={report} />
      <FailuresSection report={report} />
      <DecidedSection report={report} />
      <RememberedSection report={report} kept={run.status === "completed"} />
      {report.healed.length > 0 && (
        <HealedSection
          report={report}
          triggerId={triggerId}
          run={run}
          onSaved={() => setLoads((n) => n + 1)}
          onInvestigate={onInvestigate}
        />
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
