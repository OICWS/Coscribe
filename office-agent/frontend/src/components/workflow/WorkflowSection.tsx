import { useState, type ReactNode } from "react";
import type { Workflow } from "../../types/workflow";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { ViewToggle } from "./ViewToggle";
import { WorkflowEditor, type Persist } from "./WorkflowEditor";

/** A tab after the workflow's own two, such as a saved task's settings. */
export interface ExtraTab {
  view: string;
  label: string;
  content: ReactNode;
}

/** A workflow on its task or draft page: the canvas to look at, or the
 * editor, and any `tabs` the page adds. Clicking a step on the canvas opens it in the editor. */
export function WorkflowSection({
  workflow,
  persist,
  focusStepId,
  tabs = [],
}: {
  workflow: Workflow;
  persist: Persist;
  focusStepId?: string | null;
  tabs?: ExtraTab[];
}) {
  const views = [
    { view: "canvas", label: "Overview" },
    { view: "edit", label: "Edit steps" },
    ...tabs.map(({ view, label }) => ({ view, label })),
  ];
  const [view, setView] = useState<string>(focusStepId ? "edit" : "canvas");
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
      <ViewToggle label="Workflow view" views={views} value={view} onChange={setView} />
      {view === "canvas" && (
        <WorkflowCanvas
          workflow={workflow}
          onOpenStep={(stepId) => {
            setFocus(stepId);
            setView("edit");
          }}
        />
      )}
      {view === "edit" && <WorkflowEditor workflow={workflow} persist={persist} focusStepId={focus} />}
      {tabs.find((tab) => tab.view === view)?.content}
    </div>
  );
}
