import { describe, expect, it } from "vitest";
import { askedBecauseLabel, askedBecauseText } from "./askedBecause";

describe("askedBecause", () => {
  it("says why a command was asked", () => {
    expect(askedBecauseText("command_online", null)).toContain("network");
  });

  it("leaves the reason to the reviewer's note when there is one", () => {
    expect(askedBecauseText("auto_review_blocked", "Auto mode kept blocking actions")).toBeNull();
  });

  it("shows nothing for a reason it doesn't know or a card from before reasons", () => {
    expect(askedBecauseText("something_new", null)).toBeNull();
    expect(askedBecauseText(undefined, null)).toBeNull();
  });

  it("labels every reason, and an unknown one by its words", () => {
    expect(askedBecauseLabel("workspace_rule")).toBe("Workspace rule");
    expect(askedBecauseLabel("something_new")).toBe("something new");
  });
});
