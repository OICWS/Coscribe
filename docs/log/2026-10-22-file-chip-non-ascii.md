# A file named in Chinese is a working chip

Why: the maintainer's deck, named in Chinese, showed in the reply as a chip reading `AI%E6%96%B0...` and could not be opened.

## Shipped
- The markdown pipeline percent-encodes what is not ASCII in a link, so the chip got the file's address encoded and neither showed nor opened the name. `fileLinkPath` decodes it (a path that does not decode is left as it is).
- The chat-files spec runs with an ASCII name and a Chinese one, and checks the chip opens the file; without the fix the Chinese one fails.

## Not verified
- Not run on Windows or with a real model.
