"""Tool wrappers for raw XML, notes, transitions, animations and audio."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from .toolkit import PresentationToolkit


# The tools are grouped into builders under 100 lines; `build_xml_animation_tools` merges them in
# the original order, which is the tool-list order the schema snapshot pins.
def _xml_animation_tools_1(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def read_pptx_xml(
        path: str, slide: int, shape_index: str, part: str = "auto"
    ) -> dict[str, object]:
        """Read one shape's raw underlying OOXML from a PowerPoint (.pptx)
        file -- the escape hatch for anything not covered by a dedicated
        tool (list_pptx_shapes/edit_pptx_shape and friends), most notably
        the real text inside an *existing* SmartArt diagram: python-pptx
        has no SmartArt API at all, and SmartArt's own real text doesn't
        even live in the slide's own XML -- it's in a separate linked
        part this tool resolves automatically (`part="auto"`, the
        default). Always call this before edit_pptx_xml on a shape you
        haven't inspected yet -- its own `xpath` argument has to target
        real element names/namespaces/nesting you can only see here.

        Args:
            path: presentation file to read, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it (is_smartart there flags a SmartArt one)
            part: "auto" (default) reads a SmartArt shape's linked data
                part (where its real text lives) or a normal shape's own
                inline XML, whichever applies. "shape" always reads the
                shape's own inline slide XML, even for SmartArt (its
                `<p:graphicFrame>` wrapper -- position/size/relationship
                pointers, not the diagram's own content). "smartart_data"
                always reads the linked data part, and raises if this
                shape isn't SmartArt.
        """
        return toolkit.read_pptx_xml(path=path, slide=slide, shape_index=shape_index, part=part)

    return {
        "read_pptx_xml": read_pptx_xml,
    }


def _xml_animation_tools_2(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def edit_pptx_xml(
        path: str,
        slide: int,
        shape_index: str,
        xpath: str,
        new_text: Optional[str] = None,  # noqa: UP045
        set_attributes: Optional[str] = None,  # noqa: UP045
        part: str = "auto",
    ) -> dict[str, object]:
        """Edit one element inside a shape's raw OOXML in a PowerPoint
        (.pptx) file, found by XPath -- the narrow escape hatch for
        anything no dedicated tool covers (most notably: changing the
        text of an *existing* node inside a SmartArt diagram, which
        python-pptx has no API for at all). Call read_pptx_xml first --
        `xpath` has to target the real structure it shows you, not a
        guess.

        Deliberately bounded, not a general patch tool: `xpath` must
        match exactly one real element (raises otherwise, same "ambiguous
        match" discipline edit_file's own old_text uses) -- there's no
        way to add, remove, or reorder elements, only change an existing
        one's text and/or attributes. `xpath` understands these
        namespace prefixes: p (presentationml), a (drawingml), r
        (relationships), dgm (SmartArt diagram), p14/a14/p15/p159
        (PowerPoint extension namespaces) -- e.g. `//dgm:t` finds every
        SmartArt text-node element, `//dgm:t[../../@modelId='1']` narrows
        to the one belonging to a specific node.

        Validated before saving -- a "shape"-part edit is checked against
        the real ECMA-376 schema (same guarantee every other hand-XML
        tool in this package already makes: an invalid result means the
        file was never touched). A "smartart_data" edit only gets a
        well-formedness check -- this package has no vendored schema for
        SmartArt's own diagram markup, so a structurally-wrong-but-still-
        well-formed edit there (e.g. a broken node relationship) won't be
        caught here; keep such edits to changing existing text content,
        not restructuring the diagram.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it
            xpath: an XPath expression that must match exactly one element
                inside the target XML (see `part`) -- call read_pptx_xml
                first to see the real structure
            new_text: if given, replaces the matched element's own direct
                text content
            set_attributes: if given, sets attributes on the matched
                element -- one "name=value" pair per line (not a
                structured object: this codebase's tool schemas have to
                stay Gemini-compatible, and a dict-typed parameter breaks
                that, same reason edit_file_batch's own `edits` is a
                delimited string too). `name` is "attr" or "prefix:attr"
                using the same namespace prefixes `xpath` understands --
                e.g. "modelId=2\ntype=parTrans" sets two plain attributes,
                "r:id=rId5" sets one in the relationships namespace
            part: which XML to search -- see read_pptx_xml's own `part`
                argument for the exact "auto"/"shape"/"smartart_data"
                meaning, identical here
        """
        return toolkit.edit_pptx_xml(
            path=path,
            slide=slide,
            shape_index=shape_index,
            xpath=xpath,
            new_text=new_text,
            set_attributes=set_attributes,
            part=part,
        )

    def set_pptx_notes(path: str, slide: int, notes: str) -> dict[str, object]:
        """Set the speaker notes for one slide in a PowerPoint (.pptx) file.

        Replaces that slide's notes entirely (not an append).

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to set notes on
            notes: the full speaker-notes text for that slide
        """
        return toolkit.set_pptx_notes(path=path, slide=slide, notes=notes)

    return {
        "edit_pptx_xml": edit_pptx_xml,
        "set_pptx_notes": set_pptx_notes,
    }


def _xml_animation_tools_3(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def set_pptx_transition(
        path: str, slide: int, transition: str, duration: float = 1.0
    ) -> dict[str, object]:
        """Set the slide-change transition for one slide in a PowerPoint (.pptx) file.

        `transition` is any of PowerPoint's own real native transitions --
        call `list_pptx_transition_types()` for the full list (48 effects
        across PowerPoint's own Subtle/Exciting/Dynamic Content gallery
        categories -- "fade"/"push"/"wipe"/"morph"/"vortex"/"honeycomb"/
        "cube"/"page_curl", etc. -- plus a few legacy aliases), or "none".
        Each effect uses PowerPoint's own sensible default variant (e.g.
        "push" always enters from the right) -- no direction/shape/style
        customization yet. `duration` is in seconds and controls how long
        the transition animation takes when advancing *into* this slide.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to set the transition on
            transition: any name from list_pptx_transition_types(), or "none"
            duration: transition length in seconds
        """
        return toolkit.set_pptx_transition(
            path=path, slide=slide, transition=transition, duration=duration
        )

    def list_pptx_transition_types() -> list[str]:
        """List every `transition` name `set_pptx_transition` accepts --
        PowerPoint's own real native transition gallery (48 effects) plus
        8 legacy aliases. No arguments: this is a static list, not
        specific to any file."""
        return toolkit.list_pptx_transition_types()

    def list_pptx_animation_types() -> list[str]:
        """List every `animation` name `add_pptx_animation` accepts --
        PowerPoint's own real native animation gallery (203 presets across
        entrance/emphasis/exit/motion-path categories) plus 6 legacy
        aliases. No arguments: this is a static list, not specific to any
        file."""
        return toolkit.list_pptx_animation_types()

    return {
        "set_pptx_transition": set_pptx_transition,
        "list_pptx_transition_types": list_pptx_transition_types,
        "list_pptx_animation_types": list_pptx_animation_types,
    }


def _xml_animation_tools_4(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def add_pptx_animation(
        path: str,
        slide: int,
        shape_index: str,
        animation: str,
        duration: float = 0.5,
        trigger: str = "on-click",
        delay: float = 0.0,
        by_paragraph: bool = False,
    ) -> dict[str, object]:
        """Add an animation to one shape on a slide.

        `shape_index` is 0-based, in the order shapes were added to the
        slide (the same convention `list_pptx_shapes`/`edit_pptx_shape`/
        `replace_pptx_image` use -- call `list_pptx_shapes` first to find
        it rather than guessing): for a slide from `write_pptx`, index 0
        is the title and index 1 is the body content/table; each later
        `add_pptx_image` or `add_pptx_chart` call on that slide appends
        one more shape after those.

        `animation` is any of PowerPoint's own 203 real animation
        presets -- call `list_pptx_animation_types()` for the full list,
        grouped by category (`"entrance_*"`: shape starts hidden, then
        reveals; `"exit_*"`: shape is visible, then hides; `"emphasis_*"`:
        shape stays visible throughout; `"path_*"`: shape moves along a
        motion path, then stays at the end position). The original six
        short names this tool exposed before the full catalog still work
        as aliases: `"fade"`->`"entrance_fade"`, `"fly-in"`->
        `"entrance_fly"`, `"exit-fade"`->`"exit_fade"`, `"exit-fly"`->
        `"exit_fly"`, `"emphasis-grow"`->`"emphasis_grow_shrink"`,
        `"emphasis-spin"`->`"emphasis_spin"`. A handful of presets (instant
        appear/disappear toggles, discrete state changes like changing a
        shape's font) aren't duration-adjustable in real PowerPoint either
        -- for those, `duration` is ignored and the result's own
        `duration_ms` reports what was actually used instead of silently
        pretending the requested value took effect.

        `trigger` is PowerPoint's own Animation Pane "Start" setting for
        this animation:
        - `"on-click"` (default): plays the next time the presenter
          advances past this slide -- one click, one animation. Calling
          this again with `trigger="on-click"` adds one more independent
          click group, played in the order you called them in.
        - `"with-previous"`: plays at the same time as whatever animation
          you most recently added to this slide, no extra click needed.
        - `"after-previous"`: plays automatically right when that
          previous animation finishes, no extra click needed -- use this
          to chain a sequence that auto-plays once the presenter clicks
          into the slide (the first animation in the chain can itself be
          `"after-previous"`; it just starts on slide entry, same as real
          PowerPoint). `delay` adds an extra gap (seconds) on top of
          whichever trigger you chose, e.g. a short pause between
          with-previous elements or between one after-previous step and
          the next.

        `by_paragraph=True` animates each of the shape's non-empty text
        paragraphs as its own step instead of animating the whole shape
        at once -- the standard way to reveal a bulleted list one bullet
        at a time. Combine with `trigger="on-click"` for one click per
        bullet, or `trigger="after-previous"` (with a small `delay`) to
        have the bullets cascade in automatically. Raises if the shape
        has no text frame or no non-empty paragraphs.

        This writes hand-built animation XML (python-pptx itself has no
        animation API) and is verified after saving to structurally match
        what was requested, but has only been tested against LibreOffice
        in this environment, not real PowerPoint -- treat it as best-
        effort, and have the user confirm it looks right in PowerPoint
        before relying on it for anything important. The by_paragraph
        paragraph-range targeting in particular is a standard, common
        ECMA-376 pattern but -- unlike the six base effects above -- has
        not been cross-checked against a captured real-PowerPoint sample.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            animation: one of list_pptx_animation_types()'s names, or one
                of the six legacy short aliases above
            duration: animation length in seconds (ignored for the few
                presets that aren't duration-adjustable -- see result's
                own duration_ms)
            trigger: "on-click", "with-previous", or "after-previous"
            delay: extra gap in seconds before this animation starts, on
                top of its trigger's own natural timing
            by_paragraph: animate each non-empty paragraph in the shape's
                text frame as its own step, instead of the whole shape
        """
        return toolkit.add_pptx_animation(
            path, slide, shape_index, animation, duration, trigger, delay, by_paragraph
        )

    return {"add_pptx_animation": add_pptx_animation}


def _xml_animation_tools_5(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def add_pptx_audio(
        path: str,
        slide: int,
        audio_path: str,
        left_in: float = 0.3,
        top_in: float = 0.3,
        trigger: str = "auto",
        start_delay: float = 0.0,
        hidden: bool = False,
    ) -> dict[str, object]:
        """Embed an audio file (mp3/m4a/wav) on a slide -- background
        music, a voiceover/narration track, or a sound effect -- as a
        real PowerPoint media shape with a speaker icon, not just an
        attached file.

        `trigger="auto"` (default) starts playback automatically once the
        slide begins, `start_delay` seconds later (0 by default -- no
        wait). `trigger="on-click"` instead waits for the shape's own
        speaker icon to be clicked during the slideshow, matching
        PowerPoint's own "Start: On Click" option; `start_delay` is
        ignored for this trigger. Only one audio track's timing is set up
        per call -- call this again for a second track on the same or a
        different slide.

        `hidden=True` moves the speaker icon off the visible slide canvas
        instead of placing it at `(left_in, top_in)` -- use this for
        background music/narration nobody should see or accidentally
        click, keeping `trigger="auto"` so it still plays. Leave it
        `False` (the default) for a sound effect or narration the
        presenter might want to see and re-trigger manually.

        This writes hand-built OOXML (python-pptx's own `add_movie` only
        supports video, and reusing it as-is for audio would leave the
        wrong element name and relationship type on the shape) and is
        schema-validated before saving, but has only been tested against
        LibreOffice in this environment, not real PowerPoint -- treat it
        as best-effort, and have the user confirm playback sounds right
        in PowerPoint before relying on it for anything important.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to add the audio to
            audio_path: the audio file to embed, relative to the
                workspace root -- .mp3, .m4a, or .wav
            left_in: horizontal position of the speaker icon, in inches
                (ignored if hidden=True)
            top_in: vertical position of the speaker icon, in inches
                (ignored if hidden=True)
            trigger: "auto" or "on-click"
            start_delay: seconds after slide entry before playback starts
                (only used when trigger="auto")
            hidden: move the speaker icon off-canvas instead of placing
                it on the visible slide
        """
        return toolkit.add_pptx_audio(
            path=path,
            slide=slide,
            audio_path=audio_path,
            left_in=left_in,
            top_in=top_in,
            trigger=trigger,
            start_delay=start_delay,
            hidden=hidden,
        )

    return {
        "add_pptx_audio": add_pptx_audio,
    }


def build_xml_animation_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    return {
        **_xml_animation_tools_1(toolkit),
        **_xml_animation_tools_2(toolkit),
        **_xml_animation_tools_3(toolkit),
        **_xml_animation_tools_4(toolkit),
        **_xml_animation_tools_5(toolkit),
    }
