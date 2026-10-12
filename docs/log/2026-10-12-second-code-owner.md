# kurtosisOC is a second code owner of the invariant paths (partly shipped)

Why: Decision 0007 says a second owner is added on each `CODEOWNERS` line when the second maintainer joins (issue #80).

## Shipped
- `.github/CODEOWNERS`: all 15 path lines end in `@OICWS @kurtosisOC`; the comment block now says both owners are listed.
- `docs/plan.md` item 2 says what is done and what is left.

## Not verified
- That GitHub accepts the owner as valid: it only does so once `kurtosisOC` has write access to the repository, which an admin controls. The "Codeowners errors" view in the repository shows any problem.

## Follow-ups
- An admin turns on "require code owner review" in the ruleset; until then the file is advisory.
