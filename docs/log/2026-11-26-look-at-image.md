# The agent looks at picture files itself (shipped)

Why: on the OmegaUse-OfficeVal run (#1078) the 48 tasks that come with a picture (a scan to
redraw as an editable slide, a chart to rebuild) scored 0.41 against 0.55 for the rest. The agent
had no way to see a picture in the workspace: it measured pixels in scripts and told the person
"there is no OCR on this machine" about words it could have read. A picture the person attached
in the message box was already seen; one in the folder was not.

## Shipped
- `look_at_image(path)` (`conversation/look_image.py`, beside `look_at_page`), read only and
  deferred: the picture as the model's own input, upright (EXIF), at most 1568 px on its long
  side, with its real size. It also opens a preview a render tool returned by its name, so the
  agent can check its own deck or document instead of only the reviewer seeing it.
- `read_file` on a picture points to it, and the prompt says to look at a picture a task hands
  over before working from it; the line that said the agent cannot see images is gone.
- Checked live: DeepSeek Flash reads a picture sent this way.

## Not verified
- The desktop app on Windows; the effect on OfficeVal scores is measured in the rerun on #1078.
- A text-only model refuses the picture, as it does look_at_page's (`docs/plan.md`).

## Follow-ups
- None beyond the open item on which models take images.
