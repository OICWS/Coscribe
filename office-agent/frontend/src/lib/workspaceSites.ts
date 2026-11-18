/** Sites as a workspace lists them, matched the way the server matches them
 * (`runtime/network_access.py` for sites, `runtime/secret_store.py` for a secret's hosts). */

/** "https://www.Example.com/a" or "*.example.com" -> "example.com", as the server keeps a domain. */
export function normalizeSite(text: string): string | null {
  let site = text.trim().toLowerCase();
  if (site.startsWith("*.")) site = site.slice(2);
  try {
    site = new URL(site.includes("://") ? site : `https://${site}`).hostname;
  } catch {
    return null;
  }
  site = site.replace(/^www\./, "").replace(/\.$/, "");
  return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(site) ? site : null;
}

/** The host a secret's pattern names: "*.example.com" is sent to example.com's subdomains. */
export function patternBase(pattern: string): string {
  return pattern.startsWith("*.") ? pattern.slice(2) : pattern;
}

function covers(sites: string[], host: string): boolean {
  return sites.some((site) => site === "*" || host === site || host.endsWith(`.${site}`));
}

/** Whether a secret with this host pattern can reach any listed site: a site covers itself and
 * its subdomains, "*.example.com" every subdomain of example.com. */
export function reachesPattern(sites: string[], pattern: string): boolean {
  const base = patternBase(pattern);
  return covers(sites, base) || (pattern.startsWith("*.") && sites.some((site) => site.endsWith(`.${base}`)));
}
