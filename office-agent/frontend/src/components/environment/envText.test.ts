import { describe, expect, it } from "vitest";
import { formatEnvText, parseEnvText } from "./envText";

describe("parseEnvText", () => {
  it("reads lines, comments, export and inline comments", () => {
    expect(parseEnvText("# note\nA=1\n\nexport B = two words # c\nC=\n")).toEqual({
      variables: { A: "1", B: "two words", C: "" },
    });
  });

  it("reads quoted values over several lines", () => {
    expect(parseEnvText('CONFIG="key1=val1\nkey2=val2" # x\nNEXT=\'a # b\'\nZ=1')).toEqual({
      variables: { CONFIG: "key1=val1\nkey2=val2", NEXT: "a # b", Z: "1" },
    });
  });

  it("names the line of a mistake", () => {
    expect(parseEnvText("A=1\nnonsense")).toEqual({ error: "Line 2: expected KEY=value." });
    expect(parseEnvText("A=1\nA=2")).toEqual({ error: "Line 2: A appears twice." });
    expect(parseEnvText("1X=a")).toMatchObject({ error: expect.stringContaining("isn't a variable name") });
    expect(parseEnvText('A="open')).toEqual({ error: "Line 1: the quote is never closed." });
  });

  it("round-trips what it formats", () => {
    const variables = {
      PLAIN: "x",
      EMPTY: "",
      SPACED: " a b ",
      MULTI: "l1\nl2",
      APOS: "it's \"q\" \\ # h",
      BACK: "C:\\dir\\n",
    };
    expect(parseEnvText(formatEnvText(variables))).toEqual({ variables });
  });
});
