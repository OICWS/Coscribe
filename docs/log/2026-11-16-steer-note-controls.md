# A note sent while the reply runs has copy, rewind, cancel-and-edit and Send now controls (shipped)

Why: a message sent while the agent works waits under the reply as a note. Its row had only a bare
X and "Send now", and the X put the note back into the message box even over a draft there.

## Shipped
- `frontend/src/components/chatlog/UserMessageView.tsx` (`SteerView`): the waiting note's row is
  copy, rewind, X and Send now. Rewind is always disabled there (nothing can be rewound while a reply
  runs), with a dark tooltip saying so; the X reads "Cancel and edit message"; Send now darkens to a
  gray background on hover. The tooltips sit on a wrapper, so a disabled button still shows why.
- The X is disabled while the message box holds text or attachments, since taking the note back
  would overwrite them; its tooltip says to clear the box first. `Composer` reports whether it holds
  a draft (`onHasDraftChange`), and `App.tsx` passes that into `SteerActions.composerHasDraft`.
- `UserMessageView.test.tsx`: the X is enabled with an empty box and disabled over a draft; rewind is
  disabled with its reason.

## Not verified
- Looked at only as the row rendered on its own with the built CSS (Playwright screenshots), not in
  the running app on Windows; the X going gray as the box fills was not tried by hand there.
