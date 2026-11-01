import { toolLabel } from "../../lib/toolLabels";
import { formatValue, stepOutput, wholeReference } from "../../lib/workflowLabels";
import type { AgentStep, Condition, Match, WorkflowStep } from "../../types/workflow";
import { ConditionText, VarToken } from "./parts";

function Conditions({
  conditions,
  match,
  inputNames,
}: {
  conditions: Condition[];
  match: Match | undefined;
  inputNames: Set<string>;
}) {
  return (
    <>
      {conditions.map((condition, index) => (
        <span key={index} className="inline-flex items-baseline gap-1.5">
          {index > 0 && <span>{match === "any" ? "or" : "and"}</span>}
          <ConditionText condition={condition} inputNames={inputNames} />
        </span>
      ))}
    </>
  );
}

const ARG_PREVIEW_CHARS = 32;

function Irreversible({ on }: { on: boolean }) {
  return on ? <span className="text-[var(--warning)]">· can’t be undone</span> : null;
}

function Arrow({ output, inputNames }: { output: string | null; inputNames: Set<string> }) {
  if (!output) return null;
  return (
    <>
      <span aria-label="saved as">→</span>
      <VarToken name={output} isInput={inputNames.has(output)} />
    </>
  );
}

export function ArgPreview({ value, inputNames }: { value: unknown; inputNames: Set<string> }) {
  const ref = wholeReference(value);
  if (ref) return <VarToken name={ref} isInput={inputNames.has(ref.split(".")[0])} />;
  const text = formatValue(value).replace(/\s+/g, " ");
  return (
    <span className="font-mono text-[12px] text-[var(--fg)]">
      {text.length > ARG_PREVIEW_CHARS ? `${text.slice(0, ARG_PREVIEW_CHARS)}…` : text}
    </span>
  );
}

const SCOPE = { high: "Any tool", full: "The whole task" };

function AgentSummary({
  step,
  output,
  inputNames,
}: {
  step: AgentStep;
  output: string | null;
  inputNames: Set<string>;
}) {
  const scope =
    step.autonomy === "bounded"
      ? `${step.tools.length} ${step.tools.length === 1 ? "tool" : "tools"}`
      : SCOPE[step.autonomy];
  return (
    <>
      <span>{scope}</span>
      {step.fields.length > 0 && (
        <>
          <span>· returns</span>
          <span className="font-mono text-[12px] text-[var(--fg)]">{step.fields.map((f) => f.name).join(", ")}</span>
        </>
      )}
      <Irreversible on={step.irreversible} />
      <Arrow output={output} inputNames={inputNames} />
    </>
  );
}

function Chosen({ name, missing, inputNames }: { name: string; missing: string; inputNames: Set<string> }) {
  if (!name) return <span className="text-[var(--danger)]">{missing} not chosen yet</span>;
  return <VarToken name={name} isInput={inputNames.has(name.split(".")[0])} />;
}

export function StepSummary({ step, inputNames }: { step: WorkflowStep; inputNames: Set<string> }) {
  const output = stepOutput(step);
  if (step.kind === "tool") {
    const shown = Object.entries(step.args)
      .filter(([, value]) => typeof value === "string")
      .slice(0, 2);
    return (
      <>
        <span>{toolLabel(step.tool)}</span>
        {shown.map(([key, value]) => (
          <span key={key} className="inline-flex items-baseline gap-1">
            <span className="text-[var(--muted)]">{key}</span>
            <ArgPreview value={value} inputNames={inputNames} />
          </span>
        ))}
        <Irreversible on={step.irreversible} />
        <Arrow output={output} inputNames={inputNames} />
      </>
    );
  }
  if (step.kind === "script") {
    const lines = step.code.split("\n").length;
    return (
      <>
        <span>
          Python · {lines} {lines === 1 ? "line" : "lines"}
        </span>
        {Object.values(step.inputs).map((value, index) => (
          <ArgPreview key={index} value={value} inputNames={inputNames} />
        ))}
        <Arrow output={output} inputNames={inputNames} />
      </>
    );
  }
  if (step.kind === "llm") {
    return (
      <>
        <span>Returns</span>
        <span className="font-mono text-[12px] text-[var(--fg)]">{step.fields.map((f) => f.name).join(", ")}</span>
        <Arrow output={output} inputNames={inputNames} />
      </>
    );
  }
  if (step.kind === "agent") return <AgentSummary step={step} output={output} inputNames={inputNames} />;
  if (step.kind === "check") {
    return (
      <>
        <Conditions conditions={step.conditions} match={step.match} inputNames={inputNames} />
        <span>· otherwise stop</span>
      </>
    );
  }
  if (step.kind === "branch") {
    return (
      <>
        <span>If</span>
        <Conditions conditions={step.conditions} match={step.match} inputNames={inputNames} />
      </>
    );
  }
  if (step.kind === "choice") {
    return (
      <>
        <span>Goes by</span>
        <Chosen name={step.value} missing="a value" inputNames={inputNames} />
        <span>· {step.cases.map((c) => `“${c.is}”`).join(", ")}, or anything else</span>
      </>
    );
  }
  if (step.kind === "loop") {
    return (
      <>
        <span>For each</span>
        <VarToken name={step.item} isInput={false} />
        <span>in</span>
        <Chosen name={step.over} missing="a list" inputNames={inputNames} />
        {step.collect && (
          <>
            <span>· keeps</span>
            <VarToken name={step.collect} isInput={false} />
          </>
        )}
        <Arrow output={output} inputNames={inputNames} />
      </>
    );
  }
  return (
    <>
      <span>Pauses for your approval</span>
      {step.when.length > 0 && (
        <span className="inline-flex items-baseline gap-1.5">
          · only when <Conditions conditions={step.when} match={step.match} inputNames={inputNames} />
        </span>
      )}
    </>
  );
}
