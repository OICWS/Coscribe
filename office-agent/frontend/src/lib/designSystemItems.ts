import { createDesignSystem, deleteDesignSystem, getDesignSystem, getDesignSystems, saveDesignSystem } from "./rest";
import type { SystemItem } from "./artifacts";

/** The library as the Artifacts page lists it. */
export async function listSystemItems(): Promise<SystemItem[]> {
  return (await getDesignSystems()).map((s) => ({ id: s.id, name: s.name, kind: "design-system", modified_at: s.updated_at, palette: s.palette }));
}

const failure = (result: { error: string } | object): string | null => ("error" in result ? result.error : null);

export async function renameSystem(id: string, name: string): Promise<void> {
  const system = await getDesignSystem(id);
  const error = failure(await saveDesignSystem({ ...system, name }));
  if (error) throw new Error(error);
}

/** A copy under "<name> copy", with everything the original has. */
export async function duplicateSystem(id: string): Promise<void> {
  const original = await getDesignSystem(id);
  const made = await createDesignSystem(`${original.name} copy`);
  if ("error" in made) throw new Error(made.error);
  const error = failure(await saveDesignSystem({ ...original, id: made.id, name: made.name }));
  if (error) throw new Error(error);
}

export async function removeSystem(id: string): Promise<void> {
  const error = failure(await deleteDesignSystem(id));
  if (error) throw new Error(error);
}
