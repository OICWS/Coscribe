import { useEffect, useState } from "react";
import { inputClass } from "../../lib/formStyles";
import { getTaskOverview, setTaskOverview, type TaskOverview } from "../../lib/rest";

/** The one sentence a task's simple view opens with. The server writes it once per saved version
 * (so the first look at a new version waits a moment) and keeps one the person wrote. */
export function TaskOverviewLine({ triggerId, version }: { triggerId: string; version: number }) {
  // Kept with the version it was read for, so a newer version shows as loading, not stale.
  const key = `${triggerId}:${version}`;
  const [loaded, setLoaded] = useState<{ key: string; overview: TaskOverview } | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    getTaskOverview(triggerId)
      .then((overview) => live && setLoaded({ key, overview }))
      .catch(() => live && setLoaded({ key, overview: { text: null } }));
    return () => {
      live = false;
    };
  }, [triggerId, key]);
  const overview = loaded?.key === key ? loaded.overview : null;

  const save = async (text: string) => {
    setDraft(null);
    setLoaded({ key, overview: await setTaskOverview(triggerId, text) });
  };

  if (draft !== null)
    return (
      <form
        className="flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void save(draft);
        }}
      >
        <input
          aria-label="What this task does"
          autoFocus
          maxLength={300}
          className={`${inputClass} min-w-0 flex-1`}
          value={draft}
          placeholder="Empty: Coscribe writes one"
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="text-[13px] font-medium hover:underline">
          Save
        </button>
        <button
          type="button"
          className="text-[13px] text-[var(--muted)] hover:underline"
          onClick={() => setDraft(null)}
        >
          Cancel
        </button>
      </form>
    );
  if (overview === null)
    return (
      <p className="animate-pulse text-[15px] text-[var(--muted)]" data-testid="task-overview">
        Describing what this task does…
      </p>
    );
  return (
    <p className="text-[15px] leading-relaxed" data-testid="task-overview">
      {overview.text ?? <span className="text-[var(--muted)]">No description yet.</span>}{" "}
      <button
        type="button"
        aria-label="Edit what the task says it does"
        className="text-[13px] text-[var(--muted)] hover:text-[var(--fg)] hover:underline"
        onClick={() => setDraft(overview.text ?? "")}
      >
        {overview.text ? "Change" : "Write one"}
      </button>
    </p>
  );
}
