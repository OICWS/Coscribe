# Full-screen slideshow gives the slide the whole screen (shipped)

Why: presented full screen, the Slides panel kept the control bar in its own strip under the
slide, so the slide was scaled down and black space was left around it (#1108).

## Shipped
- `SlidePresenter`: in full screen the bar floats over the bottom of the slide instead of taking a
  strip of its own. It is hidden until the pointer comes within 96 px of the bottom, and stays up
  while one of its buttons has the keyboard focus (Tab), not after a mouse click. Out of full
  screen nothing changed.
- e2e (`slides-stage.spec.ts`): at 1600×800 the slide is 800 px tall in full screen, the bar
  shows near the bottom and hides away from it, its buttons work, and Tab brings it back.
- [Before](screenshots/fullscreen-slideshow-before-idle.png),
  [after](screenshots/fullscreen-slideshow-after-idle.png),
  [after, pointer at the bottom](screenshots/fullscreen-slideshow-after-pointer-bottom.png).

## Not verified
- The desktop app on Windows (Electron's full screen); checked in headless Chromium only.

## Follow-ups
- None.
