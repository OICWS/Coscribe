import { describe, expect, it } from "vitest";
import type { ModelRow } from "../types/settings";
import { contextLabel, modelMarks, typedModelRow } from "./modelMarks";

const row = (over: Partial<ModelRow>): ModelRow => ({
  id: "m",
  name: "M",
  vision: false,
  effort_levels: [],
  context: null,
  tools: true,
  kind: "chat",
  known: true,
  ...over,
});

describe("modelMarks", () => {
  it("quotes a context window the way vendors do", () => {
    expect(contextLabel(1_048_576)).toBe("1M");
    expect(contextLabel(2_000_000)).toBe("2M");
    expect(contextLabel(128_000)).toBe("128K");
    expect(contextLabel(512)).toBe("512");
  });

  it("lists images, effort levels and context for a known model", () => {
    expect(modelMarks(row({ vision: true, effort_levels: ["low", "high"], context: 200_000 }))).toEqual([
      "Reads images",
      "Effort: low, high",
      "200K context",
    ]);
    expect(modelMarks(row({ tools: false }))).toEqual(["No tool calls"]);
  });

  it("claims nothing about a model the catalog doesn't list", () => {
    expect(modelMarks(typedModelRow("my-tuned"))).toEqual(["Not in the bundled catalog: what it can do is unknown"]);
  });
});
