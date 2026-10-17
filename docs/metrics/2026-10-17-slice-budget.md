# Slice size of three sample changes (static estimate)

What this is: `office-agent/scripts/slice.py` run on the file a typical change would start
from. It counts the files and tokens a session reads by the discovery protocol in the root
`AGENTS.md` (card, interface, the component's own files, its tests). Tokens are file size
divided by 4. It is not a measurement of a fresh session doing the change.

| Change starts at | Component | Files | Tokens | Budget (15 files, 150k) |
|---|---|---|---|---|
| `tools/office/docx/` (a Word tool) | `tools.office.docx` | 7 | ~27.8k | inside |
| `tools/web/http_request.py` (the HTTP tool) | `tools.web` | 8 | ~17.9k | inside |
| `frontend/src/App.tsx` (the UI shell) | `frontend` | 1 | ~12.5k | inside, but no card and no tests listed |

## Finding
- The two backend slices are far inside the budget.
- The frontend has no card and no component split, so the script finds only the file itself:
  the 12.5k is the one file, not the slice a UI change really needs (types, the components App
  renders, the specs). That is the next gap; item 5 or 6 of #348 is where it gets fixed.

## Not verified
- Whether a fresh session stays inside the budget on a real change. That needs sessions that
  make the changes; not run here.
