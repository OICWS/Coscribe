# Word spec, step 4: a design system as the theme

Date: 2026-10-26
Area: tools

Step 4 of decision 0024. `design_system: <name>` in a spec's head takes the accent colour and the
font from that system of the person's library (decision 0020). The accent is the colour named
accent, primary or brand, else the first colour that is not near white; the font is the system's
first. Heading 1 and 2, the title, the table style, the cover, the cards and the contents title
take the accent (the components read it from Heading 1, so a theme sets it once); the Latin font
is the document default and the heading font. A font with Chinese glyphs or a CJK face in its
name sets the East Asian font too. A name that is not in the library is refused with the names
there are; a template with a design system is refused, as it has its own look.

Not done, on purpose: the system's text sizes. They are pixels on a 1920-wide slide, so a heading
of 144 px has no size in a page's points; the document keeps its own sizes and spacing. The note
(3.3) said text styles would become Heading 1 to 3; this is the part of it that carries over.

Not verified: a document on a real brand system opened in Word on Windows (a font the machine does
not have falls back there); the picking UI is not built.
