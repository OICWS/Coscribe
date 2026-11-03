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
  /** The whole text of an element that holds text alone, as its source has it; null otherwise. */
  content: string | null;
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

/** What the properties panel writes into one element of an artboard's page; an empty value removes
 * that property from the element's own style. */
export interface ElementChange {
  style?: Record<string, string>;
  text?: string;
}

/** Writes the change into the page (`PUT /canvas/element`); rejects with the server's reason, such
 * as a page that changed since the element was picked. */
export async function editBoardElement(threadId: string, page: string, element: InspectedElement, change: ElementChange): Promise<void> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/canvas/element`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page,
      element: element.path,
      tag: element.tag,
      style: change.style ?? {},
      text: change.text,
      text_before: change.text === undefined ? undefined : element.content,
    }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(body?.error ?? `HTTP ${response.status}`);
  }
}

/** Puts the page back as it was before the panel's last edit (`POST /canvas/element/undo`); how many
 * edits are left to undo. Rejects when there is none, or the page was written since. */
export async function undoBoardElement(threadId: string, page: string): Promise<number> {
  const response = await fetch(`/api/threads/${encodeURIComponent(threadId)}/canvas/element/undo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page }),
  });
  const body = (await response.json().catch(() => null)) as { error?: string; left?: number } | null;
  if (!response.ok) throw new Error(body?.error ?? `HTTP ${response.status}`);
  return body?.left ?? 0;
}
