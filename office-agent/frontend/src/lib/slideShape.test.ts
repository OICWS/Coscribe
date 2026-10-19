import { describe, expect, it } from "vitest";
import { borderText, parseBorder } from "./slideShape";

describe("a shape's border", () => {
  it("reads the section language's border and writes it back the same", () => {
    expect(parseBorder("4px solid #aabbcc")).toEqual({ kind: "solid", width: 4, colour: "#AABBCC" });
    expect(parseBorder("1.5px dashed #000000").kind).toBe("dashed");
    expect(borderText(parseBorder("4px solid #AABBCC"))).toBe("4px solid #AABBCC");
  });

  it("takes anything else, or nothing, as no border", () => {
    expect(parseBorder(null).kind).toBe("none");
    expect(parseBorder("none").kind).toBe("none");
    expect(parseBorder("2px dotted #000000").kind).toBe("none");
    expect(borderText(parseBorder("none"))).toBe("none");
  });
});
