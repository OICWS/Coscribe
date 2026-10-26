# The conversation stays where the person is reading; Backspace takes the kind chip off (shipped)

Why: an approval card (or any new line) pulled the view to the bottom while the person was reading
above, and the "Slides"/"Design system" chip of a new conversation could be removed only through its
menu.

## Shipped
- `lib/useFollowEnd.ts`: the chat log follows new items only while it is scrolled to the end (within
  80 px). Scrolled up, an approval card or streamed text lands below and the view stays. Sending a
  message always brings the end back.
- Backspace in an empty message box removes the kind chip (`Composer`), as the chip's menu does.
- Tests: `tests/e2e/artifacts.spec.ts` (Backspace takes the chip off only from an empty box).

## Not verified
- The follow behaviour is not covered by an automated test (a stub model answers too fast to
  scroll up in between); it was checked by reading the code.
- Windows and the desktop app.
