import { useState } from "react";
import type { Workflow } from "../../types/workflow";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { WorkflowEditor, type Persist } from "./WorkflowEditor";

type View = "canvas" | "edit";

const VIEWS: { view: View; label: string }[] = [
  { view: "canvas", label: "Overview" },
  { view: "edit", label: "Edit steps" },
];

/** A workflow on its task or draft page: the canvas to look at, or the
 * editor. Clicking a step on the canvas opens it in the editor. */
export function WorkflowSection({
  workflow,
  persist,
  focusStepId,
}: {
  workflow: Workflow;
  persist: Persist;
  focusStepId?: string | null;
}) {
  const [view, setView] = useState<View>(focusStepId ? "edit" : "canvas");
  const [focus, setFocus] = useState<string | null>(focusStepId ?? null);
  // A run's "Edit step" sets a new focus while the page is open.
  const [seenFocus, setSeenFocus] = useState(focusStepId);
  if (focusStepId !== seenFocus) {
    setSeenFocus(focusStepId);
    if (focusStepId) {
      setView("edit");
      setFocus(focusStepId);
    }
  }
  return (
    <div className="flex flex-col gap-3">
      <div
        role="group"
        aria-label="Workflow view"
        className="flex gap-1 self-start rounded-lg bg-[var(--card-bg)] p-0.5"
      >
        {VIEWS.map((item) => (
          <button
            key={item.view}
            type="button"
            aria-pressed={view === item.view}
            className={`h-7 rounded-md px-3 text-[13px] ${
              view === item.view ? "bg-[var(--bg)] font-medium shadow-sm" : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
            onClick={() => setView(item.view)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {view === "canvas" ? (
        <WorkflowCanvas
          workflow={workflow}
          onOpenStep={(stepId) => {
            setFocus(stepId);
            setView("edit");
          }}
        />
      ) : (
        <WorkflowEditor workflow={workflow} persist={persist} focusStepId={focus} />
      )}
    </div>
  );
}
