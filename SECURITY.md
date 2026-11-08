# Security

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's **Report a vulnerability**
button on the repository's Security tab (private vulnerability reporting), or,
if it is not available, contact the maintainer [@OICWS](https://github.com/OICWS)
through their GitHub profile. Say what you found, how to reproduce it and what
it affects. You will get an answer as soon as the maintainer can give one.

## What the project does and does not promise

coscribe runs on your own computer.

- **Scripts run in a Windows sandbox, where it works** (decisions 0021, 0022). Python and
  Node scripts the assistant writes run in an AppContainer that reaches only the conversation's
  own folders (read-write folders without delete) and the interpreter. A self-test on each machine
  decides whether it is used; where it fails, scripts are off unless you let a conversation run
  them without isolation, a choice that is recorded. Command lines run in Codex's Windows sandbox
  where Settings set it up: they write only the conversation's read-write folders, have network
  only when the conversation's environment allows it, and your private folders are hidden by
  default. Elsewhere a command runs as you, and only after you allowed that and approve each one.
- **What the sandbox does not cover.** Off Windows, and in a conversation let out of isolation,
  code runs as you and can read any file you can and use the network. coscribe's own process and
  its built-in tools (file tools, Office, the web tools) run as you and keep to the folder
  settings themselves. A script you approve can do anything inside the folders it was given, and
  prompt injection is not removed: the approval prompts and permission modes stay, and the aim is
  the least access plus your approval.
- **Secrets** (provider keys, connector tokens, the global secrets): values go
  to the operating system's keychain where there is one. The promise is that
  the *model* cannot see a value in its tool output, the transcript, approval
  cards or logs. It is **not** a promise against code that goes digging, since
  such code runs as you and could read the keychain itself. Redaction of
  responses covers common encodings only, and a host you allow a secret to be
  sent to could echo it back.
- **Connectors** sign in through the service's own page in your browser; their
  tokens are kept in the keychain (or a 0600 file when there is none).
- **A task that starts on something new in a connector** (decision 0039) asks that connector by
  itself every few minutes, with no one watching. It asks only a tool the connector marks
  read-only, or one you confirmed in the task form, and never one blocked in Settings; each check
  that found something is in the audit log. What comes back is outside content, and the runs it
  starts keep the task's permissions and autonomy.
- **A task that starts on an event a program sends** (decision 0040) has a listener of its own on
  127.0.0.1 (port 8790 by default), on only while such a task is on. A program must send the
  task's key, a random 32-byte value kept in the keychain and checked by its hash; a request from
  a web page (with an `Origin` header) is refused. Events are limited per task (3 runs at once, 30
  an hour), each is in the audit log by size and outcome, and the event is outside content: the
  run keeps the task's permissions and autonomy. While no such task is on, the port is free, and
  another program on the machine could take it and read the keys senders send to it.
- **Skills and connectors from elsewhere** run with the access you give them;
  read what you add.

## Supported versions

Only the latest `main` is maintained.
