"""The toolkit's shared base: workspace scope, path checks and slide opening."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..._workspace import WorkspaceScope
from ..markdown_blocks import Block

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType


class ToolkitBase:
    def __init__(
        self,
        root: str | Path,
        *,
        state_dir: str | Path | None = None,
        custom_templates_dir: str | Path | None = None,
        extra_readable: Sequence[str | Path] = (),
        extra_writable: Sequence[str | Path] = (),
    ) -> None:
        self._scope = WorkspaceScope(
            root, extra_readable=extra_readable, extra_writable=extra_writable
        )
        self._state_dir = state_dir
        self._custom_templates_dir = custom_templates_dir

    def _check_readable(self, path: str) -> Path:
        file_path = self._scope.resolve(path)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return file_path

    def _check_writable(self, path: str, overwrite: bool) -> Path:
        file_path = self._scope.resolve(path, write=True)
        if file_path.exists() and file_path.is_dir():
            raise ValueError(f"Path is a directory: {path}")
        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @staticmethod
    def _require_single_table(table_blocks: list[Block]) -> None:
        if len(table_blocks) > 1:
            raise ValueError("A slide can have at most one table.")

    def _open_slide(self, path: str, slide: int) -> tuple[PresentationType, Path, Any]:
        """Load `path`, validate `slide` is in range, and return (prs,
        file_path, target_slide) -- the load-validate-locate sequence every
        tool that modifies one existing slide repeats."""
        from pptx import Presentation

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if not 1 <= slide <= slide_count:
            raise ValueError(f"Slide {slide} out of range: deck has {slide_count} slides")
        return prs, file_path, prs.slides[slide - 1]
