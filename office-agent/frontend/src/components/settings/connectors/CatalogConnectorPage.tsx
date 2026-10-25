import { useState } from "react";
import type { McpCatalogEntry, McpServerInfo } from "../../../types/settings";
import { ArrowLeftIcon, CheckIcon, ExternalLinkIcon } from "../../icons";
import { friendlySignInError } from "../../../lib/connectorSetup";
import { ConnectorIcon } from "../ConnectorIcon";
import { ConnectorSetup } from "../ConnectorSetup";
import { primaryButtonClass, secondaryButtonClass } from "../SettingRow";
import { findPinnedNpmPackage } from "./helpers";
import { NoticeText } from "./NoticeText";
import type { Notice } from "./types";

const TOOLS_SHOWN = 18;

const PENDING_BUTTON = "inline-flex min-w-[5.5rem] items-center justify-center disabled:opacity-100";
const SPINNER =
  "h-4 w-4 animate-spin rounded-full border-2 border-[color-mix(in_srgb,var(--primary-fg)_30%,transparent)] border-t-[var(--primary-fg)] motion-reduce:animate-none";

const infoLabel = "text-xs font-medium uppercase tracking-wide text-[var(--muted)]";

function ExternalLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex w-fit items-center gap-1 text-[var(--accent)] underline-offset-2 hover:underline"
    >
      {children}
      <ExternalLinkIcon className="h-3.5 w-3.5" />
    </a>
  );
}

/** A connector from Discover that isn't added yet: what it is, what it can
 * do, who makes it, and Connect. */
