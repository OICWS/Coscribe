import { useState } from "react";
import { patchScheduledTask } from "../../lib/rest";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import type { HealFixes } from "../../types/workflow";

const VALUE = "rounded bg-[var(--card-bg)] px-1 text-[var(--fg)]";

/** A heal fixes a step for its run only; saving its named changes means the next run doesn't
 * heal the same change again (decision 0030). Nothing is saved until the person asks. */
export function HealFixesSection({
  triggerId,
  fixes,
  onSaved,
  revising,
  onRevise,
}: {
  triggerId: string;
  fixes: HealFixes;
  onSaved: () => void;
  /** A conversation already looks into this run (the run view links to it). */
  revising: boolean;
  /** Opens a conversation that drafts a revision for the heals no fix keeps. */
  onRevise?: () => Promise<string | null>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const revision = fixes.workflow;
  const savedNow = saved && !revision;
  if (!revision && !savedNow && fixes.left.length === 0) return null;

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

  const revise = async () => {
    if (!onRevise) return;
    setSaving(true);
    const problem = await onRevise();
    setSaving(false);
    if (problem) setError(problem);
  };

  return (
    <div className="mt-2 flex flex-col gap-1.5" data-testid="heal-fixes">
      {savedNow && <div className="text-[13px]" data-testid="heal-fixes-saved">Saved into the task.</div>}
      {revision && (
        <>
          <div className="text-[13px]">Keep these fixes so the next run doesn't need healing:</div>
          {fixes.fixes.map((fix) => (
            <div key={`${fix.step_id}:${fix.name}`} className="text-[13px] text-[var(--muted)]">
              {fix.title}: {fix.name} <code className={VALUE}>{fix.was}</code> →{" "}
              <code className={VALUE}>{fix.now}</code>
            </div>
          ))}
          <div>
            <button type="button" className={primaryButton} disabled={saving} onClick={save}>
              {saving ? "Saving…" : "Save into the task"}
            </button>
          </div>
        </>
      )}
      {fixes.left.length > 0 && (
        <>
          <div className="text-[13px] text-[var(--muted)]">
            Not saved, because the heal changed more than a setting of the step:{" "}
            {fixes.left.map((item) => item.title).join(", ")}.
          </div>
          {!revising && onRevise && (
            <div>
              <button type="button" className={secondaryButton} disabled={saving} onClick={revise}>
                Ask for a revision
              </button>
            </div>
          )}
        </>
      )}
      {error && <div className="text-[13px] text-red-500">{error}</div>}
    </div>
  );
}
