# Pictures from the message box saved in `.coscribe/uploads/` too (shipped)

Why: a picture attached or pasted went to the model only inline, so it could see it but not put
it in a document or a deck; it had no path (#926 phase B, decision 0044).

## Shipped
- A picture attached from the computer or pasted is uploaded as it is added to the tray: an
  attached one into `images/` under its own name, a pasted screenshot (the clipboard's
  `image.png`) into `screenshots/` named by date and time. It is still sent inline as well.
- The note that names a message's files for the model lists the pictures' paths too.
- A sent message shows its pictures as pictures, not again as file cards, also after a reload
  (`fileCards` in `lib/attachments.ts`).
- A picture that can't be saved (a folder that can't be written) is still sent, without a path.

## Not verified
- On Windows: pasting a screenshot taken with Win+Shift+S in the desktop app.

## Follow-ups
- A picture picked from the browser panel or the slide preview is not saved; it has no file of
  its own.
