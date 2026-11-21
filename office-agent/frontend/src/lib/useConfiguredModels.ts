import { useEffect, useState } from "react";
import { getProviders, providerModelIds } from "./rest";

/** "provider:model" for every model a provider has turned on. */
export function useConfiguredModels(): string[] {
  const [models, setModels] = useState<string[]>([]);
  useEffect(() => {
    getProviders()
      .then((providers) => setModels(providerModelIds(providers)))
      .catch(() => {});
  }, []);
  return models;
}
