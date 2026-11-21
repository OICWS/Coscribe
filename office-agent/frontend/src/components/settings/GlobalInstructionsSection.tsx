import { useEffect, useState } from "react";
import { getMemory, updateMemory } from "../../lib/rest";
import { SettingRow, fieldClass, secondaryButtonClass } from "./SettingRow";

/** They go into every conversation's instructions, so they are kept short. */
const LIMIT = 2000;

type Status = { text: string; error: boolean };

/** Direct editor for MEMORY.md's content, the preferences injected into
 * every conversation's instructions. Saved as you type, once typing
 * pauses, like the rest of Settings; the Settings window shows the result
 * in its own corner. Text already over the limit stays as it is until the
 * person shortens it: nothing over the limit is saved, and nothing is cut. */
export function GlobalInstructionsSection({ active, onStatus }: { active: boolean; onStatus: (status: Status) => void }) {
  const [content, setContent] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [loadError, setLoadError] = useState(false);
  const over = draft.length > LIMIT;

  useEffect(() => {
    if (!active || loaded) return;
    getMemory()
      .then((res) => setContent(res.content))
      .catch(() => setLoadError(true))
      .finally(() => setLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, loaded]);

  useEffect(() => {
    if (!editing || draft === content || draft.length > LIMIT) return;
    const timer = window.setTimeout(async () => {
      try {
        await updateMemory(draft);
        setContent(draft);
        onStatus({ text: "Saved", error: false });
      } catch {
        onStatus({ text: "Couldn't save Global instructions -- keep typing to try again.", error: true });
      }
    }, 700);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing, draft, content]);

  const startEditing = () => {
    setDraft(content);
    setEditing(true);
  };

  const stopEditing = () => {
    if (draft !== content && !over)
      void updateMemory(draft).then(
        () => {
          setContent(draft);
          onStatus({ text: "Saved", error: false });
        },
        () => onStatus({ text: "Couldn't save Global instructions.", error: true }),
      );
    setEditing(false);
  };
  // Closing an edit that is over the limit would drop it unsaved.
  const unsavable = over && draft !== content;

  return (
    <div className="flex flex-col">
      <SettingRow
        label="Global instructions"
        description="Preferences, conventions or context Coscribe should always know. Applies to every new conversation."
        control={
          <button
            type="button"
            className={secondaryButtonClass}
            disabled={editing && unsavable}
            title={editing && unsavable ? `Shorten to ${LIMIT.toLocaleString("en-US")} characters to save` : undefined}
            onClick={editing ? stopEditing : startEditing}
          >
            {editing ? "Done" : "Edit"}
          </button>
        }
      />
      {editing && (
        <div className="flex flex-col gap-2 pb-2">
          <textarea
            aria-label="Global instructions"
            className={`${fieldClass} h-auto min-h-36 w-full resize-y py-2.5 leading-relaxed`}
            value={draft}
            placeholder="e.g. Always write dates as YYYY-MM-DD. I prefer decks with no more than 6 bullets per slide."
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
          />
          <div aria-live="polite" className={`flex justify-end gap-3 text-[13px] tabular-nums ${over ? "text-[var(--danger)]" : "text-[var(--muted)]"}`}>
            {over && <span className="mr-auto">Too long to save. Shorten it to {LIMIT.toLocaleString("en-US")} characters.</span>}
            <span>
              {draft.length.toLocaleString("en-US")} / {LIMIT.toLocaleString("en-US")}
            </span>
          </div>
        </div>
      )}
      {loadError && <p className="pb-2 text-[13px] text-[var(--danger)]">Couldn't load Global instructions.</p>}
    </div>
  );
}
