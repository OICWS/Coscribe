# Dependabot stops proposing major versions

The first Dependabot scan after #263 opened 16 pull requests, several of them major jumps
(Electron 33 to 44, TypeScript 6 to 7, Node types 24 to 26, dotenv 16 to 18, five Actions
majors). A major upgrade needs a deliberate change and a test on Windows, so
`.github/dependabot.yml` now ignores `version-update:semver-major` in every ecosystem.
Minor and patch updates stay grouped, and security updates are not affected by `ignore`
(they need Dependabot security updates switched on in the repository settings).

Major upgrades of Electron in particular are done by hand, because old majors stop receiving
security fixes.
