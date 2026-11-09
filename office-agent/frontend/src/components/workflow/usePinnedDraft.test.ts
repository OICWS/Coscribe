import { describe, expect, it } from "vitest";
import type { WorkflowDraftEntry } from "../../lib/transcriptGrouping";
import { draftToPin } from "./usePinnedDraft";

function draft(draftId: string | null, id = "call-1"): WorkflowDraftEntry {
  return {
    kind: "workflow_draft",
    id,
    name: "Weekly SAP export",
    workflow: { steps: [] } as unknown as WorkflowDraftEntry["workflow"],
    notes: [],
    environment: null,
    triggerId: null,
    changes: [],
    draftId,
  };
}

const scrolledAway = { cardVisible: false, turnInFlight: false, closed: new Set<string>() };

describe("draftToPin", () => {
  it("pins the latest unsaved draft once its card is out of view and the turn has ended", () => {
    expect(draftToPin(draft("d1"), new Map(), scrolledAway)?.draftId).toBe("d1");
  });

  it("waits while the turn that drafts it is still running", () => {
    expect(draftToPin(draft("d1"), new Map(), { ...scrolledAway, turnInFlight: true })).toBeNull();
  });

  it("stays hidden for a draft the person closed, and comes back for the next version", () => {
    const closed = new Set(["d1"]);
    expect(draftToPin(draft("d1"), new Map(), { ...scrolledAway, closed })).toBeNull();
    expect(draftToPin(draft("d2", "call-2"), new Map(), { ...scrolledAway, closed })?.draftId).toBe("d2");
  });

  it("closes an old draft without an id by its card", () => {
    const closed = new Set(["call-1"]);
    expect(draftToPin(draft(null), new Map(), { ...scrolledAway, closed })).toBeNull();
  });

  it("never pins a saved draft or one whose card is on screen", () => {
    expect(draftToPin(draft("d1"), new Map([["d1", {}]]), scrolledAway)).toBeNull();
    expect(draftToPin(draft("d1"), new Map(), { ...scrolledAway, cardVisible: true })).toBeNull();
  });
});
