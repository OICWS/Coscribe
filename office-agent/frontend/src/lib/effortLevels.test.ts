import { describe, expect, it } from "vitest";
import { EFFORT_SCALE, effortStops, levelFor, stopIndex } from "./effortLevels";

describe("effort levels", () => {
  it("offers a model its own levels, xhigh as Extra high", () => {
    expect(effortStops(["low", "medium", "high", "xhigh", "max"]).map((s) => s.label)).toEqual(["Low", "Medium", "High", "Extra high", "Max"]);
    expect(effortStops(["low", "high", "max"]).map((s) => s.value)).toEqual(["low", "high", "max"]);
    expect(effortStops(["xhigh"])[0].value).toBe("extra");
  });

  it("falls back to the whole scale when the model's levels are not known", () => {
    expect(effortStops(null).map((s) => s.value)).toEqual([...EFFORT_SCALE]);
    expect(stopIndex("ultra", null)).toBe(5);
  });

  it("shows a choice at the level it runs as, like the server", () => {
    const deepseek = ["low", "high", "max"];
    expect(levelFor("medium", deepseek)).toBe("low");
    expect(levelFor("ultra", deepseek)).toBe("max");
    expect(levelFor("low", ["high", "max"])).toBe("high");
    expect(stopIndex("extra", deepseek)).toBe(1);
  });
});
