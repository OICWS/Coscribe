# Decision records

One short file per decision that a future session would otherwise reopen or
"fix" because it looks wrong. At most 40 lines: Context, Decision,
Consequences, Status. Name: `NNNN-slug.md`. A record is added in the PR that
makes the decision (or, for the first ones, writes down a decision that was
already made). A decision that changes gets a new record that supersedes the
old one; the old one stays, marked "Superseded by".

| # | Decision |
|---|---|
| [0001](0001-fixed-cached-tool-list.md) | The agent's tool list is fixed; tools are deferred |
| [0002](0002-approvals-not-a-sandbox.md) | Approvals and risk tiers, not an OS sandbox |
| [0003](0003-secrets-promise.md) | Secrets: the model cannot see a value; nothing more is promised |
| [0004](0004-connectors-sign-in-once-in-the-browser.md) | Connectors sign in once, in the user's own browser |
| [0005](0005-code-is-a-second-runtime.md) | Code is a second runtime, never inside a fixed workflow |
| [0006](0006-changes-reach-main-through-pull-requests.md) | Changes reach `main` only through pull requests |
| [0007](0007-working-with-more-than-one-human.md) | Working with more than one human and their AI sessions |
| [0008](0008-conversations-can-message-each-other.md) | Conversations can message each other |
| [0009](0009-a-structure-period-then-growth-for-ai-sessions.md) | A structure period, so AI sessions can keep up with growth to 1M lines |
| [0010](0010-office-files-are-compiled-from-whole-page-sources.md) | Office files are compiled from whole-page sources; open-source code is reused as owned copies (proposed) |
| [0011](0011-workbooks-are-written-as-engine-neutral-blocks.md) | Workbooks are written as engine-neutral blocks; Excel engines come in stages |
| [0012](0012-the-product-does-not-depend-on-libreoffice.md) | The product does not depend on LibreOffice |
| [0013](0013-word-documents-gain-a-document-style-not-a-script-route.md) | Word documents gain a document style, not a script route |
| [0014](0014-office-files-are-shown-in-the-app-as-panels.md) | Office files are shown in the app as panels; changes to them go through the backend |
| [0015](0015-what-coscribe-makes-is-an-artifact.md) | What coscribe makes is an artifact; Slides are positioned HTML sections |
