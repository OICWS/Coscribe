import { describe, expect, it } from "vitest";
import type { SummaryParts } from "../../lib/transcriptGrouping";
import { inSentence, pptxOverlayTargetOf, previewPathOf, splitStopped } from "./helpers";

describe("previewPathOf", () => {
  it("returns the preview_path of a tool result that has one", () => {
    expect(previewPathOf({ preview_path: "deck-1.png", ok: true })).toBe("deck-1.png");
  });

  it("returns null for anything else", () => {
    expect(previewPathOf(null)).toBeNull();
    expect(previewPathOf("text")).toBeNull();
    expect(previewPathOf({ ok: true })).toBeNull();
    expect(previewPathOf({ preview_path: 3 })).toBeNull();
  });
});

describe("pptxOverlayTargetOf", () => {
  it("targets the slide a pptx edit names, case-insensitively on the extension", () => {
    expect(pptxOverlayTargetOf({ path: "a/Deck.PPTX", slide: 4 })).toEqual({ path: "a/Deck.PPTX", slide: 4 });
  });

  it("falls back to slide 1 when the call names none, as a bare write_pptx does", () => {
    expect(pptxOverlayTargetOf({ path: "deck.pptx" })).toEqual({ path: "deck.pptx", slide: 1 });
    expect(pptxOverlayTargetOf({ path: "deck.pptx", slide: "2" })).toEqual({ path: "deck.pptx", slide: 1 });
  });

  it("is null for a non-pptx or missing path", () => {
    expect(pptxOverlayTargetOf({ path: "report.docx", slide: 2 })).toBeNull();
    expect(pptxOverlayTargetOf({ slide: 2 })).toBeNull();
    expect(pptxOverlayTargetOf({ path: 5 })).toBeNull();
  });
});

describe("inSentence", () => {
  const parts = (verb: string) => ({ verb }) as SummaryParts;

  it("leaves the first clause alone", () => {
    expect(inSentence(parts("Ran"), 0).verb).toBe("Ran");
  });

  it("lower-cases the verb of later clauses", () => {
    expect(inSentence(parts("Read"), 1).verb).toBe("read");
  });

  it("keeps an acronym-led verb's capitals", () => {
    expect(inSentence(parts("PDF"), 2).verb).toBe("PDF");
    expect(inSentence(parts("PDFs read"), 1).verb).toBe("PDFs read");
  });
});

describe("splitStopped", () => {
  it("takes the stop marker off the end of what the model said", () => {
    expect(splitStopped("Here is part one.\n\n[stopped]")).toEqual({ said: "Here is part one.", stopped: true, running: 0 });
    expect(splitStopped("[stopped]")).toEqual({ said: "", stopped: true, running: 0 });
  });

  it("reads how many background tasks the stop left running", () => {
    const text = "[stopped]\n\n(2 background task(s) still running; stop them in the Background tasks panel.)";
    expect(splitStopped(text)).toEqual({ said: "", stopped: true, running: 2 });
  });

  it("leaves a reply that only mentions the marker alone", () => {
    expect(splitStopped("A [stopped] turn shows a note.")).toEqual({ said: "A [stopped] turn shows a note.", stopped: false, running: 0 });
  });
});
