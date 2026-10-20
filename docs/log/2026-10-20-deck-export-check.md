# An exported-deck check runs on the Windows runner (shipped)

Why: issue #472, item 2. The Slides panel writes style properties into section pages; the unit
tests check each one on Linux, but nothing read a whole built deck on Windows.

## Shipped
- `office-agent/scripts/check_deck_export.py` builds one deck of three section pages through
  `build_deck` and reads the .pptx XML: text size and style; a picture's rounded geometry,
  outline and opacity (and, on a second picture, its outer shadow); a shape's fill, radius, border
  and shadow; a chart's title, legend, data labels, series colours and stacked grouping; a row of
  cards becoming plain shapes with no container left; the file opening in python-pptx with three
  slides.
- `windows-checks.yml` runs it (and runs on a pull request that changes the script).
- Proved by breaking it: with `convert_image` not writing the picture's outline, the check fails
  on the missing `<a:ln w="38100">`; restored, it passes.

## Not verified
- The run on `windows-latest`: only the Linux run in the cloud session was done.

## Follow-ups
- The engine refuses a picture that has both `border-radius` and `box-shadow` ("cannot combine
  filter and clip-path"); the check keeps them on two pictures. Noted on #472.
