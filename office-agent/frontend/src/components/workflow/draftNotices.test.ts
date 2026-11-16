import { describe, expect, it } from "vitest";
import type { LogItem } from "../../state/reducer";
import { draftsToOffer } from "./draftNotices";

let seq = 0;
function drafted(name: string, draftId: string, extra: Record<string, unknown> = {}, args = {}): LogItem {
  return {
    id: `call-${++seq}`,
    kind: "tool",
    toolName: "draft_workflow",
    arguments: args,
    result: { status: "drafted", name, draft_id: draftId, workflow: { steps: [] }, ...extra },
  };
}

describe("draftsToOffer", () => {
  it("offers each workflow's newest unsaved draft", () => {
    const items = [
      drafted("Invoices", "d1", { trigger_id: "t1" }),
      drafted("Open items", "d2", { trigger_id: "t2" }),
      drafted("Invoices", "d3", { trigger_id: "t1" }),
    ];
    expect(draftsToOffer(items, new Map(), new Set()).map((d) => d.draftId)).toEqual(["d2", "d3"]);
  });

  it("leaves out a saved draft and one whose notice was closed", () => {
    const items = [drafted("A", "d1"), drafted("B", "d2"), drafted("C", "d3")];
    const offered = draftsToOffer(items, new Map([["d1", {}]]), new Set(["d2"]));
    expect(offered.map((d) => d.draftId)).toEqual(["d3"]);
  });
});
