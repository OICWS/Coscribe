import { describe, expect, it } from "vitest";
import { artifactId, countsByKind, dayGroups, editedLabel, visibleArtifacts, type ArtifactSummary } from "./artifacts";

const NOW = new Date("2026-10-21T15:00:00");
const ago = (hours: number) => new Date(NOW.getTime() - hours * 3600e3).toISOString();
const make = (name: string, kind: ArtifactSummary["kind"], hours: number): ArtifactSummary => ({
  id: `id-${name}`,
  path: `${name}.x`,
  location: `/w/${name}.x`,
  name,
  kind,
  modified_at: ago(hours),
  excerpt: null,
});

const DECK = make("Deck", "slides", 17);
const REPORT = make("Report", "docs", 0.1);
const SHEET = make("Figures", "sheets", 80);
const OLD = make("Rag notes", "docs", 24 * 400);
const ALL = [DECK, SHEET, REPORT, OLD];
const ALL_TYPES = { tab: "all", kind: null, query: "" } as const;

describe("visibleArtifacts", () => {
  it("lists the newest first, and the pinned ones before them", () => {
    expect(visibleArtifacts(ALL, new Set(), ALL_TYPES).map((a) => a.name)).toEqual(["Report", "Deck", "Figures", "Rag notes"]);
    const pins = new Set([artifactId(SHEET)]);
    expect(visibleArtifacts(ALL, pins, ALL_TYPES).map((a) => a.name)).toEqual(["Figures", "Report", "Deck", "Rag notes"]);
  });

  it("keeps the pinned tab, a kind and a search apart or together", () => {
    const pins = new Set([artifactId(SHEET), artifactId(REPORT)]);
    expect(visibleArtifacts(ALL, pins, { tab: "pinned", kind: null, query: "" }).map((a) => a.name)).toEqual(["Report", "Figures"]);
    expect(visibleArtifacts(ALL, pins, { tab: "all", kind: "docs", query: "" }).map((a) => a.name)).toEqual(["Report", "Rag notes"]);
    expect(visibleArtifacts(ALL, pins, { tab: "all", kind: null, query: " RAG " }).map((a) => a.name)).toEqual(["Rag notes"]);
    expect(visibleArtifacts(ALL, pins, { tab: "pinned", kind: "slides", query: "" })).toEqual([]);
  });

  it("counts the kinds over everything, whatever is shown", () => {
    expect(countsByKind(ALL)).toEqual({ docs: 2, slides: 1, sheets: 1, dashboard: 0 });
  });
});

describe("dayGroups", () => {
  it("makes a section for the pinned ones, then one per day", () => {
    const pins = new Set([artifactId(SHEET)]);
    const groups = dayGroups(visibleArtifacts(ALL, pins, ALL_TYPES), pins, NOW);
    expect(groups.map((g) => [g.title, g.items.map((a) => a.name)])).toEqual([
      ["Pinned", ["Figures"]],
      ["Today", ["Report"]],
      ["Yesterday", ["Deck"]],
      [expect.stringMatching(/2025/), ["Rag notes"]],
    ]);
  });

  it("calls the day before Yesterday", () => {
    const yesterday = make("Late", "docs", 30);
    expect(dayGroups([yesterday], new Set(), NOW)[0].title).toBe("Yesterday");
  });
});

describe("editedLabel", () => {
  it("counts minutes, then hours, then names the day", () => {
    expect(editedLabel(ago(0.005), NOW)).toBe("Edited just now");
    expect(editedLabel(ago(0.15), NOW)).toBe("Edited 9m ago");
    expect(editedLabel(ago(17), NOW)).toBe("Edited 17h ago");
    expect(editedLabel(ago(30), NOW)).toBe("Edited yesterday");
    expect(editedLabel(ago(24 * 400), NOW)).toMatch(/^Edited .*2025/);
  });
});
