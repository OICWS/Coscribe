import { useContext, useState, type ReactNode, type SVGProps } from "react";
import { primaryButton, secondaryButton } from "../../lib/formStyles";
import { PACKAGE_DECLINE, PACKAGE_INSTALL, type PackageInstallItem } from "../../state/packageInstall";
import { FolderActionsContext } from "../folderActions";
import { CheckCircleIcon, ChevronRightIcon, ExternalLinkIcon, XCircleIcon } from "../icons";

const RUNTIME = {
  python: { label: "Python", tool: "pip", registry: "PyPI", url: (name: string) => `https://pypi.org/project/${encodeURIComponent(name)}/` },
  node: { label: "Node.js", tool: "npm", registry: "npm", url: (name: string) => `https://www.npmjs.com/package/${name}` },
} as const;

type Runtime = (typeof RUNTIME)[keyof typeof RUNTIME];

function PackageIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="m7.5 4.27 9 5.15" />
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <path d="M12 22V12" />
    </svg>
  );
}

/** The part of the spec after the name ("==3.1.2", "@0.33.5"), shown apart from the name. */
function versionPart(item: PackageInstallItem): string {
  return item.package.startsWith(item.name) ? item.package.slice(item.name.length) : "";
}

function Line({ tone, icon, children, title }: { tone: "success" | "muted"; icon: ReactNode; children: ReactNode; title?: string }) {
  return (
    <div
      className={`flex w-full items-center gap-2 rounded-xl border border-[var(--border)] px-3 py-2 text-sm ${tone === "muted" ? "text-[var(--muted)]" : ""}`}
      data-testid="package-install-answered"
      title={title}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{children}</span>
    </div>
  );
}

function Failed({ item }: { item: PackageInstallItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex w-full flex-col gap-2 rounded-xl border border-[color-mix(in_srgb,var(--danger)_45%,var(--border))] px-3 py-2 text-sm" data-testid="package-install-failed">
      <div className="flex items-center gap-2">
        <XCircleIcon className="h-4 w-4 shrink-0 text-[var(--danger)]" />
        <span className="min-w-0 flex-1 truncate">
          Couldn’t install <span className="font-mono text-[13px]">{item.package}</span>
        </span>
        {item.error && (
          <button
            type="button"
            className="flex h-6 items-center gap-1 rounded-md px-1.5 text-xs text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            Details
            <ChevronRightIcon className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-90" : ""}`} />
          </button>
        )}
      </div>
      {open && item.error && (
        <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-[var(--card-bg)] px-2.5 py-2 font-mono text-xs text-[var(--muted)] [overflow-wrap:anywhere]">
          {item.error}
        </pre>
      )}
    </div>
  );
}

/** One line for an answered card: installed, failed (with the installer's output) or not installed. */
function Outcome({ item, runtime }: { item: PackageInstallItem; runtime: Runtime }) {
  if (item.status === "failed") return <Failed item={item} />;
  if (item.status === "installed") {
    const version = item.version ? ` ${item.version}` : versionPart(item);
    return (
      <Line tone="success" icon={<CheckCircleIcon className="h-4 w-4 shrink-0 text-[var(--success)]" />}>
        Installed <span className="font-mono text-[13px]">{item.name}{version}</span>
        <span className="text-[var(--muted)]"> · {runtime.label}</span>
      </Line>
    );
  }
  return (
    <Line tone="muted" icon={<PackageIcon className="h-4 w-4 shrink-0" />} title={item.reply}>
      Didn’t install <span className="font-mono text-[13px]">{item.package}</span>
      {item.reply && <>: “{item.reply}”</>}
    </Line>
  );
}

function PackageTile({ item, runtime }: { item: PackageInstallItem; runtime: Runtime }) {
  const version = versionPart(item);
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--card-bg)] px-3 py-2.5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] font-mono text-[11px] font-semibold text-[var(--accent-ink)]" aria-hidden>
        {runtime.tool}
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-mono text-[13.5px] font-medium" title={item.package}>
          {item.name}
          {version && <span className="font-normal text-[var(--muted)]">{version}</span>}
        </span>
        <span className="truncate text-xs text-[var(--muted)]">
          Into coscribe’s {runtime.label} environment
          {item.installedVersion && ` · ${item.installedVersion} installed now`}
        </span>
      </div>
      <a
        href={runtime.url(item.name)}
        target="_blank"
        rel="noreferrer"
        className="flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-xs text-[var(--accent)] underline-offset-2 hover:underline"
      >
        {runtime.registry}
        <ExternalLinkIcon className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

/** A script needs a package coscribe's environment lacks (decision 0056). Install runs the same
 * installer as Settings › Packages; the card follows it to its end. */
export function PackageInstallCard({ item }: { item: PackageInstallItem }) {
  const actions = useContext(FolderActionsContext);
  const runtime = RUNTIME[item.runtime];
  if (item.status !== "pending" && item.status !== "installing") return <Outcome item={item} runtime={runtime} />;

  const installing = item.status === "installing";
  const answer = (value: string) => actions?.onAnswerPackageInstall(item.id, value);
  return (
    <div
      role="region"
      aria-label={`Install ${item.name}`}
      className="flex w-full flex-col gap-3 rounded-xl border border-[var(--accent)] px-3.5 py-3 text-sm"
      data-waiting={installing ? undefined : item.id}
      data-testid="package-install"
    >
      <div className="flex items-center gap-2.5">
        <PackageIcon className="h-4 w-4 shrink-0" />
        <span className="min-w-0 flex-1 font-medium">Install a {runtime.label} package</span>
        {installing ? (
          <span className="flex shrink-0 items-center gap-1.5 text-[13px] text-[var(--muted)]">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[color-mix(in_srgb,var(--fg)_15%,transparent)] border-t-[var(--accent)]" />
            Installing
          </span>
        ) : (
          <span className="flex shrink-0 items-center gap-1.5 text-[13px] font-medium text-[var(--warning)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--warning)]" />
            Waiting for you
          </span>
        )}
      </div>
      {item.reason && <p className="text-[13px] text-[var(--muted)] [overflow-wrap:anywhere]">{item.reason}</p>}
      <PackageTile item={item} runtime={runtime} />
      {installing ? (
        <div className="flex flex-col gap-2">
          <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--border)]">
            <div className="package-install-bar h-full w-1/3 rounded-full bg-[var(--accent)]" />
          </div>
          <span className="shimmer-text text-xs">
            {runtime.tool} install {item.package} · this can take a minute
          </span>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className={primaryButton} onClick={() => answer(PACKAGE_INSTALL)}>
              Install
            </button>
            <button type="button" className={secondaryButton} onClick={() => answer(PACKAGE_DECLINE)}>
              Not now
            </button>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Installed with {runtime.tool}, as from Settings › Packages. The package’s own setup runs on this computer.
          </p>
        </>
      )}
    </div>
  );
}
