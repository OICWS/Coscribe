import { expect, type Page } from "@playwright/test";

/** A fresh, random thread id per test -- avoids collisions between test
 * runs and with any real conversation history sitting in the dev
 * backend's state dir. */
export function freshThreadPath(prefix: string): string {
  const id = `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
  return `/?thread=${id}`;
}

/** React 18 StrictMode double-invokes effects in dev (see frontend
 * README's "known dev-mode-only artifact" note): the first WebSocket
 * connect() call opens, then is immediately torn down by the first
 * effect cleanup, and a second call opens the socket that actually
 * stays alive. Interacting before that second socket's "state" event
 * lands risks racing the teardown of the first one -- wait for the
 * model pill to show a real model (not the "Select model" placeholder)
 * as a reliable signal the surviving connection is up.
 *
 * The initial render gate used to be a "Sessions" button, then a
 * "Toggle navigation" button -- both removed by later NavRail.tsx
 * changes. It's now a pin/unpin toggle whose accessible name (from its
 * `title` attribute -- see NavRail.tsx) flips between "Pin navigation
 * open" and "Unpin navigation" depending on pinned state, so this
 * matches on the shared "navigation" substring rather than the exact
 * label -- a real, live-caught staleness bug: the exact-label match
 * above silently timed out on every spec in this suite once the label
 * changed, none of them actually exercising anything by that point.
 * Waiting on it instead of jumping straight to the model-pill check
 * keeps the same "app has rendered at all" gate this helper always had. */
export async function waitForConnected(page: Page): Promise<void> {
  await page.getByRole("button", { name: /navigation/i }).waitFor();
  await expect(page.getByTestId("model-pill")).not.toHaveText("Select model", { timeout: 10_000 });
}

/** Makes an environment from the picker below the message box; the conversation then uses it. */
export async function newEnvironment(page: Page, name: string): Promise<void> {
  await page.getByTitle("Choose this conversation's environment").click();
  await page.getByRole("button", { name: "New environment" }).click();
  const dialog = page.getByRole("dialog", { name: "New environment" });
  await dialog.getByLabel("Environment name").fill(name);
  await dialog.getByRole("button", { name: "Create" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByTitle("Choose this conversation's environment")).toHaveText(name);
}

/** Opens an environment's dialog with its gear in the picker. */
export async function editEnvironment(page: Page, name: string): Promise<void> {
  await page.getByTitle("Choose this conversation's environment").click();
  await page.getByRole("button", { name: `Edit ${name}` }).click();
}

export interface EnvironmentRecord {
  id: string;
  name: string;
  network: { mode: string; domains: string[] };
  secrets: string[];
  variables: Record<string, string>;
  used_by: number;
}

export async function environmentNamed(
  request: { get: (url: string) => Promise<{ json: () => Promise<unknown> }> },
  name: string,
): Promise<EnvironmentRecord | undefined> {
  const listed = (await (await request.get("/api/environments")).json()) as { environments: EnvironmentRecord[] };
  return listed.environments.find((e) => e.name === name);
}
