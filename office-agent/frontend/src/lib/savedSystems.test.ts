import { describe, expect, it } from "vitest";
import { savedSystems } from "./savedSystems";

const saved = (id: string, name: string) => ({ toolName: "save_design_system", result: JSON.stringify({ id, name, summary: "4 colors" }) });

describe("savedSystems", () => {
  it("lists a saved system once, the later save winning", () => {
    expect(savedSystems([saved("a1", "Acme"), saved("a1", "Acme warm"), saved("b2", "Other")])).toEqual([
      { id: "a1", name: "Acme warm", summary: "4 colors" },
      { id: "b2", name: "Other", summary: "4 colors" },
    ]);
  });

  it("ignores failed, pending and other calls", () => {
    expect(savedSystems([{ ...saved("a1", "Acme"), isError: true }, { toolName: "save_design_system" }, { toolName: "write_file", result: "{}" }, { toolName: "save_design_system", result: "not json" }])).toEqual([]);
  });
});
