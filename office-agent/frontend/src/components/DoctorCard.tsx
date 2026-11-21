import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { runDoctor } from "../lib/rest";
import type { DoctorCheck } from "../types/session";
import { CheckIcon, CloseIcon } from "./icons";

type Report = { status: "running" } | { status: "done"; checks: DoctorCheck[] } | { status: "failed"; message: string };

const ORDER: Record<DoctorCheck["state"], number> = { problem: 0, off: 1, ok: 2 };

/** /doctor: runs the checks and holds the card that shows them above the message box. */
export function useDoctor(onOpenSettings: (page: NonNullable<DoctorCheck["page"]>) => void): {
  run: () => void;
  card: ReactNode;
} {
  const [report, setReport] = useState<Report | null>(null);
  // A second /doctor while one runs, or after the card closed, must not show the older answer.
  const runId = useRef(0);
  const run = useCallback(() => {
    const id = ++runId.current;
    setReport({ status: "running" });
    runDoctor()
      .then((result) => id === runId.current && setReport({ status: "done", checks: result.checks }))
      .catch((error: unknown) => id === runId.current && setReport({ status: "failed", message: String(error) }));
  }, []);
  const close = () => {
    runId.current += 1;
    setReport(null);
  };
  const card = report && (
    <DoctorCard
      report={report}
      onClose={close}
      onOpenSettings={(page) => {
        close();
        onOpenSettings(page);
      }}
    />
  );
  return { run, card };
}

function DoctorCard({
  report,
  onClose,
  onOpenSettings,
}: {
  report: Report;
  onClose: () => void;
  onOpenSettings: (page: NonNullable<DoctorCheck["page"]>) => void;
}) {
  // On an empty conversation the box sits mid-window, so the card may only use the room above it.
  const ref = useRef<HTMLElement>(null);
  const [room, setRoom] = useState<number | null>(null);
  useEffect(() => {
    const measure = () => {
      const box = ref.current?.parentElement?.getBoundingClientRect();
      if (box) setRoom(Math.max(160, box.top - 24));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const checks = report.status === "done" ? [...report.checks].sort((a, b) => ORDER[a.state] - ORDER[b.state]) : [];
  const problems = checks.filter((check) => check.state === "problem").length;
  const summary =
    report.status === "running"
      ? "Checking…"
      : report.status === "failed"
        ? "Could not run"
        : problems
          ? `${problems} ${problems === 1 ? "problem" : "problems"}`
          : "Everything works";
  return (
    <section
      ref={ref}
      style={room === null ? undefined : { maxHeight: `min(60vh, ${room}px)` }}
      aria-label="Coscribe check"
      className="absolute bottom-full left-0 right-0 z-20 mb-2 flex max-h-[60vh] flex-col overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--bg)] shadow-[var(--shadow)]"
    >
      <header className="flex items-center gap-2 border-b border-[var(--border)] px-4 py-2.5">
        <h2 className="text-sm font-medium">Coscribe check</h2>
        <span
          className={`text-xs ${report.status === "done" ? (problems ? "text-[var(--danger)]" : "text-[var(--success)]") : "text-[var(--muted)]"}`}
        >
          {summary}
        </span>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="ml-auto rounded-md p-1 text-[var(--muted)] hover:bg-[var(--card-bg)] hover:text-[var(--fg)]"
        >
          <CloseIcon className="h-4 w-4" />
        </button>
      </header>
      {report.status === "running" && (
        <p role="status" className="flex items-center gap-2.5 px-4 py-4 text-sm text-[var(--muted)]">
          <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)] motion-reduce:animate-none" />
          Asking the model and looking for Python, Node.js, Office or LibreOffice, a browser and the sandbox.
        </p>
      )}
      {report.status === "failed" && <p className="px-4 py-4 text-sm text-[var(--danger)]">{report.message}</p>}
      {checks.length > 0 && (
        <ul className="min-h-0 overflow-y-auto p-1.5">
          {checks.map((check) => (
            <CheckRow key={check.id} check={check} onOpenSettings={onOpenSettings} />
          ))}
        </ul>
      )}
    </section>
  );
}

function CheckRow({ check, onOpenSettings }: { check: DoctorCheck; onOpenSettings: (page: NonNullable<DoctorCheck["page"]>) => void }) {
  const page = check.page;
  return (
    <li className="flex items-start gap-3 rounded-lg px-2.5 py-2">
      <StateMark state={check.state} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-sm ${check.state === "off" ? "text-[var(--muted)]" : ""}`}>{check.name}</span>
        </div>
        <p className="text-xs leading-snug text-[var(--muted)] [overflow-wrap:anywhere]">{check.detail}</p>
        {check.state !== "ok" && (check.fix || page) && (
          <p className="mt-1 flex flex-wrap items-center gap-x-2 text-xs">
            {check.fix && <span>{check.fix}</span>}
            {page && (
              <button type="button" onClick={() => onOpenSettings(page)} className="text-[var(--accent)] hover:underline">
                Open Settings
              </button>
            )}
          </p>
        )}
      </div>
    </li>
  );
}

function StateMark({ state }: { state: DoctorCheck["state"] }) {
  if (state === "ok")
    return (
      <span aria-label="Works" className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-[var(--success)]">
        <CheckIcon className="h-3 w-3" />
      </span>
    );
  if (state === "problem")
    return (
      <span aria-label="Problem" className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-[var(--danger)] text-[11px] font-semibold text-white">
        !
      </span>
    );
  return <span aria-label="Not set up" className="mt-0.5 h-[18px] w-[18px] shrink-0 rounded-full border-2 border-[var(--border-hover)]" />;
}
