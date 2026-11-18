# The top-level docs catch up with the work merged up to 2026-11-18 (shipped)

Why: the maintainer asked whether README, ARCHITECTURE.md and the other living documents still
held after the workspace, browser, providers and chat changes of 2026-11-11 to 2026-11-18.

## Shipped
- `ARCHITECTURE.md`: no per-turn model-call cap any more (a reply runs until the model is done or
  the person stops it; a scheduled run keeps its task's step count, from
  `2026-11-11-capability-switches-no-step-cap.md`); workspaces (decisions 0048, 0050) and the
  Sessions page in "Shape of the system"; "environment" read as workspace where a person sees it;
  the browser's per-site levels and acting from a picture; the provider presets.
- `README.md`: the provider presets.
- `SECURITY.md`: "workspace" for the command sandbox's network, and what the built-in browser
  promises (its own profile, the site levels, approvals).
- `office-agent/README.md`, Web UI: the Providers tab as it is now (Yours, Discover, a page per
  provider, routes in `web/routes/settings/providers.py`; there is no API Keys tab), Rewind and
  Edit on sent messages, the Sessions page, Export a failed turn, the struck-through plan steps.
- `docs/plan.md`: reviewed today; the "Later" line about the environment dialog's old messages
  section is gone, since the one-page workspace dialog has none.

## Not verified
- Nothing to run: a docs change. The wording was checked against the code and the log entries
  it names.

## Follow-ups
- `docs/manual-checks.md` still says "Settings > Environment" (steps 4 and 10); left to #958,
  which is changing that file.
- The website (`site/index.html`) shows the old Providers form in its mock-up of the app.
- `docs/plan.md` is about 245 lines against its own limit of about 150.
