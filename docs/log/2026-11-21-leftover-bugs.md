# Three leftover bugs: Office left running after a conversion timeout, a rounded picture's shadow, a spec that ran once (shipped)

Why: two engineering follow-ups found while scripting the Windows checks (#393) and one engine
refusal found while writing the exported-deck check (#472) were never fixed or tracked.

## Shipped
- `tools/_office_com.py`: COM starts Word, Excel, PowerPoint or WPS for a conversion as a child of
  its own service with `-Embedding`, not of PowerShell, so the timeout's `taskkill /T` left the
  program running hidden with the file open. On a timeout the copies of that program with
  `-Embedding` started since the job began are now ended; one the user opened, or the user's
  PowerPoint that was already running, is left alone. The scripts also close the program in a
  `finally`, so a file it cannot open no longer leaves it running.
  `tests/test_windows_real.py` checks the real process query on the Windows runner
  (`windows-more-checks.yml`, which now also runs when `_office_com.py` changes).
- Deck engine (`engine/sections.py`, `engine/section_view.py`): an `<img>` with both
  `border-radius` and `box-shadow` was refused ("cannot combine filter and clip-path"). The
  shadow now goes on a group around the clipped image, which the converter reads as that
  picture's own effect: one `<p:pic>` with the rounded geometry, its outline and the outer
  shadow. `scripts/check_deck_export.py` now checks the shadow on the rounded picture.
- `frontend/tests/e2e/skill-plugins.spec.ts` removes the Legal plugin's Discover skills before
  and after it runs, so a second run in the same workspace finds the Add button again (checked:
  the old spec failed on its second run here; the new one passed three runs in a row).

## Not verified
- A real Office or WPS conversion that times out on a Windows machine: the runner has no Office,
  so its test uses a stand-in process with `-Embedding`. WPS's process names (`wps.exe`,
  `et.exe`, `wpp.exe`) are not checked against a real install.
- The rounded, shadowed picture opened in the real PowerPoint.
