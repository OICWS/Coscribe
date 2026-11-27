import { expect, test, type Page } from "@playwright/test";
import type { WsServerEvent } from "../../src/types/wire";
import { freshThreadPath, waitForConnected } from "./helpers";

async function openSimpleConversation(page: Page) {
  let send: (event: WsServerEvent) => void = () => { throw new Error("The conversation socket is not open"); };
  await page.route("**/api/config", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: {
      ...await response.json(), COSCRIBE_CONVERSATION_VIEW: "simple", COSCRIBE_MOTION: "system",
    } });
  });
  await page.routeWebSocket("**/ws/**", (socket) => {
    const server = socket.connectToServer();
    send = (event) => socket.send(JSON.stringify(event));
    server.onMessage((message) => socket.send(message));
  });
  await page.goto(freshThreadPath("activity-robot"));
  await waitForConnected(page);
  send({ type: "turn_started", text: "Review the figures." });
  return send;
}

test("the Simple activity robot finishes each gesture before using the latest activity", async ({ page }) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date(Date.now() + 1_000));
  const send = await openSimpleConversation(page);
  const status = page.getByTestId("simple-status");
  const robot = status.getByTestId("activity-robot");

  await expect(status.getByText("Thinking", { exact: true })).toBeVisible();
  await page.clock.runFor(1_450);
  await expect(robot).not.toHaveAttribute("data-gesture");
  await page.clock.runFor(1_280);
  await expect(robot).not.toHaveAttribute("data-gesture");
  await expect(robot.locator("[data-part=head]")).toHaveAttribute("opacity", "0");
  await page.clock.runFor(840);
  await expect(robot).toHaveAttribute("data-gesture", "Thinking");
  const eye = robot.locator("[data-part=head] path").first();
  const atEntrance = await eye.getAttribute("d");
  expect(atEntrance).toBeTruthy();

  const activities = [
    ["run_python_script", "Running commands"],
    ["read_xlsx", "Reading"],
    ["write_file", "Writing"],
    ["edit_file", "Editing"],
    ["web_search", "Searching"],
    ["browser_navigate", "Browsing"],
    ["remember", "Working"],
  ] as const;
  let previous = "Thinking";
  for (const [tool, label] of activities) {
    send({ type: "tool_started", tool_name: tool, arguments: {} });
    await expect(status.getByText(label, { exact: true })).toBeVisible();
    await expect(robot).toHaveAttribute("data-gesture", previous);

    await page.clock.runFor(800);
    await expect(robot).toHaveAttribute("data-gesture", previous);
    if (previous === "Thinking") await expect(eye).not.toHaveAttribute("d", atEntrance!);
    await page.clock.runFor(3_780);
    await expect(robot).not.toHaveAttribute("data-gesture");
    await page.clock.runFor(920);
    await expect(robot).toHaveAttribute("data-gesture", label);
    send({ type: "tool_result", tool_name: tool, arguments: {}, result: "ok", is_error: false });
    await expect(status.getByText("Thinking", { exact: true })).toBeVisible();
    previous = label;
  }

  send({
    type: "approval_required", id: "confirm", tool_name: "run_python_script", arguments: {},
    before_preview: null, after_preview: null, reviewer_note: null,
  });
  await expect(robot).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeVisible();
});

test("a system motion preference freezes the robot and leaves the activity visible", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const send = await openSimpleConversation(page);
  const status = page.getByTestId("simple-status");
  const robot = status.getByTestId("activity-robot");
  const dot = robot.locator("[data-part=dots] circle").first();
  await expect(dot).toHaveAttribute("cx", "19");
  await expect(robot.locator("[data-part=head]")).toHaveAttribute("opacity", "0");

  send({ type: "tool_started", tool_name: "web_search", arguments: {} });
  await expect(status.getByText("Searching", { exact: true })).toBeVisible();
  await expect(dot).toHaveAttribute("r", "3.25");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(robot).toHaveAttribute("data-gesture", "Searching");

  send({ type: "agent_message", text: "Reviewed the figures." });
  await expect(robot).toHaveCount(0);
  await expect(page.getByText("Reviewed the figures.", { exact: true })).toBeVisible();
});
