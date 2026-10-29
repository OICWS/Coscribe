# A Word file's card opens it in Word; the Outputs list drops files that are gone (shipped)

Why: the maintainer's packaged app after the Word editor was removed (decision 0027): the card at the
end of a turn for a `.docx` did nothing when clicked, and the Outputs list kept scratch files the run
had made and deleted ("No longer on disk").

## Shipped
- A chip or end-of-turn card for a file the app has no panel for (a Word file) opens it in the program
  the computer keeps for it, as the Outputs row and the file menu already did (`openMentioned`).
- `getThreadActivity` leaves out outputs that no longer exist, so the list and its count show only
  what is there.
- `chat-files.spec.ts`: a Word card click asks the server to open the file and opens no panel.

## Not verified
- Word itself starting from the card: the server call is checked, the OS hand-over is not (no Word here).
