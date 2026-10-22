# The Stop button is a ring with a dot

Why: while a reply is worked on, the Stop button was a black rounded square, heavy beside the context ring under it. The maintainer asked for a ring with a dot (his reference) at the context ring's size.

## Shipped
- `StopRingIcon`: a ring with a filled dot, 20 px like the context ring, no black tile; it takes the hover tint the Send button has. Only the composer's Stop uses it; the Stop buttons in the Background tasks panel and the workflow run keep the square.

## Not verified
- Not run on Windows or in the desktop shell; checked by screenshot in headless Chromium.
