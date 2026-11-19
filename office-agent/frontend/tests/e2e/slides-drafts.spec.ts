import { expect, test } from "@playwright/test";
import { freshThreadPath, waitForConnected } from "./helpers";

const SVG = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'><rect width='1280' height='720' fill='#eef'/></svg>";

test("only the matching active build can show source pages, and moved deck cards disappear", async ({ page }) => {
  const old = "deck-new.pptx";
  const current = "deck.pptx";
  let exists = true;
  let send: (event: unknown) => void = () => {};
  await page.route("**/files/download?**", (route) => {
    const path = new URL(route.request().url()).searchParams.get("path");
    return path?.endsWith(".svg")
      ? route.fulfill({ body: SVG, contentType: "image/svg+xml" })
      : route.fulfill({ status: path === current || (path === old && exists) ? 200 : 404 });
  });
  await page.route(/\/slides\?path=/, (route) => route.fulfill({ status: 404, json: { error: "No deck" } }));
  await page.routeWebSocket("**/ws/**", (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    send = (event) => socket.send(JSON.stringify(event));
    server.onMessage((message) => {
      const event = JSON.parse(String(message));
      if (event.type === "history") event.entries = [
        { kind: "user", text: "Build a presentation" },
        { kind: "tool", tool_name: "write_file", arguments: { path: "pages/01-cover.svg" }, result: "Written" },
        { kind: "tool", tool_name: "build_pptx_from_pages", arguments: { path: old, pages_dir: "pages" }, result: "Built" },
        { kind: "tool", tool_name: "write_file", arguments: { path: current }, result: "Written" },
      ];
      send(event);
    });
  });
  await page.goto(freshThreadPath("slides-drafts"));
  await waitForConnected(page);

  const card = page.getByTitle(`Open ${old}`, { exact: true });
  await expect(card).toBeVisible();
  send({ type: "turn_started", text: "Build a new version" });
  send({ type: "tool_started", tool_name: "build_pptx_from_pages", arguments: { path: current, pages_dir: "pages" } });
  await card.click();
  await expect(page.getByText("No deck", { exact: true })).toBeVisible();
  await expect(page.getByText("1 page so far")).toHaveCount(0);

  await page.getByTitle(`Open ${current}`, { exact: true }).click();
  await expect(page.getByText(/1 page so far/)).toBeVisible();
  await expect(page.getByRole("img", { name: "01-cover.svg" })).toBeVisible();

  exists = false;
  send({ type: "tool_result", tool_name: "move_file", arguments: { source: old, destination: current }, result: { source: old, destination: current }, is_error: false });
  await expect(card).toHaveCount(0);
});
