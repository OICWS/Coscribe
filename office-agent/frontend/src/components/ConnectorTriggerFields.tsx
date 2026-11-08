import { useEffect, useState } from "react";
import { checkConnectorTool, getTools } from "../lib/rest";
import { connectorLabel } from "../lib/runLabels";
import { MAX_PER_HOUR, type ScheduleForm } from "../lib/scheduleForm";
import { connectorToolLabel } from "../lib/toolLabels";
import type { ConnectorCheckResult, ToolInfo } from "../types/settings";
import type { Workflow, WorkflowInput } from "../types/workflow";
import { SelectMenu } from "./SelectMenu";
import { ArgControl } from "./workflow/StepEditors";

// A task that starts when something new shows up in a connector (decision 0039): which tool to
// ask, with what, and which of the workflow's inputs each new item fills in.

const control = "rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-sm outline-none";
const WHOLE_ITEM = "*";

function plain(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** The field an input takes when the person didn't pick one, as the backend picks it. */
function matchingField(input: WorkflowInput, fields: string[]): string {
  const wanted = new Set([plain(input.name), plain(input.label ?? "")].filter(Boolean));
  return fields.find((path) => wanted.has(plain(path)) || wanted.has(plain(path.split(".").pop() ?? ""))) ?? "";
}

function sample(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 40 ? `${text.slice(0, 39)}…` : text;
}

function ConnectorPicker({
  tools,
  form,
  onChange,
}: {
  tools: ToolInfo[];
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
}) {
  const servers = [...new Set(tools.map((tool) => tool.category.slice(4)))].sort();
  const current = tools.find((tool) => tool.name === form.tool);
  const server = current ? current.category.slice(4) : (servers[0] ?? "");
  const own = tools
    .filter((tool) => tool.category === `mcp:${server}`)
    .sort((a, b) => Number(!a.read_only) - Number(!b.read_only) || a.name.localeCompare(b.name));
  const pick = (tool: string) => onChange({ ...form, tool, args: {}, inputsFrom: {}, trustUnmarked: false });
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-[var(--muted)]">Ask</span>
      <SelectMenu
        ariaLabel="Connector"
        variant="field"
        className="w-40"
        value={server}
        options={servers.map((name) => ({ value: name, label: connectorLabel(name) }))}
        onChange={(name) => pick(tools.find((tool) => tool.category === `mcp:${name}` && tool.read_only)?.name ?? "")}
      />
      <SelectMenu
        ariaLabel="Tool to ask"
        variant="field"
        className="w-64"
        value={form.tool}
        placeholder="Pick what to ask"
        options={own.map((tool) => ({
          value: tool.name,
          label: `${connectorToolLabel(tool.name)}${tool.read_only ? "" : " (may change things)"}`,
        }))}
        onChange={pick}
      />
    </div>
  );
}

function UnmarkedNotice({ form, onChange }: { form: ScheduleForm; onChange: (form: ScheduleForm) => void }) {
  return (
    <label className="flex items-start gap-2 rounded-md border border-[var(--border)] p-2.5 text-[13px]">
      <input
        type="checkbox"
        className="mt-0.5"
        checked={form.trustUnmarked}
        onChange={(e) => onChange({ ...form, trustUnmarked: e.target.checked })}
      />
      <span>
        Its connector doesn't say this tool only reads, so it could change something each time it's asked.{" "}
        <span className="font-medium">It only reads: ask it every few minutes.</span>
      </span>
    </label>
  );
}

