/** What an artboard's page says about its elements (`conversation/board_inspector.js`): the page
 * answers by message, since its frame is sandboxed apart from the app. */

type ElementKind = "Frame" | "Row" | "Column" | "Grid" | "Text" | "Image";

export interface InspectedNode {
  /** Child indexes from the body, dot-separated; the body is "". */
  path: string;
  tag: string;
  kind: ElementKind;
  text: string;
  children: InspectedNode[];
}

interface InspectedRule {
  selector: string;
  declarations: [string, string][];
}

export interface InspectedElement {
  path: string;
  tag: string;
  label: string;
  kind: ElementKind;
  text: string;
  /** In the page's own pixels, from its top-left corner. */
  box: { x: number; y: number; width: number; height: number };
  computed: Record<string, string>;
  rules: InspectedRule[];
  inherited: { from: string; props: [string, string][] }[];
}

/** The page's answer to one of the panel's questions, or null for any other message. */
export function inspectorAnswer(data: unknown): { tree: InspectedNode } | { element: InspectedElement | null } | null {
  const message = data as { coscribe?: unknown; tree?: InspectedNode; element?: InspectedElement | null } | null;
  if (message?.coscribe === "inspect-tree" && message.tree) return { tree: message.tree };
  if (message?.coscribe === "inspect-element") return { element: message.element ?? null };
  return null;
}

/** The tree as rows to draw, each with its depth. */
export function treeRows(node: InspectedNode, depth = 0): { node: InspectedNode; depth: number }[] {
  return [{ node, depth }, ...node.children.flatMap((child) => treeRows(child, depth + 1))];
}
