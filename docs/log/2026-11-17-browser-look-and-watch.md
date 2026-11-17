# The AI sees a page as a picture, clicks by position, and a task watches a page (shipped, part 4b of #915)

Why: canvases, charts, maps and icons without a label had no element for the AI to name; and a
person who wanted to know when a price, a status or a notice changed had no way to say so in a
task (#915, items 10 and 16).

## Shipped
- `browser_screenshot` returns the visible part of the page as a picture (at most 1280 pixels
  wide) with its size; `browser_click_at(x, y, double)` clicks a point of it. The desktop app keeps
  how many page pixels one picture pixel is from the last look and scales the click back
  (`browserAgentLook.ts`, `lookScale`), and refuses a point outside the page's visible part. The
  picture travels as look_at_page's does: moved into a user message after the tool results.
- `browser_read_text(near)` reads the block a label sits in ("Price ¥89"), or the one around it
  when the label is a block of its own (`<dt>Price</dt><dd>¥89</dd>`), waiting for it to appear;
  empty reads the whole page. A workflow reads `{{<save_as>.text}}`.
- Watching a page is a task: read the value, a check `ne` the remembered one with
  `"otherwise": "end"` (decision 0034: a run with nothing new ends quietly), then a remember step.
  The drafting prompt describes that shape. A completed run's notification now names the text and
  number values it remembered by their labels ("Completed · Price: ¥89"); dates and lists stay out.
- Healing (decision 0030) may also read text, look and click by position; the drafting prompt
  keeps a click by position only where nothing could be named, noted as layout-dependent.
- Tests: `scripts/browser-native.cjs` clicks a canvas by position and checks the page got the
  same point, refuses one off the page and reads a value next to two kinds of label; pytest covers
  the tools, a watching task that runs, then ends quietly on the same value, the notification and
  the heal's tools.

## Not verified
- Which configured models take images. DeepSeek documents image input for a vision model only
  (api-docs.deepseek.com/guides/vision); a model without image input refuses the picture, as it
  refuses look_at_page's. Checking that per model before offering the tool is open in
  `docs/plan.md`.
- A person using the Windows app; a click by position at a display scale other than 100%.

## Follow-ups
- Tell a text-only model's conversation not to call browser_screenshot.
