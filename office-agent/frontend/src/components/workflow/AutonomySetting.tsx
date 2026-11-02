import { useState } from "react";
import { neededAutonomy } from "../../lib/workflowLabels";
import type { TaskAutonomy, Workflow } from "../../types/workflow";

export const AUTONOMY_LABEL: Record<TaskAutonomy, string> = {
  fixed: "Fixed",
  self_healing: "Self-healing",
  proactive: "Proactive",
  autonomous: "Autonomous",
};

const DESCRIPTION: Record<TaskAutonomy, string> = {
  fixed:
    "Only the saved steps run. A failure a step doesn’t handle stops the run, and a fix is proposed for you to save.",
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

const PLAIN_LABEL: Record<TaskAutonomy, string> = {
  fixed: "Stop and tell me",
  self_healing: "Work around small website changes",
  proactive: "Let its AI steps decide how",
  autonomous: "Let AI do the whole task",
};

const PLAIN_DESCRIPTION: Record<TaskAutonomy, string> = {
  fixed: "The run stops where the step failed. You can ask Coscribe to suggest a fix from the run's page.",
  self_healing:
    "When a website changed and a step no longer fits it, Coscribe does that step on the page as it is now and tells you what it did. Anything that can't be undone waits for your OK.",
  proactive: "As above, and its AI steps may work out their part, using only the tools and sites they were given.",
  autonomous: "Coscribe's AI may do the whole task its own way.",
};

/** The same switch in plain words, for the task page's simple view. A task without the setting
 * acts at the lowest level its steps need, so that is what it shows; a level below that would
 * refuse to save, so it can't be picked. */
export function AutonomyChoice({
  workflow,
  persist,
}: {
  workflow: Workflow;
  persist: (next: Workflow) => Promise<string | null>;
}) {
  const [problem, setProblem] = useState<string | null>(null);
  const needed = neededAutonomy(workflow);
  const current = workflow.autonomy ?? needed;
  return (
    <div className="flex flex-col gap-1.5" data-testid="autonomy-choice">
      <select
        aria-label="If a step stops working"
        className="self-start rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-sm"
        value={current}
        onChange={async (e) =>
          setProblem(
            await persist({
              ...workflow,
              autonomy: e.target.value as TaskAutonomy,
            }),
          )
        }
      >
        {LEVELS.map((level) => (
          <option key={level} value={level} disabled={LEVELS.indexOf(level) < LEVELS.indexOf(needed)}>
            {PLAIN_LABEL[level]}
          </option>
        ))}
      </select>
      <p className="text-[13px] text-[var(--muted)]">{PLAIN_DESCRIPTION[current]}</p>
      {problem && <p className="text-[13px] text-[var(--danger)]">{problem}</p>}
    </div>
  );
}
