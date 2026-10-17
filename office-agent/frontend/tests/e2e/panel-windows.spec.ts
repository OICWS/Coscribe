import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

// The desktop shell's part (office-agent-desktop's main/panelWindows.ts)
// stood in for by two pages relaying through a BroadcastChannel, the way
// the shell relays between the main window and a panel's own window.
const bridge = () => {
  const channel = new BroadcastChannel("panel-windows");
  const mine = new URLSearchParams(location.search).get("panelWindow");
  const last: Record<string, unknown> = {};
  type Message = { t: string; panel: string; [key: string]: unknown };
  const listen = (type: string, cb: (m: Message) => void) => {
    const handler = (e: MessageEvent<Message>) => e.data.t === type && cb(e.data);
    channel.addEventListener("message", handler);
    return () => channel.removeEventListener("message", handler);
  };
  if (!mine) listen("ready", (m) => last[m.panel] && channel.postMessage({ t: "state", panel: m.panel, state: last[m.panel] }));
  const shell: Record<string, unknown> = {
    platform: "win32",
    openPanelWindow: async (request: unknown) => {
      (window as unknown as { opened: unknown }).opened = request;
    },
    listPanelWindows: async () => [],
    sendPanelWindowState: (panel: string, state: unknown) => {
      last[panel] = state;
      channel.postMessage({ t: "state", panel, state });
    },
    onPanelWindowAction: (cb: (p: unknown) => void) => listen("action", (m) => cb({ panel: m.panel, action: m.action })),
    onPanelWindowClosed: (cb: (p: unknown) => void) => listen("closed", (m) => cb({ panel: m.panel, dock: m.dock })),
    onPanelWindowState: (cb: (s: unknown) => void) => {
      const stop = listen("state", (m) => m.panel === mine && cb(m.state));
      channel.postMessage({ t: "ready", panel: mine });
      return stop;
    },
    sendPanelWindowAction: (action: unknown) => channel.postMessage({ t: "action", panel: mine, action }),
    dockPanelWindow: () => channel.postMessage({ t: "closed", panel: mine, dock: true }),
    setPanelWindowPinned: async (pinned: boolean) => pinned,
    setTitleBarColors() {},
    onBrowserAgent: () => () => {},
  };
  (window as unknown as { coscribeDesktop: unknown }).coscribeDesktop = shell;
};

test("a panel opens in its own window, keeps its switch on, and comes back where it was", async ({ context, page }) => {
  await context.addInitScript(bridge);
  await page.goto(freshThreadPath("panel-windows"));
  await page.evaluate(() => localStorage.removeItem("coscribe.panelLayout"));
  await page.reload();
  await waitForConnected(page);
  await page.locator("textarea").fill("Reply with just the word ok.");
  await page.keyboard.press("Enter");
  await page.getByTitle("Show task details").click();

  await page.getByRole("button", { name: "Expand Task details" }).hover();
  await page.getByRole("menuitem", { name: "Open in new window" }).click();
  await expect(page.getByRole("region", { name: "Task details", exact: true })).toBeHidden();
  await expect(page.getByTitle("Hide task details")).toHaveAttribute("aria-pressed", "true");
  const opened = await page.evaluate(() => (window as unknown as { opened: { panel: string; threadId: string } }).opened);
  expect(opened.panel).toBe("task");

  const own = await context.newPage();
  await own.goto(`/?panelWindow=${opened.panel}&thread=${opened.threadId}`);
  await expect(own.getByText("Context", { exact: true })).toBeVisible();
  await expect(own).toHaveTitle("Task details · coscribe");
  const pin = own.getByRole("button", { name: "Keep on top" });
  await pin.click();
  await expect(pin).toHaveAttribute("aria-pressed", "true");

  await own.getByRole("button", { name: "Return to the main window" }).click();
  await expect(page.getByRole("region", { name: "Task details", exact: true })).toBeVisible();
});
