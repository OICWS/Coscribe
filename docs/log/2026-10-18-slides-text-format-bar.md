# Slides editing, part 4: text and the format bar

Why: typing into a slide and the floating format bar from the maintainer's mockups (design §3,
issue #431).

## Shipped
- Typing in place: a double-click on text (or Enter on a selected text element) makes its drawn
  text editable, with the caret where the click was. Enter breaks the line (a new item in a
  list), pasted text arrives as plain text, and Escape or a press outside the text ends the
  typing. The text is then written back in the section language's own tags (`b`, `i`, `u`,
  `br`, `span` with a colour, `li`): what the browser adds while typing is turned into those or
  left out. The slide is saved only when the text changed.
- The format bar over the selected element, as the mockups draw it:
  - for text, its style (Title, Heading, Lead, Body, Caption), its colour (the slide's own
    colours, most used first, or any hex colour), bold, italic, underline, link (shown, not
    available: slides have no links yet), bulleted list and alignment. With words selected while
    typing, bold, italic, underline and colour apply to those words; otherwise to the element;
  - for every element, a comment on it (opens the new-comment box naming the element) and More:
    bring forward, send backward, duplicate, delete.
- `lib/slideSource.ts` gained the presets, the slide's colours and `retag` (a paragraph to a list
  and back), with tests.

## Checked
- In Chromium against a live server, slide 2 of the Q3 deck: a line made bold, typed into and
  saved; its style changed to Caption; a colour picked; the More menu; a comment opened from the
  bar.

## Not verified
- Typing with a Chinese IME (Microsoft Pinyin on Windows) inside the scaled slide.
