# Does the AI make a Doc when an explanation is worth keeping? (measured)

Why: decision 0027 leaves it to the AI when a Doc is the right way to explain something. The route
measurement (`evals/doc_route.py`) had no brief that only asks to be explained.

## Added
Three briefs: a step-by-step explanation to understand (expected: chat), an offsite budget "in a form I can send
to the team" (expected: a Doc) and a loan walk-through "I want to keep it and come back to it" (a Doc).

## Result (DeepSeek, effort low, 2026-10-28, off-peak, one run each)
All three right: the plain explanation stayed in chat with no file; the two that named a use afterwards
(send, keep) became valid Docs with their figures (12,000 / 20; 300,000 / 25). Cost 0.03 USD. With the
twelve earlier briefs: 12/12 routes right in the full run the same evening, seven valid Docs.

One run each says little about the margin: a brief that only hints ("it would help to have this written
down") is not measured, and the skill's own default (chat unless a use afterwards is named) is what is
being tested. Not changed.
