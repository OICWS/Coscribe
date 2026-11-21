import { connectorLabel } from "./runLabels";
import { toolLabel } from "./toolLabels";

const RULE = /^([A-Za-z0-9_*-]+)(?:\((.*)\))?$/;

/** A permission rule from a folder's settings.json in words: "write_file(docs/*)" -> "Write file
 * in docs/". Null where it reads no better than as written, so the card shows it as code. */
export function ruleSentence(rule: string): string | null {
  const match = RULE.exec(rule.trim());
  if (!match) return null;
  const [, name, argument] = match;
  if (name.endsWith("*")) {
    if (argument !== undefined) return null;
    const words = name.slice(0, -1).split("_").filter(Boolean);
    if (words.length === 0) return null;
    const [first, ...rest] = words;
    const action = rest.length ? `${connectorLabel(first)} ${toolLabel(rest.join("_")).toLowerCase()}` : first;
    return `Any ${action} action`;
  }
  const label = toolLabel(name);
  if (argument === undefined || argument === "*") return label;
  const open = argument.endsWith("*");
  const text = open ? argument.slice(0, -1).trimEnd() : argument;
  if (!text) return label;
  if (name.includes("command")) return open ? `Run commands starting “${text}”` : `Run “${text}”`;
  if (open && text.endsWith("/")) return `${label} in ${text}`;
  return `${label}: ${argument}`;
}
