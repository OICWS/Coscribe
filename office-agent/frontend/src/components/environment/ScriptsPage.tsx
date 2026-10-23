import type { ScriptsDraft } from "./drafts";
import { secondaryButtonClass } from "../settings/SettingRow";

/** The check that differed, as the person reads it. */
const CHECK_WORDS: Record<string, string> = {
  "write inside": "Couldn't write inside its own folders",
  "delete inside": "Could delete a file",
  "write outside": "Could change a file outside its folders",
  "read outside": "Could read a file outside its folders",
  network: "Reached the network with it turned off",
  "start a script in isolation": "The check couldn't start a script in isolation",
};

export function ScriptsPage({ draft }: { draft: ScriptsDraft }) {
  const { status, testing } = draft;
  const failed = status?.state === "failed";
  return (
    <section className="flex flex-col gap-3">
      <p className="text-[13px] leading-relaxed text-[var(--muted)]">
        Scripts coscribe writes run in a locked-down space on Windows: they can use only this conversation's folders,
        can't delete or rename files there, and can't reach the rest of this computer. A check on this computer decides
        whether that holds.
      </p>
      <div
        className={`flex flex-col gap-2 rounded-xl border px-4 py-3 ${
          failed ? "border-[var(--warning)] bg-[var(--card-bg)]" : "border-[var(--border)]"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="flex-1 text-[15px] font-medium">
            {status === null || testing
              ? "Checking isolation on this computer…"
              : status.state === "passed"
                ? "Scripts run isolated on this computer"
                : status.state === "unsupported"
                  ? "Isolation is only available on Windows"
                  : status.state === "untested"
                    ? "Not checked on this computer yet"
                    : "Isolation doesn't work on this computer, so scripts are off"}
          </span>
          {status !== null && status.state !== "unsupported" && (
            <button type="button" className={secondaryButtonClass} disabled={testing} onClick={() => void draft.retest()}>
              {status.state === "untested" ? "Test now" : "Test again"}
            </button>
          )}
        </div>
        {failed && !testing && (
          <p className="text-[13px] leading-relaxed">
            {CHECK_WORDS[status.failed] ?? status.failed}. Security software or a company policy can cause this.
          </p>
        )}
      </div>
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
              In this conversation only. A script then runs as you and can reach anything you can. You still approve
              each one, and turning this on is recorded in the audit log.
            </span>
          </span>
        </label>
      )}
    </section>
  );
}
