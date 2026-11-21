import type { ProviderCatalogEntry } from "../../../types/settings";
import type { ProviderForm } from "./ProviderPage";

/** Whether the provider's models list with no key: a built-in one other than OpenAI lists the
 * bundled catalog's, not the service's own /models. */
export function listsWithoutKey(name: string, builtin: boolean): boolean {
  return builtin && name.toLowerCase() !== "openai";
}

// The server routes a name that matches a built-in provider case-insensitively
// to the built-in branch, so the catalog is matched the same way.
export function findEntry(catalog: ProviderCatalogEntry[], name: string) {
  return catalog.find((e) => e.name.toLowerCase() === name.toLowerCase()) ?? null;
}

/** What is missing from the form before the server is asked, or null. A blank key keeps
 * the saved one, so it is missing only for a provider without one. */
export function formProblem(form: ProviderForm, catalog: ProviderCatalogEntry[], hasSavedKey: boolean): string | null {
  const name = form.name.trim();
  if (!name) return "Name cannot be blank.";
  if (!form.apiKey.trim() && !hasSavedKey) return "API key cannot be blank.";
  if (!findEntry(catalog, name)?.builtin && !form.baseUrl.trim()) return "Base URL cannot be blank.";
  // The model picker offers only the models turned on.
  if (form.models.length === 0) return "Turn on at least one model.";
  return null;
}
