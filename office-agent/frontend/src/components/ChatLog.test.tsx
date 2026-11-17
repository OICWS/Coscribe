import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChatLog } from "./ChatLog";

function emptyChat(suppressEmptyState: boolean) {
  return renderToStaticMarkup(
    <ChatLog
      items={[]}
      suppressEmptyState={suppressEmptyState}
      loading={false}
      olderItems={[]}
      olderStatus="none"
      onLoadOlder={() => {}}
      onApprove={() => {}}
      onReviewTaskDraft={() => {}}
      onDismissTaskDraft={() => {}}
      onPptxShapePicked={() => {}}
    />,
  );
}

describe("empty chat while creating a scheduled task", () => {
  it("leaves the chat area blank when the composer already has a seeded task request", () => {
    const html = emptyChat(true);
    expect(html).toContain('data-testid="chat-log"');
    expect(html).not.toContain("gradient-text");
  });

  it("keeps the existing greeting for an ordinary empty chat", () => {
    expect(emptyChat(false)).toContain("gradient-text");
  });
});
