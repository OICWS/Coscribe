import { describe, expect, it } from "vitest";
import { fileCards } from "./attachments";

describe("fileCards", () => {
  const files = ["report.pdf", ".coscribe/uploads/screenshots/screenshot-2026-11-18-142530.png", ".coscribe/uploads/images/photo.jpg", ".coscribe/uploads/documents/notes.txt"];

  it("leaves out the saved pictures of a message that shows its pictures", () => {
    expect(fileCards(files, ["data:image/png;base64,AA"])).toEqual(["report.pdf", ".coscribe/uploads/documents/notes.txt"]);
  });

  it("keeps every file of a message with no pictures", () => {
    expect(fileCards(files, [])).toEqual(files);
  });
});
