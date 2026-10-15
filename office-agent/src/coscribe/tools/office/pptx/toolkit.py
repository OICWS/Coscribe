"""The deck toolkit: every method of the topic mixins in one class."""

from __future__ import annotations

from .image_tools import ImageToolsMixin
from .review_tools import ReviewToolsMixin
from .shape_tools import ShapeToolsMixin
from .template_tools import TemplateToolsMixin
from .toolkit_base import ToolkitBase
from .xml_animation import XmlAnimationMixin


class PresentationToolkit(
    ReviewToolsMixin,
    TemplateToolsMixin,
    ShapeToolsMixin,
    XmlAnimationMixin,
    ImageToolsMixin,
    ToolkitBase,
):
    """Every deck tool as a method; the topics live in the mixins under office/pptx/."""
