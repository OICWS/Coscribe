"""Something a saved workflow's run was stopped from doing because the
person hasn't allowed it yet: a folder outside its own, or a site its
steps don't name; or that only the person can do, signing in to a site.
A run that may ask waits for an answer; anywhere else
this is an ordinary refusal with a message that says what to allow."""

from __future__ import annotations

from typing import Any, Literal

SITE_MARK = "NEEDS_SITE_PERMISSION:"
# The desktop app's mark on a step that failed on a sign-in form, a code or a captcha.
SIGN_IN_MARK = "NEEDS_SIGN_IN:"


class NeedsPermission(PermissionError):
    """`target` is what to allow: a folder to add, or a site's host; for "sign_in", the
    site to sign in to."""

    def __init__(
        self,
        kind: Literal["folder", "site", "sign_in"],
        target: str,
        message: str,
        hint: str = "",
    ) -> None:
        # The hint is for a model that can ask the person itself; a waiting run shows `message`.
        super().__init__(f"{message} {hint}".strip())
        self.kind = kind
        self.target = target
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "target": self.target, "message": self.message}
