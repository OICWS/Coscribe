# The built-in sandbox ships OpenAI's signed helpers, which Windows Defender doesn't flag (shipped)

Why: on the maintainer's machine Windows Defender quarantined the built-in sandbox's
`codex-windows-sandbox-setup.exe` as `Trojan:Win32/Bearfoos.A!ml` right after setup. That helper
creates local users and changes folder permissions, and the copy coscribe built (#615) carried no
signature. The same helper in the Codex wheel is signed by OpenAI.

## Shipped
- `office-agent-sandbox/scripts/build.sh` builds only `coscribe-sandbox.exe`. The two helpers come
  from the pinned Codex wheel (`signed_helpers.py`), checked against the wheel's and each
  member's sha256 in `code_runtime/_pins.py`. This also leaves less to compile.

## Not verified
- Whether Defender also flags `coscribe-sandbox.exe`, which is still built here and unsigned. If it
  does, the next step is signing it.
