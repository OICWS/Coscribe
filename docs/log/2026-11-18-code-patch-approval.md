# Patch approval when the model offers only exec_command (shipped)

Why: a code task submitted `apply_patch "<multiline patch>"`. Codex did not recognize that shell
form as a native patch, so Coscribe refused an ordinary command before any file-change card.
The resulting "rejected by user" was an automatic refusal, not a user clicking Deny.

## Shipped
- The code module's commands-off instructions specify the native-recognized heredoc form for
  models without a standalone patch tool, and prohibit the quoted-string/PowerShell/pipeline
  forms that fall through to command execution. No command permission or approval policy changes.
- Resumed code threads receive current developer instructions too, so existing conversations
  pick up corrected patch guidance rather than retaining only their original instructions.
- Windows native checks exercise the pinned real Codex with a local stub Responses API and an
  unknown model exposing exec_command only: the quoted control has no approval and cannot write;
  a recognized patch reaches file-change approval, with Deny preserving the file and Allow editing.
- The Windows check runs when these instructions change. Manual check #844 distinguishes an
  automatic command refusal from file approval, first download from cached launch, and the
  ten-minute service idle timeout from an empty background-task list.

## Not verified
- A real Windows desktop locally and whether the user's particular model follows the corrected
  instruction. The pinned executable and all three native test cases passed locally on Linux;
  the same native checks run on Windows in CI, without a real provider key.

## Follow-ups
- The remaining first-use, real-model and idle-service checks in #844.
