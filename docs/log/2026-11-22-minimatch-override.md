# The desktop build tools use a minimatch without the glob-amplification bug (shipped)

Why: Dependabot alert 77 (GHSA-g3hv-75wg-m249, moderate): minimatch 7.0.0 to 11.0.0 can be made
to do quadratic work by a crafted pattern. electron-builder's `app-builder-lib` and
`@electron/universal` pulled 10.2.6 and 9.0.9. Only our own build patterns reach them, so it was
not exploitable, but the alert stayed open and electron-builder has no release that moves off it.

## Shipped
- `office-agent-desktop/package.json` overrides `minimatch@>=7.0.0 <11.0.1` to `^11.0.9`. The
  range keeps the 3.x and 5.x copies that `glob` 7, `dir-compare` and `filelist` need (their
  default-export API differs). `npm audit` reports 0 vulnerabilities.

## Not verified
- A full installer build: `desktop build (Windows)` is manual-only; it was run on the PR branch.

## Follow-ups
- Drop the override once electron-builder depends on minimatch 11.0.1 or later.
