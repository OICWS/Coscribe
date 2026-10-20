// Smoke test of the built desktop shell: the sidecar server comes up, the window loads the UI and
// draws the page's title bar, and closing the window quits the app and takes the sidecar with it.
// No model and no sign-in. Run after `npm run build`, with a coscribe-web to use as the sidecar:
//
//   COSCRIBE_SERVER_BIN=<path to coscribe-web> node scripts/smoke.mjs
//
// It drives the app through Playwright's Electron support, which the frontend's e2e specs already
// install; it is resolved from there so this package needs no dependency of its own. Without a
// display (Linux) run it under xvfb-run.

import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const frontend = resolve(root, "..", "office-agent", "frontend");
const { _electron: electron } = createRequire(join(frontend, "package.json"))("@playwright/test");

if (!process.env.COSCRIBE_SERVER_BIN) {
  console.error("COSCRIBE_SERVER_BIN must name a coscribe-web to run as the sidecar");
  process.exit(2);
}

const STARTUP_MS = 120_000;
const QUIT_MS = 30_000;

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

async function until(what, ms, read) {
  const deadline = Date.now() + ms;
  for (;;) {
    const value = await read();
    if (value) return value;
    if (Date.now() > deadline) throw new Error(`timed out waiting for ${what}`);
    await sleep(250);
  }
}

const reachable = (url) =>
  fetch(url, { signal: AbortSignal.timeout(2000) }).then(
    (response) => response.ok,
    () => false,
  );

const dataDir = mkdtempSync(join(tmpdir(), "coscribe-smoke-"));
// A provider is configured (nothing listens at its address, no model is called): without one the
// page shows its welcome screen, which has no title bar. Closing the window hides it by default
// (the sidecar keeps scheduled tasks running); the last setting, read at every close, makes the
// close a real quit.
const forward = (path) => path.replaceAll("\\", "/");
writeFileSync(
  join(dataDir, "providers.json"),
  JSON.stringify({ providers: { stub: { base_url: "http://127.0.0.1:9/v1", api_key: "x" } } }),
);
writeFileSync(
  join(dataDir, ".env"),
  [
    `COSCRIBE_PROVIDERS_CONFIG_PATH=${forward(join(dataDir, "providers.json"))}`,
    "COSCRIBE_DEFAULT_MODEL=stub:fake",
    "COSCRIBE_BACKGROUND_ON_CLOSE=false",
    "",
  ].join("\n"),
);

const steps = [];
const step = async (name, run) => {
  try {
    await run();
    steps.push([name, null]);
    console.log(`ok    ${name}`);
  } catch (error) {
    steps.push([name, error]);
    console.log(`FAIL  ${name}  (${error.message})`);
    throw error;
  }
};

let app;
try {
  app = await electron.launch({
    executablePath: createRequire(join(root, "package.json"))("electron"),
    args: [root, ...(process.platform === "linux" ? ["--no-sandbox"] : [])],
    env: { ...process.env, COSCRIBE_APP_DATA_DIR: dataDir },
    timeout: STARTUP_MS,
  });
  const exited = new Promise((done) => app.process().once("exit", done));
  const window = await app.firstWindow();
  let origin = "";

  await step("the sidecar server comes up", async () => {
    await window.waitForURL(/^http:\/\/127\.0\.0\.1:\d+\//, { timeout: STARTUP_MS });
    origin = new URL(window.url()).origin;
    await until("the server to answer", STARTUP_MS, () => reachable(`${origin}/`));
  });

  await step("the window loads the UI and draws the title bar", async () => {
    // The page draws its own title bar only inside the desktop shell, from the preload's platform.
    await window.getByTitle("Menu", { exact: true }).first().waitFor({ timeout: STARTUP_MS });
    await window.getByTitle("Settings", { exact: true }).first().waitFor({ timeout: 5000 });
    const platform = await window.evaluate(() => window.coscribeDesktop?.platform);
    if (platform !== process.platform) throw new Error(`the preload says ${platform}`);
  });

  await step("closing the window quits the app and the sidecar", async () => {
    await window.close();
    await Promise.race([
      exited,
      sleep(QUIT_MS).then(() => {
        throw new Error(`the app is still running ${QUIT_MS / 1000}s after the window closed`);
      }),
    ]);
    await until("the sidecar to stop", QUIT_MS, async () => !(await reachable(`${origin}/`)));
  });
} catch (error) {
  // A step reports its own failure; anything else (the app did not launch) is reported here.
  if (!steps.some(([, failure]) => failure)) console.log(`FAIL  launching the app  (${error.message})`);
} finally {
  // A run that failed before the quit step leaves the app up: end it, so the job does not hang.
  if (app) await app.close().catch(() => undefined);
  rmSync(dataDir, { recursive: true, force: true });
}

const failed = steps.filter(([, error]) => error).length;
if (steps.length < 3 && !failed) console.log("FAIL  the run ended before every step");
process.exit(failed || steps.length < 3 ? 1 : 0);
