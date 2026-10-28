import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

test("General tab: a change saves itself", async ({ page }) => {
  // Restores whatever level was selected before, so the dev .env isn't
  // left changed across runs.
  await page.goto(freshThreadPath("settings"));
  await waitForConnected(page);
  const configLoaded = page.waitForResponse((r) => r.url().includes("/api/config") && r.status() === 200);
  await page.getByRole("button", { name: "Settings" }).click();
  // Wait for the actual GET /api/config fetch to resolve before typing --
  // SettingsModal populates its fields from that response asynchronously,
  // and typing before it lands gets silently clobbered when it arrives.
  await configLoaded;

  await expect(page.getByRole("button", { name: "Save changes" })).toHaveCount(0);

  const levels = ["Debug", "Info", "Warning", "Error"];
  const pressed = await page.locator("button[aria-pressed=true]").allInnerTexts();
  const original = levels.find((level) => pressed.includes(level)) ?? "Info";
  const target = original === "Debug" ? "Warning" : "Debug";

  await page.getByRole("button", { name: target, exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(/^Saved/);
  const config = await page.evaluate(() => fetch("/api/config").then((r) => r.json()));
  expect(JSON.stringify(config)).toContain(target.toUpperCase());

  await page.getByRole("button", { name: original, exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(/^Saved/);
});

test("General tab: Default Mode saves", async ({ page }) => {
  await page.goto(freshThreadPath("settings-mode"));
  await waitForConnected(page);
  const configLoaded = page.waitForResponse((r) => r.url().includes("/api/config") && r.status() === 200);
  await page.getByRole("button", { name: "Settings" }).click();
  await configLoaded;

  await page.getByRole("button", { name: "Plan", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(/^Saved/);

  const config = await page.evaluate(() => fetch("/api/config").then((r) => r.json()));
  expect(config.COSCRIBE_DEFAULT_PERMISSION_MODE).toBe("plan");

  // Put the original mode back and wait for that save to land: the status
  // line still says "Saved" from the click above, so it proves nothing, and
  // a test that ends first leaves every later run in Plan mode.
  const restored = page.waitForResponse(
    (r) => r.url().includes("/api/config") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Auto", exact: true }).click();
  await restored;
  const after = await page.evaluate(() => fetch("/api/config").then((r) => r.json()));
  expect(after.COSCRIBE_DEFAULT_PERMISSION_MODE).toBe("auto");
});

test("Workspace tab: a folder can be set to read, write and delete", async ({ page }) => {
  await page.goto(freshThreadPath("settings-folders"));
  await waitForConnected(page);
  const configLoaded = page.waitForResponse((r) => r.url().includes("/api/config") && r.status() === 200);
  await page.getByRole("button", { name: "Settings" }).click();
  await configLoaded;
  await page.getByRole("button", { name: "Workspace" }).click();

  const folder = "/tmp/coscribe-e2e-deletable";
  await page.getByLabel("Folder to add").fill(folder);
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.getByRole("button", { name: `Access to ${folder}` }).click();
  await expect(page.getByRole("menuitemradio")).toHaveText(["Read only", "Read and write", "Read, write and delete"]);
  await page.getByRole("menuitemradio", { name: "Read, write and delete" }).click();
  const deletable = () =>
    page.evaluate(() => fetch("/api/config").then((r) => r.json())).then((c) => c.COSCRIBE_EXTRA_DELETABLE_DIRS);
  await expect.poll(deletable).toBe(folder);

  await page.getByRole("button", { name: `Remove ${folder}` }).click();
  await expect.poll(deletable).toBeNull();
});

test("Tools tab: categories start collapsed and open to list their tools", async ({ page }) => {
  await page.goto(freshThreadPath("settings-tools"));
  await waitForConnected(page);
  await page.getByRole("button", { name: "Settings" }).click();
  const toolsLoaded = page.waitForResponse((r) => r.url().includes("/api/tools") && r.status() === 200);
  await page.getByRole("button", { name: "Tools" }).click();
  await toolsLoaded;

  await expect(page.getByText("list_files")).toHaveCount(0);
  const filesystem = page.getByRole("button", { name: /^Filesystem/ });
  await expect(filesystem).toHaveAttribute("aria-expanded", "false");
  await filesystem.click();
  await expect(page.getByText("list_files")).toBeVisible();
  await expect(page.getByText("Needs approval").first()).toBeVisible();
});

test("Skills tab: a skill switched off from its menu shows Off, and back on", async ({ page }) => {
  await page.goto(freshThreadPath("settings-skills"));
  await waitForConnected(page);
  await page.getByRole("button", { name: "Settings" }).click();
  const skillsLoaded = page.waitForResponse((r) => r.url().endsWith("/api/skills") && r.status() === 200);
  await page.getByRole("button", { name: "Skills", exact: true }).click();
  await skillsLoaded;

  const row = page.getByRole("button", { name: "Open Word Documents" });
  const options = page.getByRole("button", { name: "Options for Word Documents", exact: true });
  await options.click();
  await page.getByRole("menuitem", { name: "Turn off" }).click();
  await expect(row.getByText("Off", { exact: true })).toBeVisible();
  // Built-in skills can only be switched off, never removed.
  await options.click();
  await expect(page.getByRole("menuitem", { name: "Remove" })).toHaveCount(0);
  await page.getByRole("menuitem", { name: "Turn on" }).click();
  await expect(row.getByText("Off", { exact: true })).toHaveCount(0);
});

test("General tab: the interface font changes the whole interface, not only the chat", async ({ page }) => {
  await page.goto(freshThreadPath("interface-font"));
  await waitForConnected(page);
  const fontOf = (selector: string) =>
    page.evaluate((s) => getComputedStyle(document.querySelector(s) as Element).fontFamily, selector);
  const original = await page.evaluate(() => document.documentElement.dataset.interfaceFont ?? "default");
  const restore = { default: "Figtree", system: "The system's own font", dyslexic: "OpenDyslexic" }[original] ?? "Figtree";

  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Interface font" }).click();
  await page.getByRole("menuitemradio", { name: "OpenDyslexic" }).click();
  await page.getByRole("button", { name: "Close settings" }).click();
  try {
    expect(await fontOf("textarea")).toContain("OpenDyslexic");
    expect(await fontOf("body")).toContain("OpenDyslexic");
  } finally {
    await page.getByRole("button", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Interface font" }).click();
    await page.getByRole("menuitemradio", { name: restore, exact: true }).click();
  }
});

test("General tab: a manual proxy saves without sending its password back, and System restores", async ({ page }) => {
  await page.goto(freshThreadPath("settings-proxy"));
  await waitForConnected(page);
  const proxyLoaded = page.waitForResponse((r) => r.url().includes("/api/settings/proxy") && r.status() === 200);
  await page.getByRole("button", { name: "Settings" }).click();
  await proxyLoaded;

  await page.getByRole("button", { name: "Manual proxy" }).click();
  await page.getByLabel("Proxy address").fill("127.0.0.1:9");
  await page.getByLabel("Do not use the proxy for").fill(".corp.local");
  await page.getByLabel("Proxy user name").fill("alice");
  await page.getByLabel("Proxy password").fill("hunter2");
  // The stub model is on this computer, which never goes through the proxy whatever the list says.
  await page.getByRole("button", { name: "Test connection" }).click();
  await expect(page.getByText("Reached 127.0.0.1 directly.")).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: "Save proxy" }).click();
  await expect(page.getByText("Saved. Restart Coscribe to apply.")).toBeVisible();
  const saved = await page.evaluate(() => fetch("/api/settings/proxy").then((r) => r.text()));
  expect(saved).not.toContain("hunter2");
  expect(JSON.parse(saved)).toMatchObject({ mode: "manual", address: "http://127.0.0.1:9", username: "alice", password_set: true });
  await expect(page.getByLabel("Proxy password")).toHaveAttribute("placeholder", "Saved");
  // The saved password stays with the address it was saved for.
  await page.getByLabel("Proxy address").fill("127.0.0.1:10");
  await expect(page.getByLabel("Proxy password")).toHaveAttribute("placeholder", "Enter it again for this proxy");

  await page.getByRole("button", { name: "System proxy" }).click();
  await page.getByRole("button", { name: "Save proxy" }).click();
  await expect(page.getByText("Saved. Restart Coscribe to apply.")).toBeVisible();
  const restored = await page.evaluate(() => fetch("/api/settings/proxy").then((r) => r.json()));
  expect(restored).toMatchObject({ mode: "system", password_set: false });
});
