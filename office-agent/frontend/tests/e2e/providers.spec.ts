import { expect, test } from "@playwright/test";

test("Discover lists providers with their logos, and a provider's page offers its key link and form", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByText("Providers", { exact: true }).first().click();

  await page.getByRole("button", { name: "Discover", exact: true }).first().click();
  for (const name of ["Anthropic", "OpenAI", "Google Gemini", "DeepSeek", "Qwen", "OpenRouter", "Ollama"]) {
    const card = page.getByRole("button", { name: `Open ${name}` });
    await expect(card).toBeVisible();
    // The provider's own logo, not a letter.
    await expect(card.locator("img")).toHaveCount(1);
  }

  await page.getByRole("textbox", { name: "Search providers" }).fill("qwen");
  await expect(page.getByRole("button", { name: "Open DeepSeek" })).toHaveCount(0);
  await page.getByRole("button", { name: "Open Qwen" }).click();

  await expect(page.getByText("Qwen", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Get an API key" })).toHaveAttribute("href", /aliyun/);
  await expect(page.getByRole("textbox", { name: "Base URL" })).toHaveValue(/dashscope\.aliyuncs\.com/);
  await expect(page.getByRole("button", { name: "Add provider" })).toBeVisible();
});
