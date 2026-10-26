# Word spec, step 1: the head and the components

Date: 2026-10-26
Area: tools

Step 1 of decision 0024. `write_docx` reads its `content` as a spec: an optional YAML head
(`title`, `subtitle`, `author`, `date`, `cover`, `toc`, `header`, `footer`, `facts`) and `:::`
components (`stats`, `callout`, `figure`, `pagebreak`), with the markdown subset between them
written as before. A head key that sets a look (colour, font) is refused, `{fact:name}` is
expanded from the head's `facts` and an undefined one is an error, and a component the compiler
cannot write is refused with what to change. A content with no head and no component is plain
markdown and takes the old path untouched.

The compiler writes a cover (colour band, title, rule, subtitle, author, date), a contents page, a
header and footer (the cover has none), a row of two to four cards, a call-out (info, success, warn,
danger), and a picture with its caption, onto the house style, each as the OOXML a person would
build and with a `cs_<component>` bookmark for the editor to find later. Components are final
content, not tracked changes (a tracked write with a component is refused).

Nothing tells the model about the grammar yet: the Word skill and the tool description change in
step 5, after the gate. Next: the chart component, the checker.

Not verified: the output in real Word on Windows (checked in LibreOffice and the schema); the
look of the cover and cards with East Asian fonts in Word.
