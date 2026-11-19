import { useId, useState } from "react";
import { neededAutonomy } from "../../lib/workflowLabels";
import type { TaskAutonomy, Workflow } from "../../types/workflow";

export const AUTONOMY_LABEL: Record<TaskAutonomy, string> = {
  fixed: "Fixed",
  self_healing: "Self-healing",
  proactive: "Proactive",
  autonomous: "Autonomous",
};

// One line each, in what the person would notice: what happens when a step stops working.
const SUMMARY: Record<TaskAutonomy, string> = {
  fixed: "Only the saved steps run. If one fails, the run stops and tells you.",
  self_healing: "If a website changed, AI does that step on the page as it is now.",
  proactive: "AI steps decide how to do their part. If a step fails, AI may add a few steps; any that change something wait for you.",
  autonomous: "AI may do the whole task its own way.",
};

const LEVELS = Object.keys(AUTONOMY_LABEL) as TaskAutonomy[];

function Option({
  checked,
  disabled,
  name,
  line,
  onPick,
}: {
  checked: boolean;
  disabled?: boolean;
  name: string;
  line: string;
  onPick: () => void;
}) {
  const lineId = useId();
  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      aria-label={name}
      aria-describedby={lineId}
      disabled={disabled}
      onClick={onPick}
      className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        checked
          ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_8%,transparent)]"
          : "border-[var(--border)] hover:border-[var(--border-hover)]"
      }`}
    >
      <span
        className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
          checked ? "border-[var(--accent)]" : "border-[var(--border-hover)]"
        }`}
      >
        {checked && <span className="h-2 w-2 rounded-full bg-[var(--accent)]" />}
      </span>
      <span className="min-w-0">
        <span className="block text-[13px] font-medium">{name}</span>
        <span id={lineId} className="block text-[13px] text-[var(--muted)]">
          {line}
        </span>
      </span>
    </button>
  );
}

/** The task's one autonomy switch (decision 0030): a ceiling on its steps, which saving checks.
 * A level below what its steps need would refuse to save, so it can't be picked. */
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
  const needed = neededAutonomy(workflow);
  return (
    <fieldset className="flex flex-col gap-2" data-testid="autonomy-setting">
      <legend className="sr-only">Autonomy</legend>
      <div className="flex flex-col gap-1.5" role="radiogroup" aria-label="Autonomy">
        <Option
          checked={current === null}
          name="Match the steps"
          line={`Allow what its steps need (now ${AUTONOMY_LABEL[needed]}), and follow them as they change.`}
          onPick={() => void choose(null)}
        />
        {LEVELS.map((level) => (
          <Option
            key={level}
            checked={current === level}
            disabled={LEVELS.indexOf(level) < LEVELS.indexOf(needed)}
            name={AUTONOMY_LABEL[level]}
            line={SUMMARY[level]}
            onPick={() => void choose(level)}
          />
        ))}
      </div>
      {problem && <p className="text-[13px] text-[var(--danger)]">{problem}</p>}
    </fieldset>
  );
}

export const PLAIN_LABEL: Record<TaskAutonomy, string> = {
  fixed: "Stop and tell me",
  self_healing: "Work around small website changes",
  proactive: "Let its AI steps decide how",
  autonomous: "Let AI do the whole task",
};
