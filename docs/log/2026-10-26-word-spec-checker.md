# Word spec, step 3: the checker

Date: 2026-10-26
Area: tools

Step 3 of decision 0024. A document written from a spec is checked without a model, and the
findings come back in the `write_docx` result as `check`, each with a `code`, a `where` and the
`fix` that clears it. The file is still written: the author repairs the spec and writes again.

The spec is checked for a heading that skips a level, a fact defined and never used, an empty
call-out, an untitled chart, a document with no title and a contents list with no headings. The
saved document is read back: every component in the spec is in it, once, in order (the cover comes
from the head), none is one the compiler does not know, and each chart draws the numbers of its
table. Plain markdown is not checked, as before.

Not verified: that a repair pass after a finding converges on a real model run (step 5's tasks
measure that), and the check on a document opened in real Word on Windows.
