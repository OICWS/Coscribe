import { describe, expect, it } from "vitest";
import { commentMessage, elementAt, type SlideElement } from "./slideComments";

const card: SlideElement = { id: "1", label: "Shape", box: [0.1, 0.1, 0.4, 0.4] };
const words: SlideElement = { id: "2", label: 'Text "896k"', box: [0.15, 0.2, 0.1, 0.05] };
const rule: SlideElement = { id: "3", label: "Shape", box: [0.05, 0.6, 0.9, 0.001] };

describe("slide comments", () => {
  it("picks the smallest element under the point", () => {
    expect(elementAt([card, words], 0.2, 0.22)?.id).toBe("2");
    expect(elementAt([card, words], 0.4, 0.4)?.id).toBe("1");
    expect(elementAt([card, words], 0.9, 0.9)).toBeNull();
  });

  it("lets a hairline be hit", () => {
    expect(elementAt([rule], 0.5, 0.603)?.id).toBe("3");
  });

  it("tells coscribe where the comment is and quotes it", () => {
    expect(commentMessage("q3.pptx", 2, "02-glance.svg", 'Title "Q3"', "Shorter\nplease")).toBe(
      'Comment on q3.pptx, Slide 2 › Title "Q3" (page 02-glance.svg):\n> Shorter\n> please',
    );
  });
});
