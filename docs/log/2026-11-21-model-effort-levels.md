# Each model's own effort levels, from the bundled catalog (shipped)

Why: part 3 of decision 0055. Every model was offered one six-level scale (Low to Ultra), so a
model's own levels and names were hidden, and Ultra matched no provider's level.

## Shipped
- `runtime_lg/effort.py`: a model's levels come from the bundled catalog first
  (`catalog_levels`, by provider name or base URL host; `none`, `minimal` and the like are left
  out), then from the library's or the provider's documented ones as before. `for_conversation`
  returns the levels with the level a choice runs as; the state event carries them
  (`effort_levels`).
- The effort picker offers the model's own levels with its names (xhigh as Extra high), and the
  animated field marks its highest level, whatever it is called. A model whose levels are not known
  keeps the six-level scale, and one with no effort setting shows it greyed out as before.
- The choice is still kept on the six-level scale, so it carries over a model switch: Max on
  Claude Opus 5.5 stays Max on DeepSeek V4 Flash.
- Behaviour change: DeepSeek's models run the catalog's levels (low, high, max for V4 Flash), so
  Extra now runs as high, not xhigh; an OpenAI-compatible provider whose models the catalog lists
  with levels now gets an effort setting where it had none.

## Not verified
- Each provider accepting the catalog's levels with a real key: models.dev lists them, nothing here
  sent them. A wrong row is corrected in `runtime/models/overrides.json`.
- The picker in the desktop app on Windows: checked in Chromium against a local server.

## Follow-ups
- The protocols, and pasting a vendor's Codex or Claude Code setup (decision 0055).