function ToolArgs({
  tool,
  form,
  onChange,
}: {
  tool: ToolInfo;
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
}) {
  if (tool.params.length === 0) return null;
  const setArg = (name: string, value: unknown) => {
    const args = { ...form.args };
    if (value === undefined) delete args[name];
    else args[name] = value;
    onChange({ ...form, args });
  };
  return (
    <div className="grid grid-cols-[minmax(0,140px)_minmax(0,1fr)] items-start gap-x-3 gap-y-2">
      {tool.params.map((param) => (
        <div key={param.name} className="contents">
          <label htmlFor={`trigger-arg-${param.name}`} className="pt-1.5 font-mono text-[12.5px] text-[var(--muted)]">
            {param.name}
            {param.required && <span className="text-[var(--danger)]"> *</span>}
          </label>
          <div>
            <ArgControl
              id={`trigger-arg-${param.name}`}
              param={param}
              value={form.args[param.name]}
              onChange={(value) => setArg(param.name, value)}
            />
            {param.description && <p className="mt-1 text-xs text-[var(--muted)]">{param.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

function CheckResult({ result }: { result: ConnectorCheckResult }) {
  if ("error" in result && result.error) {
    return <p className="text-xs text-[var(--danger)]">It couldn't be asked: {result.error}</p>;
  }
  if (!("items" in result) || result.items === null) return null;
  if (result.items.length === 0) return <p className="text-xs text-[var(--muted)]">It has nothing right now.</p>;
  return (
    <div className="text-xs text-[var(--muted)]">
      <p>
        It has {result.count} {result.count === 1 ? "item" : "items"} now
        {(result.count ?? 0) > result.items.length ? `; the first ${result.items.length}:` : ":"}
      </p>
      <ul className="mt-1 list-disc pl-5">
        {result.items.map((entry, index) => (
          <li key={index} className="truncate">
            {entry.title}
          </li>
        ))}
      </ul>
    </div>
  );
}

function InputsFromItem({
  inputs,
  fields,
  form,
  onChange,
}: {
  inputs: WorkflowInput[];
  fields: Record<string, unknown>;
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
}) {
  const paths = Object.keys(fields);
  const saved = Object.values(form.inputsFrom).filter((path) => path && path !== WHOLE_ITEM && !(path in fields));
  const options = [
    { value: "", label: "Its default" },
    { value: WHOLE_ITEM, label: "The whole item" },
    ...[...paths, ...saved].map((path) => ({
      value: path,
      label: path in fields ? `${path} · ${sample(fields[path])}` : path,
    })),
  ];
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm text-[var(--muted)]">Each new item fills in</span>
      <div className="grid grid-cols-[minmax(0,140px)_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5">
        {inputs.map((input) => (
          <div key={input.name} className="contents">
            <span className="truncate text-sm">{input.label || input.name}</span>
            <SelectMenu
              ariaLabel={`${input.label || input.name} from`}
              variant="field"
              value={form.inputsFrom[input.name] ?? matchingField(input, paths)}
              options={options}
              onChange={(path) => onChange({ ...form, inputsFrom: { ...form.inputsFrom, [input.name]: path } })}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

/** The controls a "connector" schedule needs, under the Frequency row. */
export function ConnectorTriggerFields({
  form,
  onChange,
  workflow,
}: {
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
  workflow: Workflow | null;
}) {
  const [tools, setTools] = useState<ToolInfo[] | null>(null);
  const [result, setResult] = useState<ConnectorCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    getTools()
      .then((listed) => setTools(listed.tools.filter((tool) => tool.category.startsWith("mcp:"))))
      .catch(() => setTools([]));
  }, []);
  const tool = tools?.find((entry) => entry.name === form.tool);
  const inputs = workflow?.inputs ?? [];
  const fields = result && "fields" in result ? (result.fields ?? {}) : {};
  const check = async () => {
    setChecking(true);
    const found = await checkConnectorTool(form.tool, form.args, form.trustUnmarked);
    setChecking(false);
    setResult(found);
    // What it found names the fields: an input not picked yet takes the one named like it, saved.
    if ("fields" in found && found.fields) {
      const paths = Object.keys(found.fields);
      const picked = Object.fromEntries(inputs.map((input) => [input.name, matchingField(input, paths)]));
      onChange({ ...form, inputsFrom: { ...picked, ...form.inputsFrom } });
    }
  };
  if (tools === null) return null;
  return (
    <div className="flex w-full flex-col gap-2.5 pl-[6.5rem]">
      {tools.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          No connector is connected. Add one in Settings &gt; Connectors, then come back.
        </p>
      ) : (
        <ConnectorPicker tools={tools} form={form} onChange={onChange} />
      )}
      {tool?.description && <p className="-mt-1 text-xs text-[var(--muted)]">{tool.description}</p>}
      {form.tool && tools.length > 0 && !tool && (
        <p className="text-xs text-[var(--danger)]">
          {form.tool} isn't available now: its connector isn't connected, or the tool is blocked.
        </p>
      )}
      {tool && !tool.read_only && <UnmarkedNotice form={form} onChange={onChange} />}
      {tool && <ToolArgs tool={tool} form={form} onChange={onChange} />}
      {tool && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <button
            type="button"
            className="rounded-md border border-[var(--border)] px-3 py-1 hover:bg-[var(--card-bg)] disabled:opacity-50"
            disabled={checking || (!tool.read_only && !form.trustUnmarked)}
            onClick={() => void check()}
          >
            {checking ? "Checking…" : "Check now"}
          </button>
          <span className="text-[var(--muted)]">At most</span>
          <input
            aria-label="Runs an hour at most"
            type="number"
            min={1}
            max={MAX_PER_HOUR}
            className={`${control} w-16`}
            value={form.perHour}
            onChange={(e) =>
              onChange({ ...form, perHour: Math.max(1, Math.min(MAX_PER_HOUR, Number(e.target.value) || 1)) })
            }
          />
          <span className="text-[var(--muted)]">runs an hour</span>
        </div>
      )}
      {result && <CheckResult result={result} />}
      {tool && inputs.length > 0 && <InputsFromItem inputs={inputs} fields={fields} form={form} onChange={onChange} />}
      <p className="text-xs text-[var(--muted)]">
        Each new item starts one run. What's there now is left alone; items that show up while Coscribe is closed run
        after it starts. At most 3 run at once.
      </p>
    </div>
  );
}
