#!/usr/bin/env node
// Time from launching the Electron shell to a usable window (#478 part 2).
//
//   node scripts/measure-startup.mjs --server <coscribe-server exe> [--runs 5] [--xvfb]
//
// Reads the window's own URL through Chromium's remote-debugging endpoint, so the shell needs
// no instrumentation: "splash" is the first page the window shows (file://), "app" is the first
// time the window is on the server's page (http://127.0.0.1:<port>/). Build first (`npm run
// build`); a stub or real sidecar is named with --server (COSCRIBE_SERVER_BIN).

import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const electron = createRequire(import.meta.url)("electron");

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const i = args.indexOf(name);
  return i < 0 ? fallback : args[i + 1];
};
const server = flag("--server");
const runs = Number(flag("--runs", "5"));
const noSandbox = args.includes("--no-sandbox");
if (!server) {
  console.error("usage: measure-startup.mjs --server <coscribe-server exe> [--runs N] [--no-sandbox]");
  process.exit(2);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () =>
  new Promise((resolve) => {
    const s = createServer();
    s.listen(0, "127.0.0.1", () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
  });

async function pages(debugPort) {
  try {
    const res = await fetch(`http://127.0.0.1:${debugPort}/json/list`);
    return (await res.json()).filter((t) => t.type === "page");
  } catch {
    return [];
  }
}

async function once() {
  const data = mkdtempSync(join(tmpdir(), "coscribe-startup-"));
  const debugPort = await freePort();
  const env = Object.fromEntries(
    Object.entries(process.env).filter(([k]) => !k.toLowerCase().includes("proxy")),
  );
  Object.assign(env, {
    COSCRIBE_SERVER_BIN: server,
    COSCRIBE_APP_DATA_DIR: data,
    COSCRIBE_DEFAULT_MODEL: "claude-sonnet-5-5",
    ANTHROPIC_API_KEY: "sk-ant-measure-startup",
  });
  const t0 = performance.now();
  const child = spawn(
    electron,
    [root, `--remote-debugging-port=${debugPort}`, `--user-data-dir=${join(data, "electron")}`, ...(noSandbox ? ["--no-sandbox"] : [])],
    { env, stdio: "ignore" },
  );
  let splash;
  let app;
  try {
    while (app === undefined) {
      if (performance.now() - t0 > 120_000) throw new Error("no app page after 120 s");
      for (const page of await pages(debugPort)) {
        if (splash === undefined && page.url.startsWith("file:")) splash = performance.now() - t0;
        if (page.url.startsWith("http://127.0.0.1:") && !page.url.includes(`:${debugPort}`)) {
          app = performance.now() - t0;
        }
      }
      await sleep(10);
    }
  } finally {
    child.kill();
    await sleep(500);
    rmSync(data, { recursive: true, force: true });
  }
  return { splash: splash ?? app, app };
}

const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const results = [];
for (let i = 0; i < runs; i++) {
  const r = await once();
  results.push(r);
  console.log(`run ${i + 1}: splash ${(r.splash / 1000).toFixed(2)} s, app ${(r.app / 1000).toFixed(2)} s`);
}
const fmt = (key) => {
  const xs = results.map((r) => r[key]);
  return `median ${(median(xs) / 1000).toFixed(2)} s (range ${(Math.min(...xs) / 1000).toFixed(2)}-${(Math.max(...xs) / 1000).toFixed(2)})`;
};
console.log(`splash ${fmt("splash")}; app ${fmt("app")}`);
