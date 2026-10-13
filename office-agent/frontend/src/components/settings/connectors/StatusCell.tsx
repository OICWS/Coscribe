import { CheckIcon } from "../../icons";
import type { ConnectorRow } from "./types";

export function StatusCell({ row, pending }: { row: ConnectorRow; pending: boolean }) {
  const info = row.serverInfo;
  if (pending) {
    return <span className="running-wave-ring rounded-md px-2.5 py-1 text-sm">Connecting…</span>;
  }
  if (info?.connected) return <CheckIcon aria-label="Connected" className="h-4 w-4" />;
  if (info?.secret_error) {
    return (
      <span className="text-sm text-[var(--danger)]" title={info.secret_error}>
        Secret problem
      </span>
    );
  }
  if (info?.signin) return <span className="text-sm text-[var(--muted)]">Waiting for sign-in</span>;
  if (info?.auth === "oauth") return <span className="text-sm text-[var(--danger)]">Sign in</span>;
  return <span className="text-sm text-[var(--danger)]">Not connected</span>;
}
