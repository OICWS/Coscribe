import { useState } from "react";
import { ChevronRightIcon, TerminalIcon } from "./icons";

// Mirrors conversation/subagents.py's background_report.
export const BACKGROUND_REPORT_PREFIX = "[Background task finished]";
const HEADER_RE = /^\[Background task finished\] "(.*?)" \(task \w+\) (.*?)\.(?: The end of its output:| It printed nothing\.)?\s*/s;

interface ParsedReport {
  description: string;
  outcome: string;
  output: string;
}

function badge(outcome: string): string | null {
  if (outcome === "finished") return null;
  if (outcome.startsWith("ran out of time")) return "Timed out";
  if (outcome.startsWith("was stopped")) return "Stopped by you";
  if (outcome.startsWith("was cut off")) return "Cut off";
  const code = /exit code (-?\d+)/.exec(outcome)?.[1];
  return code ? `Failed (exit ${code})` : "Failed";
}

function parseReport(text: string): ParsedReport | null {
  const match = HEADER_RE.exec(text);
  if (!match) return null;
  return { description: match[1], outcome: match[2], output: text.slice(match[0].length).trim() };
}

/** Stands in for the message a background script's or command's end sends the
 * conversation -- the app sent it, not the user. */
export function BackgroundTaskReportCard({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const parsed = parseReport(text);
  const label = parsed ? badge(parsed.outcome) : null;
  return (
    <div className="rounded-xl border border-[var(--border)]">
      <button
        type="button"
        aria-expanded={open}
        className="flex w-full items-center gap-2.5 rounded-xl px-4 py-2.5 text-left text-sm hover:bg-[var(--card-bg)]"
        onClick={() => setOpen((v) => !v)}
      >
        <TerminalIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
        <span className="min-w-0 flex-1 truncate">
          Background task {label ? "ended" : "finished"}: <span className="text-[var(--muted)]">{parsed?.description ?? ""}</span>
        </span>
        {label && <span className="shrink-0 text-xs text-[var(--danger)]">{label}</span>}
        <ChevronRightIcon className={`h-4 w-4 shrink-0 text-[var(--muted)] transition-transform motion-reduce:transition-none ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap border-t border-[var(--border)] px-4 py-3 font-mono text-xs [overflow-wrap:anywhere]">
          {parsed ? parsed.output || "It printed nothing." : text}
        </pre>
      )}
    </div>
  );
}
