# PowerPoint: the user's use sets the density, and decks may draw illustrations (shipped)

Why: the maintainer looked at the first theme round's decks (tasks 13 and 14) in PowerPoint. The
pages were dense, but how much text a page holds is the user's choice, not the style's: a deck
someone presents carries one point a page and the speaker says the rest; a deck people read on
their own is written like a document. The decks had no pictures either; the maintainer decided
against an image-generation backend (#259, closed) and for pictures drawn as SVG, as Claude
draws them.

## Shipped
- The design spec starts with **Use**: `talk` or `read`, taken from the request ("汇报", "听众"
  → talk; "发给", "读者" → read), or one question when the request does not say; a deck made
  with no one to ask is read. Talk: one point a page, body 24-28 px, the rest in the speaker
  notes (a talk deck gets notes without being asked). Read: full statements and tables, body
  18-22 px.
- A section "Illustrations": a cover or section picture drawn flat in SVG from the palette, at
  most about 40 shapes, which the build keeps as editable shapes.

## Checked
- Which SVG features carry over, by compiling a test page: curves, linear and radial gradients,
  opacity, dashes, rotation, a drop shadow and a glow do (the last three looked at in PowerPoint
  by the maintainer); a mask is an error and a pattern fill turns solid, and the skill says so.
- Round 2 (tasks 13 and 14): task 13 chose read from "读者", task 14 chose talk from the
  speaker notes it was asked for, but still wrote read-size pages (body 20 px, the English line
  15 px). Task 14 drew a globe with a trade route on its cover, which the maintainer liked.

## Tried and dropped: a check that a talk page is not full
Two runs of task 14 (about 0.6-0.8 yuan each) with a build check counting a page's text
(title aside; a Chinese character one, three Latin letters or digits one):
- As a warning on the first build, at 90 characters: the deck stayed as full (10 of 16 pages
  over) at the same cost.
- As an error, at 120 characters of text 15 px and larger: the counted text fell, but the model
  shrank the rest under 15 px (that text doubled, to 138-368 a page), so the pages got harder to
  read, and the run cost about 0.15 yuan more.
Counting all text does not help either: every deck for this task, ppt-master's included, has
126-499 a page, because the brief asks for two languages, a source on every figure and the
scope of each; an error there would make the model rewrite nearly every page, at about double
the cost and the user's wait. The maintainer decided against it: the cost in money and waiting
is not worth it. The talk-or-read rule stays in the skill; whether a model follows it is
something to look at again with a model that does.

## Not verified
- Talk density with a brief that does not ask for sources and two languages on every page.
