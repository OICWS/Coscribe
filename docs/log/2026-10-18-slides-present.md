# Slides panel, part C1: Present, and Present with speaker notes

Why: the mockups' play button presents the deck over the panel, with a bar of previous, page,
next, notes, full screen (F) and stop (issue #420).

## Shipped
- The play button in the stage's toolbar opens Present and Present with speaker notes.
- `components/slides/SlidePresenter.tsx` plays the deck over the panel, black around the slide.
  - **Next**: a click on the slide, →, ↓, Page Down, Space or Enter.
  - **Previous**: ←, ↑, Page Up or Backspace.
  - **Ends**: Home and End.
  - **Full screen**: F.
  - **Stop**: Escape. Leaving the panel shows the slide that presenting reached.
- Notes appear under the slide and can be shown or hidden while presenting.
- Each slide comes in with its own transition: Fade and Push as in PowerPoint. Magic move fades,
  as PowerPoint does where nothing matches. Reduced motion turns them off.

## Checked
- In Chromium against a live server, the six-slide Q3 deck: the menu, presenting with notes,
  next, and stopping back on the slide reached.

## Not verified
- Full screen inside the Electron app on Windows, and a second screen for the presenter view
  (the design's later step).
