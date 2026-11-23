# Website: Coscribe with a capital C and the paper-plane logo

Why: the maintainer found the website messy; the name was written "coscribe" everywhere though
the product is Coscribe, and the logo was a generic document icon, not the app's paper plane.

## Shipped
- Every docs page in all nine languages, the frame's words (`site/_docs/i18n.toml`), the docs
  template and the promo page write the name as **Coscribe**. Code, paths, storage keys, the
  `coscribe:lang` event, repository URLs and heading anchors keep the lowercase spelling, so
  links into a section still work.
- `site/logo.svg`: the app's paper plane (`office-agent-desktop/icons/icon.svg` without its
  metadata), used as the favicon and the brand mark on the promo page and in the docs header.

## Not verified
- The Pages deploy itself: it runs only from `main`. Looked at in Chromium on Linux.

## Follow-ups
- More layout polish on the English pages with the maintainer, then the same in the other
  eight languages.
