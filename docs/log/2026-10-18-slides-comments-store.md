# Slides step 3, part 1: comments are stored beside the pages, and a slide names its elements

Why: design §5. A comment sits on an element of a slide and can be sent to coscribe. The panel
draws an unedited slide as a picture, so it needs to know what is where on it (issue #420).

## Shipped
- `read_deck` gives each slide its `elements`: every shape, inside groups too, with its box as
  fractions of the slide and a label. Labels look like `Title "Q3 review"`, `Text "896k"`,
  `Chart`, `Table`, `Picture`, `Shape` or `Line`. A group's child coordinates are mapped through
  its chOff/chExt.
- `engine/view_comments.py`: `comments.json` in the deck's pages folder, written under a file
  lock and replaced in one step.
  - A comment holds the slide (page name), the point (fractions), the element's label, the text,
    the author, whether it was sent to coscribe, whether it is resolved, and its replies.
  - A damaged store reads as no comments, so it never stops the deck from opening.
- Routes under `/api/threads/{id}/slides/comments`:
  - GET lists the comments; POST adds one;
  - `/{id}/replies` replies (`from_coscribe` marks coscribe's answer);
  - POST `/{id}` resolves or reopens; DELETE removes.
  - The author is the computer's user name, as Word does. Text is 1 to 4,000 characters (422
    otherwise).
- Tests: elements and the store in `tests/test_deck_view.py`, the routes in
  `tests/web/test_thread_activity.py`.

## Follow-ups
- Part 2: the panel's comment mode, markers, threads and Send to coscribe.
