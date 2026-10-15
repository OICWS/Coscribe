"""The OOXML namespace URIs the hand-built slide XML uses."""

from __future__ import annotations

# The presentationml namespace every <p:...> element in a slide part lives
# in, and the PowerPoint-2010 extension namespace real PowerPoint uses for
# the transition duration attribute (`p14:dur`, milliseconds) -- the base
# ECMA-376 schema only has the three-value `spd` attribute (fast/med/slow),
# `p14:dur` is the real-world attribute PowerPoint itself writes for
# precise timing, confirmed by inspecting real .pptx files' XML.
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
# Markup Compatibility and Extensibility (ECMA-376 Part 3) -- the mechanism
# that makes a foreign-namespace attribute like `p14:dur` below valid OOXML
# at all: a producer declares the namespace prefix "ignorable" via
# `mc:Ignorable` on an ancestor, and a schema-strict consumer is specified
# to strip that content before validating rather than reject it outright.
# Confirmed live against `_ooxml_schemas/`: `CT_SlideTransition`/`CT_Slide`
# have no `xsd:anyAttribute` wildcard, so `p14:dur` genuinely doesn't
# validate against the bare ECMA-376 schema without this declaration --
# `_ooxml_validate.py` implements the matching strip-before-validate side.
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

# add_pptx_formula's own pair: the PowerPoint-2010 DrawingML extension
# namespace real PowerPoint uses to embed a native Office Math equation
# inside a text paragraph (`<a14:m>`, wrapping `<m:oMathPara>`/`<m:oMath>`),
# and Office Math's own namespace -- confirmed against
# hugohe3/ppt-master's own documented contract (`references/native-
# formula.md`: "Export replaces the whole group with a14:m > m:oMathPara >
# m:oMath"), not guessed. Same foreign-namespace-extension-content shape as
# `p14:dur` above -- `<a:p>`'s base ECMA-376 content model has no slot for
# either `a14:m` or `m:oMath`, so this needs the exact same `mc:Ignorable`
# treatment (`mark_mce_ignorable`/`_ooxml_validate.py`'s strip-before-
# validate side), reused unmodified rather than duplicated.
A14_NS = "http://schemas.microsoft.com/office/drawing/2010/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
# DrawingML's base namespace -- add_pptx_audio's own <a:audioFile>/
# <a:blip>/<a:xfrm> below, none of which needed a dedicated constant
# until now (every earlier hand-XML feature only ever needed the "p"/
# "p14"/"a14"/"m" namespaces above).
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# The relationships namespace every r:id/r:embed/r:link attribute lives
# in, regardless of which element or local attribute name carries it --
# used by duplicate_slide_part to blanket-remap every such attribute in
# one pass rather than enumerating every possible tag (a:blip r:embed,
# a:hlinkClick r:id, c:chart r:id, a:videoFile r:link, ...).
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# PowerPoint 2012/2015 extension namespaces -- set_pptx_transition's own
# pair beyond P14_NS above, needed for the newer transition effects below
# (Morph is p159; the 2013 "Exciting"-category ones -- Fracture, Crush,
# Airplane, Origami, etc. -- are p15). Same foreign-namespace-extension
# reasoning as P14_NS/A14_NS: real PowerPoint XML for these effects,
# confirmed against hugohe3/ppt-master's own reverse-engineered registry
# (`pptx_transitions.py`), not guessed.
P15_NS = "http://schemas.microsoft.com/office/powerpoint/2012/main"
P159_NS = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
