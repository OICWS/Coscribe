import { describe, expect, it } from "vitest";
import type { WorkflowInput, WorkflowStep } from "../types/workflow";
import { plainDetail, plainKind, plainReference } from "./plainSteps";

const inputs: WorkflowInput[] = [{ name: "sheet", label: "Claims CSV", type: "file", default: null }];
const tool = (name: string, args: Record<string, unknown>): WorkflowStep => ({
  id: name,
  kind: "tool",
  title: name,
  tool: name,
  args,
  save_as: null,
  irreversible: false,
});

describe("plain words for a step", () => {
  it("names a value by where it comes from, never by its variable", () => {
    expect(plainReference("claim.employee_id", inputs)).toBe("the claim’s employee id");
    expect(plainReference("sheet", inputs)).toBe("“Claims CSV”");
  });

  it("says what a browser step does on the page", () => {
    expect(plainDetail(tool("browser_type", { ref: 'textbox "Full name"', text: "{{claim.name}}" }), inputs)).toBe(
      "Types the claim’s name into “Full name”",
    );
    expect(plainDetail(tool("browser_navigate", { url: "https://example.com/claims/new" }), inputs)).toBe(
      "Opens example.com/…/new",
    );
    expect(plainDetail(tool("browser_navigate", { url: "{{link}}" }), inputs)).toBe("Opens a web page");
    // A dropdown's accessible name runs into its options.
    const select = tool("browser_select_option", {
      ref: 'combobox "Department Choose…FinanceSales"',
      values: ["{{claim.department}}"],
    });
    expect(plainDetail(select, inputs)).toBe("Picks the claim’s department in “Department”");
  });

  it("says which pages a browser step opens, reads or closes", () => {
    expect(plainDetail(tool("browser_tabs", { action: "close", tab_ids: ["a", "b"] }), inputs)).toBe("Closes 2 pages");
    expect(plainDetail(tool("browser_tabs", { action: "close_all" }), inputs)).toBe("Closes its browser pages");
    expect(plainDetail(tool("browser_tabs", { action: "close_all", keep: ["current"] }), inputs)).toBe(
      "Closes its browser pages except the current one",
    );
    expect(plainDetail(tool("browser_tabs", { action: "new", url: "https://example.com/" }), inputs)).toBe(
      "Opens example.com in a new tab",
    );
    expect(plainDetail(tool("browser_snapshot", { tab_ids: [1, 2, 3] }), inputs)).toBe("Reads 3 pages at once");
    expect(plainDetail(tool("browser_fill_form", { fields: [{}, {}] }), inputs)).toBe("Fills in 2 fields");
    expect(plainDetail(tool("browser_steps", { steps: [{}] }), inputs)).toBe("Does 1 thing on the page");
    expect(plainDetail(tool("browser_wait_for", { any_of: ["Saved", "Error"] }), inputs)).toBe(
      "Waits for the page to show “Saved” or “Error”",
    );
  });

  it("says what a file step touches, and falls back to the tool's label", () => {
    expect(plainDetail(tool("read_file", { path: "{{sheet}}" }), inputs)).toBe("Reads “Claims CSV”");
    expect(plainDetail(tool("write_file", { path: "reports/a.txt" }), inputs)).toBe("Saves “reports/a.txt”");
    expect(plainDetail(tool("edit_xlsx_cells", {}), inputs)).toBe("Edit Excel cells");
  });

  it("puts each step in a category a person knows", () => {
    expect(plainKind(tool("browser_click", {}))).toBe("Website");
    expect(plainKind(tool("read_file", {}))).toBe("File");
    expect(plainKind(tool("send_email", {}))).toBe("Action");
  });
});
