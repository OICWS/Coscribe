# 0062: Auto mode reviews commands, a card can allow similar calls, and Bypass mode asks for nothing

Status: proposed (2026-11-27, issue #1106 blocks 2 and 3; Collins agreed the design in the
project thread).
Narrows 0022: a command it sends to the person in every mode goes to Auto mode's reviewer in
Auto mode and runs without asking in Bypass mode.

## Context
The goal Collins set: as few asks as safety allows, rather than handing every risk to the
person, and an option to skip them all. 0022 sends every command without the elevated
sandbox, and every sandboxed command with network, to the person in every mode, so an Auto
task that runs `git` or `npm` raised a card per command. The person also had no way to say
"yes, and the same again" short of switching modes.

## Decision
- **Auto mode sends those commands to its reviewer**, told where the command runs (outside
  any sandbox, or in it with network) so it can weigh that. A reviewer with no answer, or a
  run of three blocks, still puts the command to the person. Outside Auto mode 0022 holds.
- **A card can allow similar calls for the rest of the conversation**: a command line by its
  program (`git`, `npm`; not one chained with `&&`, `|` or `;`), any other tool by its name.
  The allowance lives in the session only and is audited as `allowed_similar`. The code
  module's actions keep their own "allow for this task".
- **Bypass mode** asks for nothing. It is a fifth mode of the pill, offered only while
  Settings › General's "Allow bypass permissions mode" is on (off by default, read live:
  turning it off ends Bypass at once). Every gated call is approved and audited as `bypass`.
- **A scheduled task's tiers follow the same two modes.** "Automatically approve" (`auto`)
  still lets a local edit through, and hands what it used to park (code, connectors, a command
  0022 keeps from the person) to the reviewer: a prompt run's prompt is the person's request in
  its thread, and a high or full agent step is weighed against its title and goal as saved,
  never as rendered with values earlier steps brought in. An allow runs the call (`auto_review`),
  a block is refused to the agent (`auto_review_block`). A reviewer with no answer parks an
  agent step for a person; a prompt run, which can't park a call it has started deciding,
  refuses it and records why (`unattended`). "Never ask" (`skip`) is Bypass mode's equal and
  holds only while the same setting is on; otherwise the task runs as `auto` (`ScheduledTrigger.tier`), so
  turning the setting off holds every saved task to the reviewer. A bounded step, an approval
  or ask step, and a heal's guard keep asking a person.
- **The floor every mode keeps**: hooks, an exec policy rule that forbids, the workspace's
  `deny` and `ask` rules (the person wrote those), a switched-off capability, Stop, the audit
  log, and the sandbox, which still confines what a script or command can reach.

## Consequences
- In Auto and Bypass mode a command without the sandbox runs as the person after a model's
  check or none; the setting's text says so. 0002 holds: approvals are not a sandbox.
- A scheduled run keeps its task's approval tier; the conversation's mode never reaches it.
- A task saved as "Never ask" before this decision now runs as "Automatically approve" until the
  person turns the setting on.

Retired wording: "the Auto reviewer is never asked, and an unattended run refuses it", "but pause before running code or using connectors"
