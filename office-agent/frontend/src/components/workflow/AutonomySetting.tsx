import { useState } from "react";
import type { TaskAutonomy, Workflow } from "../../types/workflow";

export const AUTONOMY_LABEL: Record<TaskAutonomy, string> = {
  fixed: "Fixed",
  self_healing: "Self-healing",
  proactive: "Proactive",
  autonomous: "Autonomous",
};

const DESCRIPTION: Record<TaskAutonomy, string> = {
  fixed:
    "Only the saved steps run. A failure stops the run, and a fix is proposed for you to save.",
  self_healing:
    "The saved steps run. A browser step that breaks because the page changed is done by an agent on the page as it is now, and the report says what it did instead. A step that can't be undone waits for your yes.",
  proactive:
    "As Self-healing, and agent steps may work out their part within their tools and sites.",
  autonomous: "An agent may do the whole task.",
};

const LEVELS = Object.keys(AUTONOMY_LABEL) as TaskAutonomy[];

/** The task's one autonomy switch (decision 0030): a ceiling on its steps, which saving checks. */
export function AutonomySetting({
  workflow,
  persist,
}: {
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
}) {
  const [problem, setProblem] = useState<string | null>(null);
  const choose = async (autonomy: TaskAutonomy | null) => {
    setProblem(await persist({ ...workflow, autonomy }));
  };
  const current = workflow.autonomy ?? null;
  return (
    <fieldset className="flex flex-col gap-2" data-testid="autonomy-setting">
      <legend className="mb-1 text-[13px] font-medium">Autonomy</legend>
      <div
        className="flex flex-wrap gap-1.5"
        role="radiogroup"
        aria-label="Autonomy"
      >
        {[null, ...LEVELS].map((level) => (
          <button
            key={level ?? "auto"}
            type="button"
            role="radio"
            aria-checked={current === level}
            onClick={() => void choose(level)}
            className={`rounded-full border px-3 py-1 text-[13px] ${
              current === level
                ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)]"
                : "border-[var(--border)] text-[var(--muted)]"
            }`}
          >
            {level ? AUTONOMY_LABEL[level] : "Match the steps"}
          </button>
        ))}
      </div>
      <p className="text-[13px] text-[var(--muted)]">
        {current
          ? DESCRIPTION[current]
          : "No limit set: the task allows what its steps need. Pick a level to keep it there."}
      </p>
      {problem && <p className="text-[13px] text-[var(--danger)]">{problem}</p>}
    </fieldset>
  );
}
