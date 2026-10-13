import { defineConfig } from "vitest/config";

// Separate from vite.config.ts so unit tests skip the React and Tailwind
// plugins; `include` keeps vitest off the Playwright specs in tests/e2e,
// which fail when loaded outside Playwright's runner.
export default defineConfig({
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "node",
  },
});
