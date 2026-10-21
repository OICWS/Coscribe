/** A tool call's arguments and result as plain "name: value" lines, so the
 * transcript never has to show the JSON the wire carries. Pure, so the rules
 * are unit-tested; the component only draws what this returns. */

export interface FieldLine {
  /** `null` for an item of a list, which has no name of its own. */
  name: string | null;
  /** The value, when it is a scalar; `null` for a nested object or list. */
  value: string | null;
  /** The indented lines of a nested object or list. */
  children: FieldLine[];
}

export type ResultView = { kind: "lines"; lines: FieldLine[] } | { kind: "text"; text: string };

const MAX_DEPTH = 6;

function scalar(value: unknown): string | null {
  if (value === null || value === undefined) return "none";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") return String(value);
  return null;
}

function lineOf(name: string | null, value: unknown, depth: number): FieldLine {
  const text = scalar(value);
  if (text !== null) return { name, value: text, children: [] };
  if (depth >= MAX_DEPTH) return { name, value: JSON.stringify(value), children: [] };
  const children = linesOf(value, depth + 1);
  return children.length > 0 ? { name, value: null, children } : { name, value: "none", children: [] };
}

function linesOf(value: unknown, depth: number): FieldLine[] {
  if (Array.isArray(value)) return value.map((item) => lineOf(null, item, depth));
  if (typeof value === "object" && value !== null) {
    return Object.entries(value).map(([key, item]) => lineOf(key, item, depth));
  }
  return [lineOf(null, value, depth)];
}

/** A call's arguments, one line per argument. */
export function describeArgs(args: Record<string, unknown>): FieldLine[] {
  return linesOf(args, 0);
}

/** A tool's result. JSON in a string is read as JSON; anything else, text
 * that is not JSON included, stays the text it is. */
export function describeResult(result: unknown): ResultView {
  let value = result;
  if (typeof result === "string") {
    const trimmed = result.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        value = JSON.parse(trimmed);
      } catch {
        return { kind: "text", text: result };
      }
    } else {
      return { kind: "text", text: result };
    }
  }
  if (typeof value === "object" && value !== null) {
    const lines = linesOf(value, 0);
    return lines.length > 0 ? { kind: "lines", lines } : { kind: "text", text: "(empty)" };
  }
  return { kind: "text", text: scalar(value) ?? "" };
}

/** The original JSON, for whoever wants it. */
export function rawJson(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

/** The tools that run a script or a shell command. Their text is the
 * whole safety review, so they are drawn as a terminal line, not as fields. */
const SHELL_COMMAND_TOOLS = new Set(["run_background_command"]);
const SCRIPT_TOOLS = new Set(["run_python_script", "run_node_script", "run_code_command", "run_background_script"]);

/** What a command-like call runs, or null for any other tool. */
export function commandOf(toolName: string, args: Record<string, unknown>): string | null {
  if (!SHELL_COMMAND_TOOLS.has(toolName) && !SCRIPT_TOOLS.has(toolName)) return null;
  const text = SHELL_COMMAND_TOOLS.has(toolName) ? args.command : args.script;
  return typeof text === "string" ? text : null;
}

function linesAsText(lines: FieldLine[], indent = ""): string {
  return lines
    .map((line) => {
      const head = `${indent}${line.name === null ? "-" : `${line.name}:`}${line.value === null ? "" : ` ${line.value}`}`;
      return line.children.length > 0 ? `${head}\n${linesAsText(line.children, `${indent}  `)}` : head;
    })
    .join("\n");
}

/** What a command printed, and its exit code when the result carries one.
 * The script tools return stdout and stderr, the code module one `output`;
 * any other record (a started background task) is shown as its fields. */
export function commandOutput(result: unknown): { output: string; exitCode: number | null } {
  if (result !== null && typeof result === "object") {
    const record = result as Record<string, unknown>;
    const exitCode = typeof record.exit_code === "number" ? record.exit_code : null;
    if ("output" in record) return { output: String(record.output ?? ""), exitCode };
    if ("stdout" in record || "stderr" in record) {
      const printed = [record.stdout, record.stderr]
        .filter((text): text is string => typeof text === "string")
        .map((text) => text.replace(/\n+$/, ""))
        .filter((text) => text !== "");
      return { output: printed.join("\n"), exitCode };
    }
    return { output: linesAsText(linesOf(result, 0)), exitCode };
  }
  return { output: typeof result === "string" ? result : String(result ?? ""), exitCode: null };
}
