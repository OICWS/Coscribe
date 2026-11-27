import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SteerView, UserMessageView } from "./UserMessageView";
import { MessageActionsContext, SteerActionsContext } from "./contexts";
import type { MessageActions } from "../../lib/messageActions";

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

describe("a delivered note", () => {
  it.each(["2026-11-18T04:33:00Z", undefined])("offers Copy and explains disabled actions with send time %s", (sentAt) => {
    const html = renderToStaticMarkup(<SteerView item={{ ...note, status: "delivered", sentAt }} />);
    expect(html).toMatch(/<button[^>]*aria-label="Rewind to here"[^>]* disabled=""/);
    expect(html).toMatch(/<button[^>]*aria-label="Edit"[^>]* disabled=""/);
    expect(html).toContain("can’t be edited or rewound separately");
    expect(html).toContain("Copy");
    expect(html).not.toContain("Send now");
    expect(html.includes("Nov 18, 2026")).toBe(Boolean(sentAt));
    expect(html.includes("Added while working")).toBe(Boolean(sentAt));
  });
});

const sent = { kind: "user", id: "u1", text: "fix and watch it", turnIndex: 0, sentAt: "2026-11-18T04:33:00Z" } as const;

function renderSent(actions: Partial<MessageActions> | null) {
  const value = actions && { edit: () => {}, rewind: () => {}, blocked: null, leavesChanges: new Set<number>(), ...actions };
  return renderToStaticMarkup(
    <MessageActionsContext.Provider value={value}>
      <UserMessageView item={sent} />
    </MessageActionsContext.Provider>,
  );
}

describe("a sent message", () => {
  it("offers its time, Rewind, Edit and Copy", () => {
    const html = renderSent({});
    expect(html).toContain("Nov 18, 2026");
    expect(html).toContain("Rewind to here");
    expect(html).toMatch(/aria-label="Edit"/);
    expect(html).toContain("Copy");
  });

  it("keeps Rewind and Edit disabled while they can't run, and says why", () => {
    const html = renderSent({ blocked: "Unavailable while working" });
    expect(html).toMatch(/<button[^>]*aria-label="Rewind to here"[^>]* disabled=""/);
    expect(html).toMatch(/<button[^>]*aria-label="Edit"[^>]* disabled=""/);
    expect(html).toContain("Unavailable while working");
  });

  it("before a compaction shows only its time and Copy", () => {
    const html = renderSent(null);
    expect(html).not.toContain("Rewind to here");
    expect(html).toContain("Copy");
  });
});
