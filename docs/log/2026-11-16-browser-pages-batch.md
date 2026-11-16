# The AI closes and reads several browser pages in one step (shipped, part 1 of #915)

Why: after a workflow's web automation the person had to close its pages one by one, and the AI
could only close or read one page per call. The maintainer asked for these abilities in both
conversations and saved workflows, planned once in #915.

## Shipped
- `browser_tabs("close", tab_ids=[...])` closes several pages, and `browser_tabs("close_all",
  keep=[...])` every page but the kept ones (ids, saved names or "current"). Pages the person used
  or took over, and pages another step is still working in, stay open; the result names each with
  its reason. An unknown page name closes nothing. Both run outside any one tab's queue
  (`browserAgentTabs.ts`).
- `browser_snapshot(tab_ids=[...])` reads several pages at once; each gets a share of the length
  (at least 2,000 characters), and a page that fails to answer is reported without hiding the rest.
- A workflow run's pages stay open after it ends, so the person can check them (the maintainer's
  choice). A workflow that should clean up ends with a `close_all` step; solidifying a conversation
  adds one only where the conversation closed its pages or the person asked. The step list says
  "Closes its browser pages", "Closes 2 pages", "Reads 3 pages at once".
- Tests: `scripts/browser-regression.cjs` covers closing by name, skipping the person's and a busy
  page, `keep: ["current"]` and an unknown name; pytest covers the tool output, a saved workflow
  that reads two pages and closes its own, and the argument checks; vitest the plain step words.

## Not verified
- A person using the Windows app; the scripts and tests ran under Linux.

## Follow-ups
- Parts 2 to 4 of #915 (forms and interaction, data out, resilience).
