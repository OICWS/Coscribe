import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SteerView } from "./UserMessageView";
import { SteerActionsContext } from "./contexts";

const note = { kind: "steer", id: "s1", text: "How far along is it?", status: "pending" } as const;

function render(composerHasDraft: boolean) {
  return renderToStaticMarkup(
    <SteerActionsContext.Provider value={{ withdraw: () => {}, sendNow: () => {}, composerHasDraft }}>
      <SteerView item={note} />
    </SteerActionsContext.Provider>,
  );
}

const cancelButton = (html: string) => html.match(/<button[^>]*aria-label="Cancel and edit message"[^>]*>/)?.[0] ?? "";

describe("a note waiting while the reply is worked on", () => {
  it("can be taken back to edit while the message box is empty", () => {
    const html = render(false);
    expect(cancelButton(html)).not.toContain(` disabled=""`);
    expect(html).toContain("Cancel and edit message");
  });

  it("can't be taken back over a draft in the message box, and says why", () => {
    const html = render(true);
    expect(cancelButton(html)).toContain(` disabled=""`);
    expect(html).toContain("Clear the message box first to edit this message");
  });

  it("offers rewind only as a disabled control that says why", () => {
    const html = render(false);
    expect(html).toMatch(/<button[^>]*aria-label="Rewind"[^>]* disabled=""/);
    expect(html).toContain("Rewind is unavailable while working");
  });
});
