"""Data labels that carry their own text. openpyxl's data label has no `tx`, so it can neither
write a point's name as its label nor keep one a workbook already has: a quadrant chart's item
names would vanish the first time the workbook is saved again. A label class with `tx` takes the
place of openpyxl's in the one list that holds labels, for reading and for writing."""

from __future__ import annotations

from typing import Any

_ELEMENTS = (
    "idx",
    "tx",
    "numFmt",
    "spPr",
    "txPr",
    "dLblPos",
    "showLegendKey",
    "showVal",
    "showCatName",
    "showSerName",
    "showPercent",
    "showBubbleSize",
    "showLeaderLines",
    "separator",
)
_label_class: Any = None


def label_class() -> Any:
    """The data label class with `tx`, put in place for every workbook read or written after."""
    global _label_class
    if _label_class is not None:
        return _label_class
    from openpyxl.chart.label import DataLabel, DataLabelList
    from openpyxl.chart.text import Text
    from openpyxl.descriptors import Sequence, Typed

    class NamedLabel(DataLabel):
        tx = Typed(expected_type=Text, allow_none=True)
        __elements__ = _ELEMENTS
        # The class builder lists only this class's own nested values; the rest are inherited.
        __nested__ = DataLabel.__nested__
        __attrs__ = DataLabel.__attrs__

        def __init__(self, idx: int = 0, tx: Any = None, **rest: Any) -> None:
            self.tx = tx
            super().__init__(idx=idx, **rest)

    # A new descriptor in place of the list's own, so each label it reads or writes is this class.
    field: Any = Sequence(expected_type=NamedLabel, allow_none=True)
    field.name = "dLbl"
    setattr(DataLabelList, field.name, field)
    _label_class = NamedLabel
    return NamedLabel
