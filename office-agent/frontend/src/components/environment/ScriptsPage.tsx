import type { ScriptsDraft } from "./drafts";

export function ScriptsPage({ draft }: { draft: ScriptsDraft }) {
  const failed = draft.status?.state === "failed";
  return (
    <section className="flex flex-col gap-3">
      <p className="text-[13px] leading-relaxed text-[var(--muted)]">
        Whether scripts run at all, the Python they use and the isolation check on this computer are in Settings ›
        Capabilities. {draft.summary === "Isolated" ? "Here, scripts run isolated to this conversation's folders." : ""}
      </p>
      {failed && (
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border)] px-4 py-3">
          <input
            type="checkbox"
            role="switch"
            className="mt-1 h-4 w-4 shrink-0 accent-[var(--accent)]"
            checked={draft.unisolated}
            onChange={(e) => draft.setUnisolated(e.target.checked)}
          />
          <span className="flex flex-col gap-1">
            <span className="text-[15px] font-medium">Run scripts without isolation</span>
            <span className="text-[13px] leading-relaxed text-[var(--muted)]">
              The isolation check failed on this computer, so scripts are off. This turns them on in this conversation
              only: a script then runs as you and can reach anything you can. You still approve each one, and turning
              this on is recorded in the audit log.
            </span>
          </span>
        </label>
      )}
    </section>
  );
}
