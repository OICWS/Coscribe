# Docs routing measured on 12 briefs (shipped: measurement only)

Why: the Docs skill and the narrowed Word skill description (decision 0025, step 6) were meant to make
a written document a Doc by default and a `.docx` only when Word, a template or tracked changes is
named. This measures whether the model routes that way. Run off-peak (18:07 Beijing time).

## Shipped
- One run of `python -m evals.doc_route --jobs 3` on `main` at bc5c717 (DeepSeek, the repo's default
  reasoning effort, 12 briefs, one run each). Cost 0.10 USD in total, 1 to 12 model calls per brief.

| brief | expected | got | Docs skill loaded | valid Doc |
|---|---|---|---|---|
| 01 proposal | Doc | Doc | yes | no (see below) |
| 02 resume | Doc | Doc | yes | yes |
| 03 guide ("I will print it") | Doc | .docx | a skill was loaded | n/a |
| 04 report with chart | Doc | Doc | yes | yes |
| 05 letter | Doc | Doc | yes | yes |
| 06 minutes (Chinese) | Doc | Doc | yes | yes |
| 07 handbook | Doc | Doc | yes | yes |
| 08 Word named | .docx | .docx | yes | n/a |
| 09 template given | .docx | .docx | no | n/a |
| 10 tracked changes | .docx | .docx | no | n/a |
| 11 simple question | chat | chat | no | n/a |
| 12 short comparison | chat | chat | no | n/a |

Route right 11 of 12; a Doc where a Doc was expected 6 of 7; valid Docs 5 of 6 written.

## What the two misses are
- **03 guide:** the brief ends "I will print it for the office". The model wrote `Expense-App-User-Guide.docx`
  with `write_docx`, then spent 12 calls and two failed edits repairing it. Decision 0025 says wanting
  to print is not a reason for Word. The run does not record which skill's text it loaded, so whether it
  loaded Docs and ignored the line, or loaded the Word skill, is not known.
- **01 proposal:** routed correctly. It is marked invalid only because the check looks for the text
  "3 weeks" and the Doc says "three weeks"; the facts are right. This is the checker being literal, not the
  skill. Three `edit_file_batch` calls failed on the `---` separator rule before the model got it right.

## What it means
- One run per brief: 1 in 12 is within noise, so this is not evidence the wording is wrong. A second
  and third run of 03 and of two more "print" or "send" briefs would say whether "print" pulls the model
  to Word.
- If it does, the fix is a line in the Docs skill's description naming print and send, not a rewrite
  for these briefs. Not changed here.
- The harness should accept number words, and should record the name of the skill loaded.

## Not verified
- One run per brief; no repeat to separate the model's variance from the wording.
- Only DeepSeek was measured; another model may route differently.
- Whether the Docs tile, which asks for a Doc through the message, makes this stronger: the briefs are typed
  without the tile.

## Follow-ups
- Repeat 03 and two more print or send briefs three times each; fix the checker's number words and record
  the loaded skill's name in `evals/doc_route.py`.
