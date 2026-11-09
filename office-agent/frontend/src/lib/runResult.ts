import type { ScheduledRun } from "../types/settings";
import type { StepRecord, Workflow } from "../types/workflow";
import { everyStep, placeSteps } from "./workflowTree";

// What a run got, as the simple view's result card says it (decision 0038). Everything comes from
// the run's own records: no model reads the run again.

// Shorter than this is a value (a count, a name), not something written for the person to read.
const MIN_TEXT = 40;

function longestText(value: unknown): string | null {
  if (typeof value === "string") return value.trim().length >= MIN_TEXT ? value.trim() : null;
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  let found: string | null = null;
  for (const field of Object.values(value)) {
    const text = typeof field === "string" ? field.trim() : "";
    if (text.length >= MIN_TEXT && text.length > (found?.length ?? 0)) found = text;
  }
  return found;
}

/** The text the run wrote for the person: the longest text the last finished AI step handed on.
 * A task that only fills a file or a form has none. */
export function runResultText(workflow: Workflow, run: ScheduledRun): { stepId: string; text: string } | null {
  const writers = new Set(
    placeSteps(everyStep(workflow))
      .filter(({ step }) => step.kind === "llm" || step.kind === "agent")
      .map(({ step }) => step.id),
  );
  const done = run.steps
    .filter((record) => record.status === "done" && writers.has(record.step_id))
    .sort((a, b) => (a.finished_at ?? "").localeCompare(b.finished_at ?? ""));
  for (const record of done.reverse()) {
    const text = longestText(record.output);
    if (text) return { stepId: record.step_id, text };
  }
  return null;
}

/** The step a run is at, stopped at or waits at, by what its record says. A failure inside a
 * block fails the block too: the one that failed first is where it stopped. */
export function runAt(run: ScheduledRun): StepRecord | undefined {
  const wanted: Partial<Record<ScheduledRun["status"], StepRecord["status"]>> = {
    failed: "failed",
    needs_approval: "waiting",
    waiting: "waiting",
    running: "running",
    stopped: "running",
  };
  const status = wanted[run.status];
  const found = run.steps.filter((record) => record.status === status && !record.recovered);
  if (status !== "failed") return found.at(-1);
  // A block's record comes before the steps inside it, so a tie goes to the later one.
  return found.reduce<StepRecord | undefined>(
    (first, record) => (first && (first.finished_at ?? "") < (record.finished_at ?? "") ? first : record),
    undefined,
  );
}

const HOW: Record<NonNullable<StepRecord["recovered"]>, string> = {
  skipped: "failed and was skipped",
  fallback: "failed, so other steps ran in its place",
  item_skipped: "failed on an item, which was skipped",
  added: "failed, so the run added steps to do it",
};

/** What went differently without stopping the run: a failure it went past, a step that took
 * more than one try. Said once per step, however many items it ran for. */
export function runNotes(run: ScheduledRun, title: (stepId: string) => string): string[] {
  const notes = new Map<string, string>();
  for (const record of run.steps) {
    if (record.recovered) notes.set(`r:${record.step_id}`, `“${title(record.step_id)}” ${HOW[record.recovered]}`);
    else if (record.status === "done" && (record.attempts ?? 1) > 1) {
      const tries = record.attempts === 2 ? "once" : `${(record.attempts ?? 1) - 1} times`;
      notes.set(`t:${record.step_id}`, `Tried “${title(record.step_id)}” again ${tries} before it worked`);
    }
  }
  return [...notes.values()];
}

/** A file the run wrote, as a name and the folder it is in. */
export function fileParts(path: string): { name: string; folder: string } {
  const name = path.split(/[\\/]/).filter(Boolean).pop() ?? path;
  // The folder as the person's system writes it, so a Windows path keeps its backslashes.
  return { name, folder: path.slice(0, path.lastIndexOf(name)).replace(/[\\/]+$/, "") };
}

// The failures people meet most, said the way they'd say them; the full error stays in Details.
const PLAIN_ERRORS: [RegExp, (match: RegExpMatchArray) => string][] = [
  [
    /No such file or directory:? ?'?([^'\n]*)'?/i,
    (m) => (m[1] ? `There is no file ${fileParts(m[1]).name}` : "A file it needs isn't there"),
  ],
  [
    /net::ERR_(NAME_NOT_RESOLVED|CONNECTION_REFUSED|INTERNET_DISCONNECTED|CONNECTION_TIMED_OUT|ADDRESS_UNREACHABLE)/,
    () => "The page couldn't be reached",
  ],
  [/^Not allowed: |declined|You said no/i, () => "You said no to a step, so it stopped there"],
  [/time(d)? ?out|ran too long|didn't appear in time/i, () => "It took too long and was stopped"],
];

/** Why a run stopped, in one line. */
export function plainError(error: string | null | undefined): string | null {
  if (!error) return null;
  for (const [pattern, say] of PLAIN_ERRORS) {
    const match = error.match(pattern);
    if (match) return say(match);
  }
  const first =
    error
      .split("\n")
      .find((line) => line.trim())
      ?.trim() ?? "";
  return first.length > 200 ? `${first.slice(0, 199)}…` : first;
}
