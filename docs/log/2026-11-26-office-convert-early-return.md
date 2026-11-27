# An Office conversion returns once the file is saved (shipped)

Why: a Word preview of a one-paragraph document took about 5 s, and only 0.3 s of it was Word
opening and exporting the file.

## Shipped
- The conversion script prints a marker once the file is written and closed; `_office_com.convert`
  returns then, and the program quits in the background. The next conversion waits for it, under
  the same lock and time limit, so two jobs never share one instance.
- Measured on Windows with Word 16: a first DOCX-to-PDF conversion 2.5 s instead of 4.9-6.0 s.
  Back-to-back conversions take as long as before, since each waits for the previous exit.

## Not verified
- WPS Office.
