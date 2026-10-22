import { beforeEach, describe, expect, it } from "vitest";
import { commentsOf, quoteOf, setPlanComments, withPlanComments } from "./planComments";

const comment = (quote: string, text: string) => ({ id: `${quote}-${text}`, quote, text });

describe("plan comments", () => {
  beforeEach(() => setPlanComments("plan", []));

  it("keeps comments by plan, so another plan has none", () => {
    setPlanComments("plan", [comment("step 1", "too vague")]);
    expect(commentsOf("plan")).toHaveLength(1);
    expect(commentsOf("another plan")).toEqual([]);
    expect(commentsOf(null)).toEqual([]);
  });

  it("puts the typed feedback first and each comment under its passage, then spends them", () => {
    setPlanComments("plan", [comment("Read the notes", "only the .md ones"), comment("Write it", "in Chinese")]);
    expect(withPlanComments("plan", "Shorter please")).toBe(
      "Shorter please\n\nComments on the plan:\n\n> Read the notes\nonly the .md ones\n\n> Write it\nin Chinese",
    );
    expect(commentsOf("plan")).toEqual([]);
  });

  it("sends comments alone when no feedback was typed, and feedback alone when there are none", () => {
    setPlanComments("plan", [comment("a", "b")]);
    expect(withPlanComments("plan", "  ")).toBe("Comments on the plan:\n\n> a\nb");
    expect(withPlanComments("plan", "just this")).toBe("just this");
  });

  it("quotes a selection on one line", () => {
    expect(quoteOf("  Read the\n  notes  ")).toBe("Read the notes");
  });
});
