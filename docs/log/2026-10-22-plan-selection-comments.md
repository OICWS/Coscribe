# Comments on selected plan text

Why: #506, PR 4 of 4. In the reference you select words in the plan, leave a comment, and Claude gets the quote with it.

## Shipped
- Selecting text in the Plan panel opens an "Add a comment" box under it; Enter or the plus adds the comment, Esc cancels.
- Comments are listed under the plan and can be removed. They are kept per plan text, so they survive closing the panel and are the same in a pop-out window.
- Revise sends them inside the feedback as the quoted words followed by the comment; they are cleared once sent.
- `lib/planComments.ts` with unit tests; `plan-comments.spec.ts` selects a line, comments, revises.

## Not verified
- Not run on Windows or in the desktop shell; the pop-out window path (comments sent to the main window by IPC) is type-checked only.
- Selection by touch or with the keyboard alone was not tried.

## Follow-ups
- None open for #506.
