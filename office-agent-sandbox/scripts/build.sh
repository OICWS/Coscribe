#!/usr/bin/env bash
# Builds coscribe-sandbox.exe with the two helpers Codex's sandbox launches beside it, inside a
# checkout of openai/codex at CODEX_TAG: the crate joins Codex's workspace, so its dependencies
# are the versions Codex's own Cargo.lock pins. Windows only (MSVC). Usage: build.sh OUT_DIR
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
out="$(mkdir -p "$1" && cd "$1" && pwd)"
tag="$(tr -d '[:space:]' < "$here/CODEX_TAG")"
work="${CODEX_CHECKOUT:-$here/target/codex-$tag}"

if [ ! -d "$work/codex-rs" ]; then
  # Codex has test snapshots past Windows' 260-character limit.
  git -c core.longpaths=true clone --quiet --depth 1 --branch "$tag" https://github.com/openai/codex "$work"
fi
rs="$work/codex-rs"
rm -rf "$rs/coscribe-sandbox"
mkdir -p "$rs/coscribe-sandbox"
cp -R "$here/Cargo.toml" "$here/src" "$rs/coscribe-sandbox/"
if ! grep -q '"coscribe-sandbox"' "$rs/Cargo.toml"; then
  # The first line of the members list; the rest of Codex's Cargo.toml stays as it is.
  sed -i 's/^members = \[$/members = [\n    "coscribe-sandbox",/' "$rs/Cargo.toml"
fi
(cd "$rs" && cargo build --release -p coscribe-sandbox \
  && cargo build --release -p codex-windows-sandbox \
    --bin codex-windows-sandbox-setup --bin codex-command-runner)
for exe in coscribe-sandbox codex-windows-sandbox-setup codex-command-runner; do
  cp "$rs/target/release/$exe.exe" "$out/"
done
printf '%s\n' "$tag" > "$out/CODEX_TAG"
# Apache-2.0 asks for the licence and notices to travel with the binaries.
cp "$work/LICENSE" "$out/LICENSE-codex.txt"
if [ -f "$work/NOTICE" ]; then cp "$work/NOTICE" "$out/NOTICE-codex.txt"; fi
