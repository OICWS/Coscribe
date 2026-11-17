import { useEffect, useState } from "react";
import { pickGreeting } from "../lib/greetings";
import { getConfig } from "../lib/rest";

export function EmptyState() {
  const greeting = pickGreeting(new Date(), "");
  return (
    <div className="flex h-full items-center justify-center px-4">
      <h1 className="gradient-text text-xl font-semibold">{greeting}</h1>
    </div>
  );
}

/** An investigation starts in the background; it is a handoff, not a new chat greeting. */
export function InvestigationHandoff({ error }: { error: string | null }) {
  return (
    <div role="status" aria-live="polite" className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
      {error ? (
        <>
          <p className="text-sm font-medium text-[var(--fg)]">Couldn't hand off to AI</p>
          <p className="max-w-lg text-sm text-[var(--muted)]">{error}</p>
        </>
      ) : (
        <>
          <span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--fg)] motion-reduce:animate-none" />
          <p className="text-sm font-medium text-[var(--fg)]">Handing off to AI…</p>
          <p className="text-xs text-[var(--muted)]">Preparing to investigate the failed run</p>
        </>
      )}
    </div>
  );
}

// Module-level so it outlives the heading, which remounts each time home opens.
let lastShown = "";

/** The new-conversation heading above the centered message box. */
export function HomeGreeting() {
  // Picked once per mount, after the name is known, so the line doesn't change once shown.
  const [greeting, setGreeting] = useState("");
  useEffect(() => {
    getConfig()
      .then((config) => config.COSCRIBE_USER_NAME ?? "")
      .catch(() => "")
      .then((name) => {
        lastShown = pickGreeting(new Date(), name, Math.random, lastShown);
        setGreeting(lastShown);
      });
  }, []);
  return (
    <h1
      className="mb-7 px-4 text-center text-[40px] font-normal leading-tight text-[var(--fg)]"
      style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
    >
      {greeting}
    </h1>
  );
}
