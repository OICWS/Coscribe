# `coscribe.tools` drops 10 names nothing uses, and its size is ratcheted (shipped)

Why: `coscribe.tools.__all__` had 230 names and its card and `slice.py` open every slice with the
list (issue #677). The measurement (`docs/metrics/2026-10-28-tools-interface-usage.md`) found 10
names no module of `src` or `tests` imports from `coscribe.tools`.

## Shipped
- `fallbacks_for_platform`, `UnisolatedConversations`, `working_interpreters`, `MessagingError`,
  `HandOff`, `RunningCommand`, `ScheduleRule`, `TemplateInfo`, `LibreOfficeStatus` and
  `load_builtin_templates` leave `tools/__init__.py` and its card: 230 to 220. They stay in the
  sub-component or module that defines them; only the re-export at the top is gone.
- `ratchet.py` gets `interface_size`: the number of names in `__all__` of every package that
  has more than 50 (`tools` 220, `runtime_lg` 72, `tools.exec` 65, `tools.bookkeeping` 55).
  A new name or a bigger number is worse. `tests/test_ratchet.py` covers it.

## Not verified
- Dynamic uses (`getattr`, strings) of the ten names: none found by `grep -w` over the repository.

## Follow-ups
- #677 item B, one PR per sub-component, once `deep_imports` counts a declared sub-component
  as an entry.
