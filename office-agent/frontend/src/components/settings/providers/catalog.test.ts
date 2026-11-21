import { describe, expect, it } from "vitest";
import type { ProviderCatalogEntry } from "../../../types/settings";
import { formProblem } from "./catalog";
import type { ProviderForm } from "./ProviderPage";

const catalog = [{ name: "gemini", builtin: true }] as ProviderCatalogEntry[];
const form = (over: Partial<ProviderForm>): ProviderForm => ({
  name: "deepseek",
  baseUrl: "https://api.deepseek.com/v1",
  apiKey: "",
  defaultModel: "deepseek-chat",
  ...over,
});

describe("formProblem", () => {
  it("asks for a key only when no key is saved", () => {
    expect(formProblem(form({}), catalog, false)).toBe("API key cannot be blank.");
    expect(formProblem(form({}), catalog, true)).toBeNull();
    expect(formProblem(form({ name: "gemini", baseUrl: "" }), catalog, true)).toBeNull();
  });

  it("needs a default model, or the model picker has nothing to offer", () => {
    expect(formProblem(form({ defaultModel: " " }), catalog, true)).toBe("Choose a default model.");
  });

  it("still needs a base URL for a custom provider with a saved key", () => {
    expect(formProblem(form({ baseUrl: " " }), catalog, true)).toBe("Base URL cannot be blank.");
  });
});
