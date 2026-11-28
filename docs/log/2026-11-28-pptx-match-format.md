# Shapes made to look like another one, as Format Painter does (shipped)

Why: OfficeVal dev task 069 asks for boxes and their text to match the size and format of
another box. The agent did it with python-pptx scripts that rewrote more than it meant to
(other boxes lost their fill and border), and scored 0 to 0.3.

## Shipped
- `match_pptx_shape_format` (`tools/office/pptx/format_match.py`): copies the named parts
  (size, outline shape, fill, border, text format) from one shape onto others; each target keeps
  its text and position, and nothing else on the slide changes. The theme style comes along with
  fill and border so a theme-styled box does not turn plain.
- `list_pptx_shapes` and the PPTX Editing skill name it; a search recall case finds it.
- Applied by hand with the task's mapping, 069 grades 53 of 53 checks.

## Not verified
- With the agent (`deepseek-flash`, six runs of 069): the one run that called the tool scored
  0.55; the five that wrote scripts scored 0 to 0.26. Reading which box maps to which in the
  picture also goes wrong in that best run. 070 scored 0.52 and 0.81.
- Not tried on a real Windows PowerPoint; the result was checked with python-pptx and the grader.

## Follow-ups
- Get the agent to reach for the tool rather than a script on a Chinese request like 069's.
