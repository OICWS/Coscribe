# A run waits for the person on a sign-in, and heals the newer browser steps (shipped, part 4a of #915)

Why: a saved workflow whose site logged it out failed, or its heal tried to click past the sign-in
form; and the heal agent could not redo a step made with the tools parts 1 to 3 added (#915).

## Shipped
- When a browser step fails, the desktop app looks at the page (`browserAgentSignIn.ts`): a
  captcha (reCAPTCHA, hCaptcha, Cloudflare, GeeTest or an element named captcha), a one-time-code
  field, or a password field on a page that says sign in or log in (its path, title, a heading or
  button; also 登录). A password field alone, as on a settings page, is not enough. The error then
  carries a mark the server turns into a `NeedsPermission` of kind `sign_in`.
- A saved workflow's run waits on it like on a folder or site (decision 0033's pause), with no heal
  and no retry: the card says what the site asks for, "Done, continue" runs the step again from
  its start, "Stop the run" fails it. The tray notification says "Needs you to sign in to <site>".
  A test run, which may not ask, fails with the same words. In a conversation the model gets them
  with a hint to ask the person and never type a password or code it was not given.
- Healing (decision 0030) also drags and copies; it pastes or saves a table or PDF only to redo a
  step that does that itself, as it opens a page only for a step that opened one.
- Tests: `scripts/browser-native.cjs` serves a sign-in page and a settings page with a password
  field over HTTP and checks only the first is marked; pytest covers the mark, the wait and
  continue without a heal, the notification and the heal's tools.

## Not verified
- A person using the Windows app; real sign-in pages (SSO, a bank's code prompt, a slider
  captcha) on real sites.

## Follow-ups
- Part 4b of #915: acting from a screenshot, watching a page for changes on a schedule.
