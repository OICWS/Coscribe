# 0022: Commands run in Codex's Windows sandbox

Status: proposed (2026-10-24, issue #588, step 4); accepted once the maintainer's independent
review passes. Changes 0021 for commands: 0021 kept command lines out of the AppContainer and
let them run as the user.

## Context
`run_background_command` runs a cmd line. cmd can't list folders inside the AppContainer, so
0021 left commands running as the user, able to change any file. On a Windows runner,
`codex sandbox --permission-profile` in elevated mode holds a cmd line to the folders a profile
names for writing: it runs as a local sandbox user that writes only those folders and has no
network unless the profile allows it. Reading is wider: elevated mode needs the whole disk
readable (`":root" = "read"`), and setup gives the sandbox users read access to every folder of
the person's profile, Documents, Desktop, Downloads and AppData among them (checked with icacls
on the runner); only the files at the top of the profile stayed closed, among them
`.git-credentials`, `.netrc` and `.npmrc`. It needs `codex sandbox setup --elevated` once, which an
administrator approves.

## Decision
- Settings › Capabilities sets the sandbox up (downloading Codex if needed) and removes it
  (`codex sandbox uninstall`); both are audited. The sandbox has its own `CODEX_HOME`, apart from
  the code module's and the person's.
- Where it is set up, a command runs as `codex sandbox --permission-profile <p> -C <folder> --
  cmd /d /c <file>.cmd`, the line written to a UTF-8 batch file (Codex quotes arguments in a way
  cmd can't read). Profile `<p>` writes the conversation's read-write folders, reads its
  read-only ones, and has network only when the environment's network is Full; one profile per
  set of folders, named after them.
- Settings › Capabilities hides the person's private folders from it, on by default (#601):
  Documents, Desktop, Downloads, Pictures, Videos, Music, OneDrive, AppData and the profile's
  credential folders (`.ssh`, `.aws`, `.azure`, `.kube`, `.docker`, `.gnupg`). Each is a `"deny"`
  entry in the profile, so Codex puts the deny-read entry on it and keeps it there (Codex resets
  the profile's own folders at each run, so an entry coscribe added itself would not hold). The
  entries name the sandbox's group, which the person is not in (checked on the runner). A folder
  the environment was given is never denied, and a deny Codex left on it earlier is taken off.
  A private folder that holds the command's own folder is not denied whole: PowerShell can't
  start in a folder whose parents its user can't list and falls back to `C:\`. Instead every
  file and folder beside the way down to the command's folder is denied (the maintainer's
  choice), and a deny Codex left on a folder on that way is taken off.
  Codex grants the folders a command writes, but not those it only reads, so coscribe grants its
  users read on each read-only folder, the batch files and the PATH folders that lie inside a
  denied one; a grant that fails stops the command and says why. A command gets its own Temp in
  the state folder, since the person's is in AppData.
- A ledger in the state folder lists every folder denied or granted, written whole before each
  change. Turning the setting off, or removing the sandbox (also when its Codex is gone), takes
  them all away, checks with icacls that no deny is left, and reports the folders it couldn't
  clear, which stay in the ledger for the next try; the sandbox is not uninstalled while any are
  left, since its group's name is what clears them. Codex leaves some of its own deny entries
  behind when they leave the profile, which is why coscribe keeps this ledger.
- Because the sandbox still reads other drives and Windows' own folders, a sandboxed command whose environment's
  network is Full is approved by the person, as an unsandboxed one is: reading plus network
  could send those files out. Offline, it follows the conversation's approval mode.
- Where it isn't (not set up, or not Windows), turning commands on is not enough: the person
  also confirms "Run commands without the sandbox". Then a command runs as the user and every
  one is approved by the person in every mode (pre-approved, Accept Edits, Auto, a scheduled
  run that skips approval); the Auto reviewer is never asked, and an unattended run refuses it.
- Codex's setup and uninstall refuse to run unelevated and don't ask Windows themselves
  (`orchestrator_elevation_required`), so unless coscribe is elevated it starts them through
  RunAs, which shows the administrator prompt. Setup names the person (`--user`, with their
  `USERPROFILE`), since a standard user's prompt runs it as the administrator who approved it.
- Without an administrator, the person can pick the unelevated mode instead (Codex's
  `[windows] sandbox = "unelevated"`): no setup, the person's own restricted token. It still
  writes only the given folders, but it can't deny a read (so private folders are not hidden)
  and is offline only by its environment, so every command in it is approved by the person, as
  an unsandboxed one is. Setting it up runs a test command, the only proof it works.
- The desktop app carries the sandbox itself (issue #607): `coscribe-sandbox.exe`, a small
  program built from Codex's sandbox crate (`codex-windows-sandbox`, Apache-2.0) at the tag in
  `office-agent-sandbox/CODEX_TAG`, inside Codex's own workspace so its Cargo.lock pins every
  dependency, with the two helpers that crate launches. It does what `codex sandbox`, `sandbox
  setup` and `sandbox uninstall` do, with the profile given as a JSON file instead of Codex's
  config. The server finds it through `COSCRIBE_SANDBOX_DIR`, which the desktop app sets; without
  it (a source checkout, an older build) setting up downloads Codex as before. The tag moves only
  when a sandbox fix is wanted, and then the Windows checks run against the new build.
- Scripts stay in the AppContainer (0021).

## Consequences
- Reads are held only for the private folders: other drives, `C:\Users\Public`, ProgramData and
  Windows' own folders stay readable, and Codex refuses a deny on a drive's root. The setting
  says so. Turned off, the sandbox reads most of the person's files again.
- The deny and grant entries are on the person's own folders. A grant runs icacls over the
  folder's tree once, off the event loop, which takes a while on a big one; it is not repeated.
- A grant is to the sandbox's group, not to one environment: once a folder is granted, every
  sandboxed command can read it, until the setting is turned off. Giving an environment a folder
  that holds private ones (the whole profile) un-hides those for its commands.
- With the command's folder inside a private one (a project on the Desktop), the names of what
  lies beside the way down can be listed, though not opened; what is added there later is hidden
  from the next command on. A junction or link there is not denied, since a deny on it may not
  reach what it points to.
- APPDATA, LOCALAPPDATA and USERPROFILE still point at hidden folders, so a tool's own cache or
  settings there (pip, npm, git) can't be read; the command fails rather than reads them.
- Another private place (a folder elsewhere, a dot-folder not listed) stays readable.
- "Ready" means the setup's Codex is still where it was recorded. A Codex upgrade installs to a
  new folder, so the old record stops counting; a sandbox removed outside the app makes the
  command fail rather than run as the person (a real-Windows check).
- The command gets the server's environment variables, as scripts do; coscribe keeps provider
  keys in the Credential Manager, not there.
- An offline sandboxed command in Auto or a run that skips approval still reads what is not
  hidden (or everything, with the setting off) and can copy what it reads into a writable folder, where another tool could send it on; the
  approvals of those tools are what stand in the way.
- A command approved without the person because the sandbox was set up is refused if the
  sandbox is gone when it starts, rather than run as the person.
- An unattended run in manual mode leaves an unsandboxed command waiting for the person, as it
  does every gated call; a run that resolves approvals itself refuses it.
- A limited network list can't be held by the sandbox, so a command is offline unless the
  network is Full.
- The elevated mode needs an administrator once per machine; a standard user without one has
  the unelevated mode, or the unsandboxed path, each with the person's approval of every command.
- Codex's own commands in the code module are still off; running them in this sandbox is the
  next step (4b).
