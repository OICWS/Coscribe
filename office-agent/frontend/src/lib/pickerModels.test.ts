import { describe, expect, it } from "vitest";
import { typedModelRow } from "./modelMarks";
import { rememberModel, splitChoices, type ModelChoice } from "./pickerModels";

const choice = (value: string): ModelChoice => ({ provider: value.split(":")[0], title: value.split(":")[0], value, row: typedModelRow(value.split(":")[1]) });
const all = ["a:1", "a:2", "a:3", "b:1", "b:2", "b:3"].map(choice);
const values = (list: ModelChoice[]) => list.map((c) => c.value);

describe("splitChoices", () => {
  it("shows the first four in order when nothing was picked yet", () => {
    const { top, more } = splitChoices(all, "", []);
    expect(values(top)).toEqual(["a:1", "a:2", "a:3", "b:1"]);
    expect(values(more)).toEqual(["b:2", "b:3"]);
  });

  it("brings the current and the recently picked models into the four, keeping their order", () => {
    const { top, more } = splitChoices(all, "b:3", ["b:2", "gone:x", "a:1"]);
    expect(values(top)).toEqual(["a:1", "a:2", "b:2", "b:3"]);
    expect(values(more)).toEqual(["a:3", "b:1"]);
  });
});

describe("rememberModel", () => {
  it("puts the pick first once and keeps a bounded list", () => {
    expect(rememberModel(["x", "y", "z"], "y", 2)).toEqual(["y", "x"]);
  });
});
