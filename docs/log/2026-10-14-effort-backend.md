# Reasoning effort, part 1: one six-level scale, mapped to each model, set per conversation (shipped; no UI yet)

Why: the model's reasoning output is most of what a turn costs (96% on generated decks), and at
`low` decks were judged level with `high` for up to 35% less. The maintainer asked for a control
next to the model, the same for every provider (#202).

## Shipped
- `runtime_lg/effort.py`: the levels Low, Medium, High, Extra, Max, Ultra. A chosen level runs as
  the nearest level the model supports at or below it: above the top it runs as the top, in a gap
  as the cheaper level below, and below the bottom as the model's lowest. Ultra runs as each
  model's highest today. Levels per model:
  - Claude: from langchain-anthropic's model profile (Opus 5.5: low to max with xhigh; Sonnet
    4.6: no xhigh); sent as `output_config.effort`.
  - DeepSeek: low, medium, high, xhigh, max; sent as `reasoning_effort`.
  - OpenAI's own endpoint, o-series and GPT-5/6: low, medium, high; `reasoning_effort`.
  - Gemini 2.5 and later: low, medium, high (3 Pro preview: low, high); `thinking_level`.
  - Anything else (an OpenAI-compatible provider other than DeepSeek, older models): nothing is
    sent, because an unknown field can be refused.
- `Settings.default_effort` (Medium). The level is set with the model: `switch_model` takes an
  optional `effort` (unchanged model, new level, to change only the level), rebuilds the model and
  graph, and a failure leaves both as they were. `runtime_lg.for_conversation` applies a
  conversation's effort and prompt-cache key to a model. The `state` event carries `effort` and
  `effort_runs_as` (`wire.py`, generated TypeScript). No new socket message, so `ws.py` changes
  one line, and `session.py` ends 16 lines shorter: `switch_model`'s docstring lost its history.
- Tests: `tests/test_effort.py` (22: the mapping table, each model's levels, the request field the
  real chat model classes send) and a socket test of a level change in `tests/web/test_chat.py`.

## Checked live (2026-10-14)
- Claude, OpenAI and Gemini parameters from their documentation pages.
- DeepSeek documents no values. Asked with an unknown one, its API lists `none, minimal, low,
  medium, high, xhigh, ultra, max`. On one hard counting question all five of medium, high,
  xhigh, max and ultra answered right, using 19k, 20k, 30k, 26k and 24k reasoning tokens. One
  sample cannot order them, so `ultra` is not used and Ultra runs as `max`. That probe cost about
  0.5 to 1 yuan, more than planned.

## Not verified
- Windows; a real Claude, OpenAI or Gemini request (no keys here); only the payloads are tested.
- Whether DeepSeek's `medium` and `xhigh` differ from `high` on real tasks (one sample only).

## Follow-ups
- #202 part 2: the pill and slider in the UI; part 3: the evaluation's `--effort` through the same
  mapping.
