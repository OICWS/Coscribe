import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/** Real application chrome and native page; usage/history are fixtures, with no model call. */
export async function checkBrowserOverlay(app, window, until) {
  let threadId;
  await window.routeWebSocket("**/ws/**", route => {
    threadId = new URL(route.url()).pathname.split("/").at(-1);
    const server = route.connectToServer();
    route.onMessage(message => server.send(message));
    server.onMessage(message => {
      const event = JSON.parse(String(message));
      if (event.type === "state") event.context_window = 1_000_000;
      if (event.type === "history") event.entries = [
        { kind: "user", text: "Check the browser while Context usage is open." },
        { kind: "agent", text: "Browser regression check: the page should remain visible beside this conversation." },
      ];
      route.send(JSON.stringify(event));
      if (event.type === "history") route.send(JSON.stringify({ type: "usage", total_tokens: 574300,
        cache_read_tokens: 573700, input_tokens: 574000, cache_hit_rate: 1 }));
    });
  });
  await window.route("**/api/threads/*/context-breakdown", route => route.fulfill({ json: {
    context_window: 1_000_000, total_tokens: 574300, total_is_estimated: false,
    categories: [
      { key: "messages", label: "Messages", tokens: 525900 },
      { key: "system_tools", label: "System tools", tokens: 40900 },
      { key: "system_prompt", label: "System prompt", tokens: 6700 },
      { key: "skills", label: "Skills", tokens: 731 },
      { key: "autocompact_buffer", label: "Autocompact buffer", tokens: 200000 },
      { key: "free_space", label: "Free space", tokens: 225769 },
    ],
  } }));
  await window.reload();
  await window.getByTitle("Context window", { exact: true }).waitFor();
  await app.evaluate(({ BrowserWindow, screen }) => {
    const host = BrowserWindow.getAllWindows()[0];
    host.setBounds(screen.getPrimaryDisplay().workArea);
    host.show(); host.focus();
  });
  await app.evaluate(({ BrowserWindow }, id) => {
    BrowserWindow.getAllWindows()[0].webContents.send("browser-panel:agent", { open: true, threadId: id });
  }, threadId);
  const area = window.getByTestId("browser-page-area");
  await area.waitFor();
  const html = '<title>Browser form check</title><style>body{font:16px system-ui;margin:0;background:#f1f5f9;color:#16324f}header{background:#164e80;color:white;padding:24px}main{margin:24px;padding:24px;background:white;border-radius:12px}label{display:block;margin:16px 0}input{display:block;margin-top:6px;padding:10px;border:1px solid #b7c5d3;border-radius:6px}</style><header>Browser form check</header><main><h2>The page remains visible</h2><p>Open Context usage beside this form.</p><label>Company code<input value="1000"></label><label>Posting date<input value="2026-11-17"></label><p>Page updates: <span id="ticks">0</span></p></main><script>let n=0;setInterval(()=>ticks.textContent=++n,100)</script>';
  await window.evaluate(url => window.coscribeDesktop.browserPanelNavigate(url), `data:text/html,${encodeURIComponent(html)}`);
  const bounds = () => app.evaluate(({ BrowserWindow }) => {
    const views = BrowserWindow.getAllWindows()[0].contentView.children;
    return views.find(view => view.webContents?.getURL().startsWith("data:text/html,"))?.getBounds();
  });
  await until("the native browser layout to settle", 5000, async () => {
    const native = await bounds(), box = await area.boundingBox();
    return native?.x >= 0 && ["x", "y", "width", "height"].every(key => native[key] === Math.round(box[key]));
  });
  const original = await bounds();
  await window.getByTitle("Context window", { exact: true }).click();
  const popup = window.getByRole("dialog", { name: "Context usage" });
  await popup.waitFor();
  await popup.getByText("Free space", { exact: true }).waitFor();
  // Wait for native visibility effects, not just the React popover's mounting.
  await window.waitForTimeout(250);
  assert.deepEqual(await bounds(), original, "a non-overlapping Context card must not hide or move the native page");
  assert.equal(await area.locator("img").count(), 0, "an uncovered page stays live");
  if (process.env.COSCRIBE_BROWSER_SCREENSHOT_DIR) {
    mkdirSync(process.env.COSCRIBE_BROWSER_SCREENSHOT_DIR, { recursive: true });
    const png = await app.evaluate(async ({ desktopCapturer, screen }) => {
      const { size } = screen.getPrimaryDisplay();
      const [source] = await desktopCapturer.getSources({ types: ["screen"], thumbnailSize: size });
      return source.thumbnail.toPNG().toString("base64");
    });
    writeFileSync(join(process.env.COSCRIBE_BROWSER_SCREENSHOT_DIR, "context-full-app.png"), Buffer.from(png, "base64"));
  }
  const page = await area.boundingBox();
  await popup.evaluate((element, x) => { element.style.left = `${x}px`; }, page.x + 20);
  await until("an overlapping card to preserve the page image", 5000, async () =>
    (await bounds())?.x < 0 && await area.locator("img").isVisible());
  await window.keyboard.press("Escape");
  await until("the live page to return after the card closes", 5000, async () =>
    (await bounds())?.x >= 0 && await area.locator("img").count() === 0);
  await window.getByTitle("Settings", { exact: true }).first().click();
  await window.getByRole("button", { name: "Close settings", exact: true }).waitFor();
  await until("Settings to keep native content behind it", 5000, async () => (await bounds())?.x < 0);
  await window.getByRole("button", { name: "Close settings", exact: true }).click();
  await until("the browser to return after Settings", 5000, async () => (await bounds())?.x >= 0);
}
