# Varied home greeting and a Profile section in Settings (shipped)

Why: the home screen said one of three fixed lines. The request was for more
variety (night owl and so on) and for the greeting to use the person's name.

## Shipped
- `frontend/src/lib/greetings.ts`: `pickGreeting(date, name, random)` draws from a pool
  by local time of day, plus Monday, Friday and weekend lines. Lines with `{name}` are
  only drawn when a name is set. English only.
- `HomeGreeting` picks once per mount and waits for the config before drawing, so the
  line doesn't change after it shows.
- Settings > General > Profile: "What should Coscribe call you?" and "What best
  describes your work?", stored as `COSCRIBE_USER_NAME` / `COSCRIBE_USER_ROLE` in `.env`
  (`PROFILE_ENV_VARS`, no restart needed).
- Unit tests in `lib/greetings.test.ts`.

## Not verified
- Not looked at in the running app or on Windows; only the build, lint and unit tests.

## Follow-ups
- The work description is stored but not yet sent to the model. That belongs with the
  first-run setup work: it must reach the model in a message, not the system prompt.
