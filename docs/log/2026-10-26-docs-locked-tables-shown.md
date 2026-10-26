# Locked Word tables and contents lines are shown in the editor

Date: 2026-10-26
Area: frontend, tools

A table the Docs editor cannot change (merged or shaded cells, such as KPI cards and call-out
boxes) was a grey line with its text run together. The reader now sends the cells (text, column
span, fill) and the editor draws them as a read-only table; the block is still kept as it is.
Lines of a contents field are shown as plain text without the grey label.

Not verified: a real Windows machine; charts and the cover's drawn bars are still grey
"Picture or drawing" lines (docx-preview in Review does not draw charts either).
