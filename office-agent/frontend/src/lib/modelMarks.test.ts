import { describe, expect, it } from "vitest";
import type { ModelRow } from "../types/settings";
import { contextLabel, inputCards, modelFacts, outputCards } from "./modelMarks";

const row = (over: Partial<ModelRow>): ModelRow => ({
  id: "m",
  name: "M",
  inputs: [],
  outputs: [],
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

  it("names native modalities as cards, image input as vision", () => {
    const voice = row({ inputs: ["image", "pdf", "audio", "3d"], outputs: ["audio"] });
    expect(inputCards(voice)).toEqual(["Vision", "PDF", "Audio", "3d"]);
    expect(outputCards(voice)).toEqual(["Audio"]);
  });

  it("lists effort levels, context and missing tool calls as plain lines", () => {
    expect(modelFacts(row({ effort_levels: ["low", "high"], context: 200_000 }))).toEqual(["Effort: low · high", "200K context"]);
    expect(modelFacts(row({ tools: false }))).toEqual(["No tool calls"]);
  });
});
