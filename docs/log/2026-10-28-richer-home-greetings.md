# Richer home greetings (shipped)

Why: the first greeting pool had plain lines such as "Hello" and "Hi there"; the
request was for something deeper and more crafted.

## Shipped
- `frontend/src/lib/greetings.ts`: pools rewritten with more evocative lines for
  morning, afternoon, evening, night, any time, Monday, Friday and weekends. Plain
  "Good morning/afternoon/evening" and "Hello, night owl" stay as anchors.
- `HomeGreeting` no longer adds a trailing "!", since lines carry their own punctuation.

## Not verified
- Not looked at in the running app or on Windows; only lint, build and the unit tests.

## Follow-ups
- None.
