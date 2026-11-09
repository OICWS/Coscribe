import { useState } from "react";
import { patchScheduledTask } from "../../lib/rest";
import { primaryButton } from "../../lib/formStyles";
import type { RunReport } from "../../types/workflow";

/** Steps the run added because a step failed (decision 0042). They held for that run only; the
 * person may keep them as the step's fallback, so the next run doesn't have to plan them again. */
export function AddedStepsSection({
  triggerId,
  report,
  onSaved,
}: {
  triggerId: string;
  report: RunReport;
  onSaved: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const added = report.added ?? [];
  const revision = report.added_fix?.workflow ?? null;
  if (added.length === 0) return null;

  const save = async () => {
    if (!revision) return;
    setSaving(true);
    const result = await patchScheduledTask(triggerId, { workflow: revision });
    setSaving(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setSaved(true);
    onSaved();
  };

  // A step failing on several items reused one plan: show it once.
  const shown = added.filter((item, index) => added.findIndex((a) => a.step_id === item.step_id) === index);
  return (
    <div data-testid="report-added">
      <div className="font-medium">Steps the run added</div>
      {shown.map((item) => (
        <div key={item.step_id} className="text-[13px]">
          {item.title}: {item.why || "it failed, so the run added steps to do it"}
          <div className="text-[var(--muted)]">Added: {item.steps.map((step) => step.title ?? "").join(", ")}</div>
        </div>
      ))}
      {saved && !revision && <div className="text-[13px]">Saved into the task.</div>}
      {revision && (
        <div className="mt-1.5 flex flex-col gap-1.5">
          <div className="text-[13px]">
            Keep them as what the step does when it fails, so the next run doesn't add them again:
          </div>
          <div>
            <button type="button" className={primaryButton} disabled={saving} onClick={save}>
              {saving ? "Saving…" : "Save into the task"}
            </button>
          </div>
        </div>
      )}
      {error && <div className="text-[13px] text-red-500">{error}</div>}
    </div>
  );
}