export function CatalogConnectorPage({
  entry,
  info,
  pending,
  notice,
  appSaved,
  redirectUri,
  onSetupChanged,
  onBack,
  onConnect,
  onSignIn,
  onManage,
  onDisconnect,
}: {
  entry: McpCatalogEntry;
  /** Set once the connector was added. */
  info: McpServerInfo | null;
  pending: boolean;
  notice: Notice | null;
  /** Whether the app this service needs (if any) has been registered and saved. */
  appSaved: boolean;
  redirectUri: string;
  onSetupChanged: () => void;
  onBack: () => void;
  onConnect: () => void;
  onSignIn: () => void;
  onManage: () => void;
  onDisconnect: () => void;
}) {
  const title = entry.title ?? entry.name;
  const pkg = findPinnedNpmPackage(entry.args ?? []);
  const tools = entry.tools ?? [];
  const [allTools, setAllTools] = useState(false);
  const shown = allTools ? tools : tools.slice(0, TOOLS_SHOWN);
  const needsSetup = entry.setup !== undefined && !appSaved;
  const showError = (text: string) => (entry.setup ? friendlySignInError(text, entry.setup, redirectUri) : text);
  const address = entry.server_url ?? (pkg ? `${pkg.name} ${pkg.version}` : `${entry.command ?? ""} ${(entry.args ?? []).join(" ")}`);
  return (
    <div className="flex flex-col gap-6">
      <button type="button" className="flex w-fit items-center gap-2 text-[15px] text-[var(--fg)] hover:opacity-70" onClick={onBack}>
        <ArrowLeftIcon className="h-4 w-4" /> Connectors
      </button>
      <div className="flex items-center gap-5 rounded-xl bg-[var(--card-bg)] px-6 py-6">
        <ConnectorIcon name={entry.name} title={title} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="text-2xl font-semibold">{title}</div>
          <div className="mt-1 text-[15px] text-[var(--muted)]">{entry.description}</div>
        </div>
        {info?.connected && !pending ? (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2 text-sm text-[var(--muted)]">
              <CheckIcon className="h-4 w-4" /> Connected
            </span>
            <button type="button" className={secondaryButtonClass} onClick={onManage}>
              Manage
            </button>
            <button type="button" className={secondaryButtonClass} onClick={onDisconnect}>
              Disconnect
            </button>
          </div>
        ) : info?.signin ? (
          <div className="flex items-center gap-2">
            <button type="button" className={secondaryButtonClass} onClick={onSignIn}>
              Start over
            </button>
            <button type="button" className={secondaryButtonClass} onClick={onDisconnect}>
              Cancel
            </button>
          </div>
        ) : info && !pending ? (
          <div className="flex items-center gap-2">
            <button type="button" className={primaryButtonClass} onClick={info.auth === "oauth" ? onSignIn : onConnect}>
              {info.auth === "oauth" ? "Sign in" : "Reconnect"}
            </button>
            <button type="button" className={secondaryButtonClass} onClick={onDisconnect}>
              Remove
            </button>
          </div>
        ) : needsSetup ? (
          <button
            type="button"
            className={primaryButtonClass}
            onClick={() => document.getElementById(`setup-${entry.name}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
          >
            Set up
          </button>
        ) : (
          <button
            type="button"
            disabled={pending}
            className={`${primaryButtonClass} ${pending ? PENDING_BUTTON : ""}`}
            onClick={onConnect}
          >
            {pending ? <span role="status" aria-label="Connecting" className={SPINNER} /> : "Connect"}
          </button>
        )}
      </div>
      {info?.signin ? (
        <p role="status" className="text-sm text-[var(--muted)]">
          Waiting for you to sign in in your browser.{" "}
          <a href={info.signin.url} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">
            Open the sign-in page
          </a>
        </p>
      ) : info && !info.connected && !pending ? (
        <p role="status" className="text-sm text-[var(--danger)]">
          {showError(info.secret_error ?? info.signin_error ?? "Not connected.")}
        </p>
      ) : (
        notice && <NoticeText notice={{ ...notice, text: notice.error ? showError(notice.text) : notice.text }} />
      )}
      {entry.setup && (
        <ConnectorSetup entry={entry} setup={entry.setup} saved={appSaved} redirectUri={redirectUri} onChanged={onSetupChanged} />
      )}
      {entry.about && <p className="max-w-[46rem] text-[15px] leading-relaxed">{entry.about}</p>}

      <section>
        <h3 className="flex items-center gap-2 text-xl font-semibold">
          Tools
          {tools.length > 0 && (
            <span className="rounded-md bg-[var(--card-bg)] px-1.5 text-xs font-normal text-[var(--muted)]">{tools.length}</span>
          )}
        </h3>
        {tools.length > 0 ? (
          <>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {shown.map((tool) => (
                <span key={tool} className="truncate rounded-lg bg-[var(--card-bg)] px-3 py-1.5 text-[13px]" title={tool}>
                  {tool}
                </span>
              ))}
            </div>
            {tools.length > TOOLS_SHOWN && (
              <button
                type="button"
                className="mt-3 text-sm text-[var(--accent)] hover:underline"
                onClick={() => setAllTools((v) => !v)}
              >
                {allTools ? "Show fewer" : `Show all ${tools.length}`}
              </button>
            )}
            <p className="mt-3 text-xs text-[var(--muted)]">
              {entry.tools_from === "service"
                ? "As the service reported them when it was last connected."
                : "From the maker's documentation. Once connected, this page lists what the service offers now."}{" "}
              The connector's own page lets you choose which tools may run.
            </p>
          </>
        ) : (
          <p className="mt-2 text-sm text-[var(--muted)]">
            The maker doesn't publish a list. Once you connect, the service reports its tools and they show here.
          </p>
        )}
      </section>

      <div className="grid grid-cols-1 gap-x-12 gap-y-6 border-t border-[var(--border)] pt-6 text-sm sm:grid-cols-2">
        {entry.made_by && (
          <div className="flex flex-col gap-1">
            <div className={infoLabel}>Made by</div>
            {entry.homepage ? <ExternalLink href={entry.homepage}>{entry.made_by}</ExternalLink> : <div>{entry.made_by}</div>}
          </div>
        )}
        <div className="flex flex-col gap-1">
          <div className={infoLabel}>{entry.server_url ? "Connector URL" : pkg ? "Package" : "Command"}</div>
          <div className="break-all font-mono text-[13px]">{address}</div>
        </div>
        {entry.category && (
          <div className="flex flex-col gap-1">
            <div className={infoLabel}>Category</div>
            <span className="w-fit rounded-lg border border-[var(--border)] px-2.5 py-1 text-[13px]">{entry.category}</span>
          </div>
        )}
        <div className="flex flex-col gap-1">
          <div className={infoLabel}>Sign-in</div>
          <div>{entry.auth === "oauth" ? "Required. You sign in on the service's own page, in your browser." : "Not required"}</div>
        </div>
        {entry.links && entry.links.length > 0 && (
          <div className="flex flex-col gap-1">
            <div className={infoLabel}>More info</div>
            {entry.links.map((link) => (
              <ExternalLink key={link.url} href={link.url}>
                {link.label}
              </ExternalLink>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
