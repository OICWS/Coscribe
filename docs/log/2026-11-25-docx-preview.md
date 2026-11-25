# Read-only DOCX preview in the chat and Files

People can read the saved Word document alongside a conversation. The preview uses the existing
local Office conversion engines, so document layout is determined by the same installed engine as
a PDF export.

## Shipped

- DOCX attachments and Files use the same paginated reader with fit width, fixed zoom levels,
  selectable text, page navigation and access to the original.
- Opening a preview checks the conversation's readable folders, uses a temporary document
  copy, and caches a bounded number of rendered bytes by file version. An open preview checks
  for saves and reloads the new version. No PDF is written in the workspace.

## Verified

- Browser tests for the attachment preview and page controls. Server tests for scoped access,
  versioned caching, invalid inputs and preservation of the original.
- Chromium with real LibreOffice output, including Chinese text, repeated table headers,
  merged and nested cells, images, landscape sections and explicit page breaks.

## Not verified

- Windows Word and WPS rendering, including an original open in a Word window.
