import { describe, expect, it } from "vitest";
import { GENERAL_FIELDS } from "./fields";
import { findSettings } from "./searchIndex";

// Settings tabs mount only while open, so search lists its rows by hand; this reads every
// SettingRow in the tabs' source and fails on one the list does not find.
const sources = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

// A row shown only in some state (a manual proxy) is found through the row that is always there.
const FOUND_THROUGH: Record<string, string> = {
  Address: "Proxy",
  "Do not use for": "Proxy",
  "User name": "Proxy",
  Password: "Proxy",
};

// Rows whose label is computed, with what each one shows. A new computed label fails the test
// until its labels are listed here and in searchIndex.ts.
const fieldLabel = (fields: { key: string; label: string }[], key: string) => fields.find((f) => f.key === key)!.label;
const COMPUTED: Record<string, string[]> = {
  "GeneralTab.tsx field(DEFAULT_MODEL_KEY).label": [fieldLabel(GENERAL_FIELDS, "COSCRIBE_DEFAULT_MODEL")],
};

function rowLabels() {
  const literal: string[] = [];
  const computed: string[] = [];
  const unread: string[] = [];
  for (const [path, source] of Object.entries(sources)) {
    for (const match of source.matchAll(/<SettingRow\b([\s\S]*?)\/?>/g)) {
      const props = match[1];
      const text = props.match(/\blabel="([^"]+)"/);
      const expression = props.match(/\blabel=\{([^}]+)\}/);
      if (text) literal.push(text[1]);
      else if (expression) computed.push(`${path.replace("./", "")} ${expression[1].trim()}`);
      else unread.push(path);
    }
  }
  return { literal, computed, unread };
}

const finds = (query: string, label: string) => findSettings(query, 1000).some((entry) => entry.label === label);

describe("settings search index", () => {
  const { literal, computed, unread } = rowLabels();

  it("reads the label of every row of the settings tabs", () => {
    expect(literal.length).toBeGreaterThan(20);
    expect(unread, "a SettingRow whose label this test can't read: put label first").toEqual([]);
  });

  it("finds every row by its label", () => {
    const missing = literal.filter((label) => !finds(label, FOUND_THROUGH[label] ?? label));
    expect(missing, "add these rows to searchIndex.ts").toEqual([]);
  });

  it("knows every computed label, and finds what each one shows", () => {
    expect([...new Set(computed)].sort()).toEqual(Object.keys(COMPUTED).sort());
    const missing = Object.values(COMPUTED)
      .flat()
      .filter((label) => !finds(label, label));
    expect(missing, "add these rows to searchIndex.ts").toEqual([]);
  });
});
