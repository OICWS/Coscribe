#!/usr/bin/env bash
# Copies the app's built stylesheet and fonts into the demo and bundles the app's tool-call
# wording into labels.js. Run after `npm run build` in office-agent/frontend.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
demo="$here/.."
repo="$here/../../.."
static="$repo/office-agent/src/coscribe/web/static"
mkdir -p "$demo/fonts"
sed 's#url(/static/assets/#url(fonts/#g' "$static/style.css" > "$demo/app.css"
for f in figtree-latin-400-normal figtree-latin-500-normal figtree-latin-600-normal figtree-latin-700-normal \
         figtree-latin-400-italic figtree-latin-ext-400-normal figtree-latin-ext-500-normal \
         figtree-latin-ext-600-normal ibm-plex-mono-latin-400-normal ibm-plex-mono-latin-ext-400-normal; do
  cp "$static/assets/$f.woff2" "$demo/fonts/"
done
(cd "$repo/office-agent/frontend" && npx rolldown "$here/labels-entry.ts" --format iife --name CoscribeLabels \
  -o "$demo/labels.js" >/dev/null)
echo "app.css, fonts/ and labels.js written"
