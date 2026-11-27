import type { ProviderCatalogEntry } from "../../../types/settings";
import type { ProviderForm } from "./ProviderPage";

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
  if (form.apiFormat === "azure" && !form.apiVersion?.trim()) return "Enter the Azure API version.";
  // The model picker offers only the models turned on.
  if (form.models.length === 0) return "Turn on at least one model.";
  return null;
}

export function providerConnection(form: ProviderForm) {
  return {
    name: form.name.trim(),
    base_url: form.baseUrl.trim(),
    api_key: form.apiKey.trim(),
    api_format: form.apiFormat,
    api_version: form.apiVersion?.trim(),
  };
}
