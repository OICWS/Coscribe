import type { Notice } from "./types";

export function NoticeText({ notice, onApplyUpdate }: { notice: Notice; onApplyUpdate?: (pkg: string, version: string) => void }) {
  return (
    <p role="status" className={`text-sm ${notice.error ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>
      {notice.text}{" "}
      {notice.update && onApplyUpdate && (
        <button
          type="button"
          className="text-[var(--accent)] hover:underline"
          onClick={() => onApplyUpdate(notice.update!.pkg, notice.update!.version)}
        >
          Update
        </button>
      )}
      {notice.signin && (
        <a href={notice.signin.url} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">
          Open the sign-in page
        </a>
      )}
    </p>
  );
}
