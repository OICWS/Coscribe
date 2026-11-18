import { getAllowedSites, isElectron, setAllowedSites } from "./electron";
import { importBrowserSites } from "./rest";

/** The desktop app's old list of sites its browser used without asking moves, once, into the
 * workspaces that reach each site (decision 0050). Only the renderer holds the launch token the
 * server asks for, so the move starts here; the list is emptied only once the server kept it. */
export async function moveOldAllowedSites(): Promise<void> {
  if (!isElectron()) return;
  const sites = await getAllowedSites();
  if (sites.length === 0) return;
  const result = await importBrowserSites(sites);
  if (!("error" in result)) await setAllowedSites([]);
}
