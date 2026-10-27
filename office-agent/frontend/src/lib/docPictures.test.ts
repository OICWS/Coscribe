// @vitest-environment jsdom
import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { describe, expect, it } from "vitest";
import { docContent, docExtensions, nodeMarkdown } from "./docModel";
import { pictureProblem, pictureUrl } from "./docPictures";

const file = (type: string, size = 10) => ({ type, size }) as File;

describe("pictureUrl", () => {
  it("shows a picture the Doc keeps from the server, and others from where they are", () => {
    expect(pictureUrl("t 1", "a b.md", "a b.doc/assets/x.png")).toBe("/api/threads/t%201/doc/asset?path=a%20b.md&src=a%20b.doc%2Fassets%2Fx.png");
    expect(pictureUrl("t", "a.md", "https://x.y/z.png")).toBe("https://x.y/z.png");
    expect(pictureUrl("t", "a.md", "data:image/png;base64,AAAA")).toBe("data:image/png;base64,AAAA");
  });
});

describe("pictureProblem", () => {
  it("refuses what the server would", () => {
    expect(pictureProblem(file("image/png"))).toBeNull();
    expect(pictureProblem(file("image/svg+xml"))).toMatch(/PNG, JPEG, GIF and WebP/);
    expect(pictureProblem(file("image/png", 9 * 1024 * 1024))).toMatch(/8 MB/);
  });
});

describe("a picture in a paragraph", () => {
  it("is written as markdown with the short path, alt text and all", () => {
    const schema = getSchema(docExtensions);
    const doc = PMNode.fromJSON(schema, docContent([{ index: 0, kind: "paragraph", text: "![the chart](plan.doc/assets/chart.png)" }]));
    expect(doc.child(0).firstChild?.type.name).toBe("image");
    expect(nodeMarkdown(doc.child(0))).toBe("![the chart](plan.doc/assets/chart.png)");
  });
});
