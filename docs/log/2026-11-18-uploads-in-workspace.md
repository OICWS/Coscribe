# Attachments saved in the workspace's `.coscribe/uploads/` (shipped)

Why: an attached file landed in the root of the person's folder beside their own files, and a
second `image.png` became `image (3).png` there (#926 phase B, decision 0044).

## Shipped
- `POST /api/upload` saves into the conversation's main folder under `.coscribe/uploads/<kind>/`:
  `images`, `documents`, `data` or `other`, by extension. The path the model gets is relative to
  that folder, as before, and a name already taken gets ` (1)`, never an overwrite.
- A `pasted` form field puts a picture in `screenshots/` as `screenshot-<date>-<time>.png`.
- A folder that can't be written answers 409 with the folder's path instead of a server error.
- A name of `.` or `..` is saved as `upload`.

## Not verified
- On Windows: an upload into a workspace folder on a shared drive.

## Follow-ups
- The message box sends pictures to the model inline and saves none of them; next it uploads
  each one too (pasted ones with `pasted`) and tells the model the path.
- The one-line description of each upload in `uploads/index.jsonl` from the side model.
- A conversation without a workspace keeps its attachments in the state folder (phase C).
