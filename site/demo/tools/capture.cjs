// Renders one exported real conversation in the real Coscribe UI and saves the pieces the
// homepage demo replays. See README.md next to this file for how to run it.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

if (process.argv[2] === "--scrub") {
  // Re-scrubs saved scenes: node capture.cjs --scrub ../scenes/*/scene.json
  for (const file of process.argv.slice(3)) fs.writeFileSync(file, JSON.stringify(scrub(JSON.parse(fs.readFileSync(file, "utf8")))));
  process.exit(0);
}

const [EXP, OUT, REAL, BASE = "http://127.0.0.1:8000"] = process.argv.slice(2);
const events = JSON.parse(fs.readFileSync(path.join(EXP, "socket-events.json"), "utf8"));
const tid = events.thread;

// The app's Markdown reads "$13,375,000 ... $4,798,139" as a formula; the demo shows the money.
const escapeMoney = (text) => text.replace(/(^|[^\\])\$(?=[\d(])/g, "$1\\$");
const history = events.events.find((e) => e.type === "history");
const state = events.events.find((e) => e.type === "state");
const overrides = JSON.parse(fs.readFileSync(path.join(__dirname, "overrides.json"), "utf8"))[path.basename(OUT)] || {};
history.entries.forEach((entry, index) => {
  if (overrides[index] !== undefined) entry.text = overrides[index];
  if (entry.kind === "agent") entry.text = escapeMoney(entry.text);
});

const DESKTOP = `
  window.coscribeDesktop = new Proxy({}, { get(_, key) {
    if (key === "platform") return "win32";
    if (typeof key !== "string" || key === "then") return undefined;
    // Keep each listener, so the capture can play the desktop shell's side of the browser.
    if (key.startsWith("on")) return (cb) => { (window.__demoOn = window.__demoOn || {})[key] = cb; return () => {}; };
    return () => Promise.resolve(null);
  }, has() { return true; } });`;

async function openPage(browser, entries, inFlight) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 861 }, deviceScaleFactor: 1 });
  await ctx.addInitScript(DESKTOP);
  const page = await ctx.newPage();
  await page.routeWebSocket(new RegExp(`/ws/${tid}`), (ws) => {
    ws.send(JSON.stringify({ ...state, turn_in_flight: inFlight }));
    ws.send(JSON.stringify({ ...history, entries }));
    ws.onMessage(() => {});
  });
  await page.route(new RegExp(`/api/threads/${tid}`), (route) => {
    const url = route.request().url();
    if (url.includes("/activity")) return route.fulfill({ json: events.activity });
    if (url.includes("/subagents")) return route.fulfill({ json: events.subagents });
    return route.continue({ url: url.replace(`/api/threads/${tid}`, `/api/threads/${REAL}`) });
  });
  await page.goto(`${BASE}/?thread=${tid}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  return page;
}

// In the page: a copy of the window with the conversation, notices and panels taken out.
const SHELL = (keepPanel) => {
  const root = document.getElementById("root").cloneNode(true);
  const log = root.querySelector('[data-testid="chat-log"] > div');
  if (log) log.innerHTML = "";
  const notices = root.querySelector('[data-testid="notice-stack"]');
  if (notices) notices.innerHTML = "";
  if (!keepPanel) root.querySelectorAll("section[data-panel]").forEach((s) => s.remove());
  return root.outerHTML;
};

// The runs' file paths name the Windows account and the test machine's folders; the demo shows
// a neutral account and a workspace called Demo instead.
function scrub(value) {
  if (typeof value === "string")
    return value
      .replace(/([A-Za-z]:)(\\+|\/)Users\2[^\\/"'\s]+/g, "$1$2Users$2demo")
      .replace(/F:(\\+|\/)Coscribe\1\.cache\1demo\1(?:en|zh)\1workspace/g, "C:$1Demo")
      .replace(/F:(\\+|\/)Coscribe\1Coscribe-Desktop/g, "C:$1Program Files$1Coscribe")
      .replace(/F:(\\+|\/)Coscribe/g, "C:$1Coscribe");
  if (Array.isArray(value)) return value.map(scrub);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, scrub(v)]));
  return value;
}

// Screenshots to compare the demo against, only when DEMO_SHOTS names a folder.
const shot = (page, name) =>
  process.env.DEMO_SHOTS ? page.screenshot({ path: path.join(process.env.DEMO_SHOTS, `${name}.png`) }) : null;

(async () => {
  fs.mkdirSync(path.join(OUT, "media"), { recursive: true });
  const browser = await chromium.launch();
  const out = {
    thread: tid,
    prompt: history.entries[0].text,
    // What came after the prompt, in order: "a" a reply or note, "t" a tool call.
    order: history.entries.slice(1).map((e) => (e.kind === "tool" ? "t" : "a")).join(""),
    tools: [],
    agents: [],
  };

  for (const entry of history.entries) {
    if (entry.kind !== "tool") continue;
    const args = {};
    for (const [k, v] of Object.entries(entry.arguments || {}))
      if (typeof v === "string" ? v.length <= 300 : Array.isArray(v) && JSON.stringify(v).length <= 300) args[k] = v;
    out.tools.push({ toolName: entry.tool_name, arguments: args, isError: !!entry.is_error });
  }

  // The finished conversation.
  let page = await openPage(browser, history.entries, false);
  Object.assign(out, await page.evaluate((shellSrc) => {
    const shell = eval(`(${shellSrc})`)(false);
    const log = document.querySelector('[data-testid="chat-log"] > div');
    const user = log.querySelector(".group\\/msg").outerHTML;
    const agents = [...log.querySelectorAll("div.min-w-0.max-w-\\[92\\%\\]")].map((el) => el.outerHTML);
    const replyActions = log.querySelector(".-mt-2")?.outerHTML ?? "";
    const cards = log.querySelector(".group\\/turn > div.mt-2.flex")?.outerHTML ?? "";
    const notices = document.querySelector('[data-testid="notice-stack"]')?.innerHTML ?? "";
    const chevron = log.querySelector('button[aria-expanded] svg')?.outerHTML ?? "";
    const title = document.querySelector('[data-testid="thread-header"]')?.outerHTML ?? "";
    return { shell, user, agents, replyActions, cards, notices, chevron, title };
  }, SHELL.toString()));
  await shot(page, "end");

  // Each call opened, as the transcript shows it.
  const groups = page.locator('[data-testid="chat-log"] button.inline-flex[aria-expanded="false"]');
  while (await groups.count()) await groups.first().click();
  out.details = await page.evaluate(async () => {
    const tidy = (el) => {
      el.querySelectorAll("details").forEach((d) => d.remove());
      el.querySelectorAll("pre, p").forEach((p) => {
        if (p.textContent.length > 900) p.textContent = p.textContent.slice(0, 900) + "\n…";
      });
      return el.innerHTML;
    };
    const wait = () => new Promise((r) => setTimeout(r, 120));
    const details = [];
    for (const list of document.querySelectorAll('[data-testid="chat-log"] div.mt-2.rounded-xl')) {
      const rows = [...list.children].filter((c) => c.querySelector(":scope > button[aria-expanded]"));
      if (rows.length === 0) { details.push(tidy(list.cloneNode(true))); continue; }
      for (const row of rows) {
        const button = row.querySelector(":scope > button");
        button.click(); await wait();
        const open = row.querySelector(":scope > div.border-t");
        details.push(open ? tidy(open.cloneNode(true)) : "");
        button.click(); await wait();
      }
    }
    return details;
  });
  await shot(page, "steps");

  // The made file opened in its panel.
  const notice = page.locator('[data-testid="notice"] button[title^="Open"]').first();
  if (await notice.count()) {
    await notice.click();
    await page.waitForTimeout(7000);
    const opened = await page.evaluate(async (shellSrc) => {
      const shell = eval(`(${shellSrc})`)(true);
      const panel = document.querySelector("section[data-panel]");
      if (!panel) return null;
      const images = {};
      for (const img of panel.querySelectorAll("img[src^='/api/']")) {
        const src = img.getAttribute("src");
        if (!(src in images)) images[src] = await (await fetch(src)).text();
      }
      const frame = document.getElementById("root").querySelector('[data-testid="chat-log"]').closest(".absolute");
      return { shell, images, chatFrame: frame?.getAttribute("style") ?? "" };
    }, SHELL.toString());
    if (opened) {
      let n = 0;
      const names = {};
      for (const [src, body] of Object.entries(opened.images)) {
        const name = `panel-${n++}.svg`;
        fs.writeFileSync(path.join(OUT, "media", name), body);
        names[src] = name;
      }
      for (const [src, name] of Object.entries(names)) {
        const escaped = src.replace(/&/g, "&amp;");
        opened.shell = opened.shell.split(escaped).join(`scenes/${path.basename(OUT)}/media/${name}`);
      }
      delete opened.images;
      out.open = opened;
    }
    await shot(page, "open");
  }
  // The Browser panel, for a run that used it: asking for the site, then the page in use.
  if (history.entries.some((e) => e.kind === "tool" && e.tool_name.startsWith("browser_"))) {
    const on = (key, payload) => page.evaluate(([k, v]) => window.__demoOn[k] && window.__demoOn[k](v), [key, payload]);
    const tab = (activity) => ({
      tabs: [{ id: 1, title: "Northwind CRM · Accounts", url: "http://127.0.0.1:8765/", favicon: null, loading: false,
        canGoBack: true, canGoForward: false, loadError: null, ...(activity ? { activity } : {}) }],
      activeId: 1,
    });
    const keep = () => page.evaluate((shellSrc) => eval(`(${shellSrc})`)(true), SHELL.toString());
    await on("onBrowserAgent", { open: true, threadId: tid });
    await page.waitForTimeout(300);
    await on("onBrowserPanelTabs", { tabs: [{ ...tab(null).tabs[0], title: "New tab", url: "" }], activeId: 1 });
    await page.waitForTimeout(800);
    await on("onBrowserPermission", { requestId: 1, host: "127.0.0.1", threadId: tid });
    await page.waitForTimeout(800);
    out.browser = { ask: await keep() };
    await shot(page, "browser-ask");
    await page.getByText("Allow for this chat").click().catch(() => {});
    await on("onBrowserPanelTabs", tab("working"));
    await page.waitForTimeout(800);
    out.browser.busy = await keep();
    await shot(page, "browser-busy");
    await on("onBrowserPanelTabs", tab(null));
    await page.waitForTimeout(800);
    out.browser.idle = await keep();
    await shot(page, "browser-idle");
  }
  await page.context().close();

  // A turn still running: the composer and the call in progress.
  const firstTool = history.entries.findIndex((e) => e.kind === "tool");
  const partial = history.entries.slice(0, firstTool + 1).map((e, i, all) =>
    i === all.length - 1 ? { ...e, result: undefined, is_error: undefined } : e);
  page = await openPage(browser, partial, true);
  out.working = await page.evaluate(() => ({
    composer: document.querySelector('[data-testid="composer"]').outerHTML,
    tail: [...document.querySelector('[data-testid="chat-log"] > div').children].slice(-1)[0]?.outerHTML ?? "",
  }));
  await shot(page, "working");
  await page.context().close();

  // The start page, before anything is sent.
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 861 }, deviceScaleFactor: 1 });
  await ctx.addInitScript(DESKTOP);
  page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  out.home = await page.evaluate(() => document.getElementById("root").outerHTML);
  await shot(page, "home");

  await browser.close();
  fs.writeFileSync(path.join(OUT, "scene.json"), JSON.stringify(scrub(out)));
  console.log(`${OUT}: ${out.tools.length} calls, ${out.details.length} details, ${out.agents.length} replies`);
})();
