import type { ConnectorToolPolicy } from "../../../types/settings";
import { ArrowLeftIcon } from "../../icons";
import { ConnectorIcon } from "../ConnectorIcon";
import { primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { ConnectorMenu } from "./ConnectorMenu";
import { findPinnedNpmPackage } from "./helpers";
import { NoticeText } from "./NoticeText";
import { ToolGroup } from "./ToolPolicies";
import type { ConnectorRow, Notice } from "./types";

/** An added connector: its tools and what each may do, and Disconnect. */
export function ConnectorDetail({
  row,
  pending,
  notice,
  onBack,
  onDisconnect,
  onReconnect,
  onSignIn,
  onCheckUpdate,
  onApplyUpdate,
  onPolicies,
}: {
  row: ConnectorRow;
  pending: boolean;
  notice: Notice | null;
  onBack: () => void;
  onDisconnect: () => void;
  onReconnect: () => void;
  onSignIn: () => void;
  onCheckUpdate: (pkg: string) => void;
  onApplyUpdate: (pkg: string, version: string) => void;
  onPolicies: (policies: Record<string, ConnectorToolPolicy>) => void;
}) {
  const info = row.serverInfo!;
  const pinned = findPinnedNpmPackage(info.args ?? []);
  const source = info.server_url ?? `${info.command ?? ""} ${(info.args ?? []).join(" ")}`.trim();
  const tools = info.tools ?? [];
  return (
    <div className="flex flex-col gap-5">
      <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
        <ArrowLeftIcon className="h-4 w-4" /> Your connectors
      </button>
      <div className="flex items-center gap-4">
        <ConnectorIcon name={row.name} title={row.title} size="md" />
        <div className="min-w-0 flex-1 truncate text-lg font-semibold">{row.title}</div>
        <button type="button" className={secondaryButtonClass} onClick={onDisconnect}>
          Disconnect
        </button>
        <ConnectorMenu
          pinned={pinned !== null}
          onReconnect={onReconnect}
          onCheckUpdate={() => pinned && onCheckUpdate(pinned.name)}
        />
      </div>
      <div className="flex flex-col gap-1">
        {row.catalogEntry && <p className="text-[15px] leading-relaxed">{row.catalogEntry.description}</p>}
        <p className="truncate font-mono text-xs text-[var(--muted)]" title={source}>
          {source}
        </p>
      </div>

      {notice && !(notice.signin && info.signin) && <NoticeText notice={notice} onApplyUpdate={onApplyUpdate} />}

      {!info.connected ? (
        <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] px-4 py-3 text-sm">
          <span className="flex-1 text-[var(--muted)]">
            {pending
              ? "Connecting…"
              : info.secret_error
                ? info.secret_error
                : info.signin
                  ? "Waiting for you to sign in in your browser."
                  : info.auth === "oauth"
                    ? (info.signin_error ?? "Not signed in. Its tools show up here once you sign in.")
                    : "Not connected. Its tools show up here once it connects."}
          </span>
          {info.signin && (
            <a href={info.signin.url} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">
              Open the sign-in page
            </a>
          )}
          {info.signin ? (
            <button type="button" className={secondaryButtonClass} disabled={pending} onClick={onSignIn}>
              Start over
            </button>
          ) : (
            <>
              <button type="button" className={secondaryButtonClass} disabled={pending} onClick={onReconnect}>
                Retry
              </button>
              {info.auth === "oauth" && (
                <button type="button" className={primaryButtonClass} disabled={pending} onClick={onSignIn}>
                  Sign in
                </button>
              )}
            </>
          )}
        </div>
      ) : (
        <section className="flex flex-col">
          <h3 className="text-[15px] font-semibold">Tool permissions</h3>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Choose when Coscribe is allowed to use these tools. Needs approval follows the conversation's own mode.
          </p>
          <div className="mt-3 flex flex-col divide-y divide-[var(--border)]">
            <ToolGroup title="Read-only tools" tools={tools.filter((t) => t.read_only)} onChange={onPolicies} />
            <ToolGroup title="Write/delete tools" tools={tools.filter((t) => !t.read_only)} onChange={onPolicies} />
          </div>
        </section>
      )}
    </div>
  );
}
