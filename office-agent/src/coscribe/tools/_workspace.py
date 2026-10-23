"""Shared workspace-root path scoping, used by any toolkit that reads or
writes files under a confined root (files, documents, ...).

Beyond the single primary root, optionally accepts extra directories the
user has explicitly trusted -- readable-only or readable+writable -- so a
file that lands outside the workspace (e.g. a browser download folder) can
be read/edited in place instead of needing to be copied into the workspace
first. Writable implies readable. Unconfigured (the default), behavior is
identical to before this existed: everything is confined to `root`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..needs_permission import NeedsPermission
from .exec import suggested_folder


class WorkspaceScope:
    def __init__(
        self,
        root: str | Path,
        *,
        extra_readable: Sequence[str | Path] = (),
        extra_writable: Sequence[str | Path] = (),
        extra_deletable: Sequence[str | Path] = (),
        protected: Sequence[str | Path] = (),
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self._protected = [Path(p).expanduser().resolve() for p in protected]
        self.root.mkdir(parents=True, exist_ok=True)
        self._extra_deletable = [Path(p).expanduser().resolve() for p in extra_deletable]
        self._extra_writable = [
            Path(p).expanduser().resolve() for p in extra_writable
        ] + self._extra_deletable
        self._extra_readable = [
            Path(p).expanduser().resolve() for p in extra_readable
        ] + self._extra_writable

    @property
    def extra_readable(self) -> list[Path]:
        return list(self._extra_readable)

    @property
    def extra_writable(self) -> list[Path]:
        return list(self._extra_writable)

    def resolve(self, path: str, *, write: bool = False, delete: bool = False) -> Path:
        """`delete` covers removing, moving or renaming: only the root and the folders set to
        "Read, write and delete" allow it."""
        candidate = Path(path).expanduser()
        resolved = (
            candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        )
        write = write or delete
        if write and any(self._under(resolved, p) for p in self._protected):
            # The model writes files in Accept Edits without asking, so a settings file it could
            # reach (a policy, a hook, a connector list) would be changed with nobody asked.
            raise PermissionError(
                f"Path is one of coscribe's own settings files; only the user changes it, in "
                f"Settings: {path}"
            )
        if self._under(resolved, self.root):
            return resolved
        allowed = self._extra_writable if write else self._extra_readable
        for extra_root in allowed:
            if self._under(resolved, extra_root):
                if delete and not any(self._under(resolved, p) for p in self._extra_deletable):
                    raise PermissionError(
                        f"{path} is in a folder set to read and write, which allows no deleting, "
                        "moving or renaming. The user can set it to \"Read, write and delete\" in "
                        "Settings > Workspace."
                    )
                return resolved
        verb = "written to" if write else "read"
        message = f"Path cannot be {verb} -- outside any allowed directory: {path}"
        folder = suggested_folder(str(resolved))
        if folder is None:
            raise PermissionError(message)
        raise NeedsPermission("folder", folder, message)

    def relative(self, path: Path) -> str:
        for candidate_root in (self.root, *self._extra_readable):
            try:
                return path.relative_to(candidate_root).as_posix()
            except ValueError:
                continue
        # Only reachable for a path that never went through resolve() (e.g.
        # a caller building a display string by hand) -- fall back to the
        # absolute path rather than raising, since this is display-only.
        return str(path)

    @staticmethod
    def _under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
