import { useId, useState } from "react";
import { neededAutonomy } from "../../lib/workflowLabels";
import type { TaskAutonomy, Workflow } from "../../types/workflow";
import { SelectMenu } from "../SelectMenu";

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
      <legend className="mb-1 text-[13px] font-medium">Autonomy</legend>
      <p className="-mt-1 mb-1 text-[13px] text-[var(--muted)]">How much AI may decide when this task runs.</p>
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

const PLAIN_DESCRIPTION: Record<TaskAutonomy, string> = {
  fixed: "The run stops where the step failed. You can ask Coscribe to suggest a fix from the run's page.",
  self_healing:
    "When a website changed and a step no longer fits it, Coscribe does that step on the page as it is now and tells you what it did. Anything that can't be undone waits for your OK.",
  proactive:
    "As above, and its AI steps may work out their part, using only the tools and sites they were given. If a step fails, AI may add a few steps to get past it; any that change something wait for your OK.",
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
      <SelectMenu
        ariaLabel="If a step stops working"
        variant="field"
        className="self-start"
        value={current}
        options={LEVELS.map((level) => ({
          value: level,
          label: PLAIN_LABEL[level],
          disabled: LEVELS.indexOf(level) < LEVELS.indexOf(needed),
        }))}
        onChange={async (autonomy) => setProblem(await persist({ ...workflow, autonomy }))}
      />
      <p className="text-[13px] text-[var(--muted)]">{PLAIN_DESCRIPTION[current]}</p>
      {problem && <p className="text-[13px] text-[var(--danger)]">{problem}</p>}
    </div>
  );
}
