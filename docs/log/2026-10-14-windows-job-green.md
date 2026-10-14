# The two Windows-only test failures on main are fixed (shipped)

Why: the nightly Windows job failed the same two tests on `main` (#210), and its 14-day green clock cannot start until it passes.

## Shipped
- `tests/test_file_sizes.py` measures the size of the blob git stores (`git ls-files -s` plus `git cat-file --batch-check`), not the working-tree file, so CRLF conversion on a Windows checkout no longer pushes `_native_svg/.../elements.py` over 200 KB.
- `tests/pptx_canonical.py` writes a PNG part as its decoded size and mode (`<png 64x64 RGBA>`), not a hash of its bytes, because a rasterised icon differs per platform's fonts and PNG encoder. Eight pptx goldens and the docx image golden changed on that one line each.
- Checked by breaking: a 250 KB tracked text file fails the size test; the icon golden still pins width, height and mode.

## Not verified
- A real Windows run. The Windows job in CI is the check.

## Follow-ups
- The Windows job needs 14 green days in a row before it becomes a required check (decision 0009).
