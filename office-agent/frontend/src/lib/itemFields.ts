import type { WorkflowInput } from "../types/workflow";

function plain(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** The field an input takes when the person didn't pick one, as the backend picks it. */
export function matchingField(input: WorkflowInput, fields: string[]): string {
  const wanted = new Set([plain(input.name), plain(input.label ?? "")].filter(Boolean));
  return fields.find((path) => wanted.has(plain(path)) || wanted.has(plain(path.split(".").pop() ?? ""))) ?? "";
}
