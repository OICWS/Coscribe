import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InvestigationHandoff } from "./EmptyState";

describe("workflow investigation handoff", () => {
  it("shows a dedicated handoff view rather than the new-chat greeting", () => {
    const html = renderToStaticMarkup(<InvestigationHandoff error={null} />);
    expect(html).toContain("Handing off to AI");
    expect(html).toContain("Preparing to investigate the failed run");
    expect(html).not.toContain("gradient-text");
    expect(html).toContain('role="status"');
  });

  it("replaces the loading indicator with an error when the handoff fails", () => {
    const html = renderToStaticMarkup(<InvestigationHandoff error="Connection failed" />);
    expect(html).toContain("hand off to AI");
    expect(html).toContain("Connection failed");
    expect(html).not.toContain("animate-spin");
  });
});
