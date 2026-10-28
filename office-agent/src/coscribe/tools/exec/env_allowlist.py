"""The environment a script or command the agent runs starts with (issue #667).

It is built from a list of names the operating system and the usual tools need, never by
copying the server's environment: the server holds every provider API key there, because the
model SDKs read them from it, and a script that prints `os.environ` would otherwise hand them to
the model. A list of names to remove would miss the next key someone adds.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from ...runtime import without_credentials
from .script_env import overlay_env

# Upper-cased: Windows' names are case-insensitive, and the proxy and certificate names are
# read in either case by different tools elsewhere.
_PASSED = frozenset(
    {
        # Windows
        "ALLUSERSPROFILE",
        "APPDATA",
        "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)",
        "COMMONPROGRAMW6432",
        "COMPUTERNAME",
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "NUMBER_OF_PROCESSORS",
        "ONEDRIVE",
        "ONEDRIVECOMMERCIAL",
        "ONEDRIVECONSUMER",
        "OS",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL",
        "PROCESSOR_REVISION",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "PSMODULEPATH",
        "PUBLIC",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "USERDOMAIN",
        "USERNAME",
        "USERPROFILE",
        "WINDIR",
        # POSIX
        "HOME",
        "LANG",
        "LANGUAGE",
        "LOGNAME",
        "SHELL",
        "TERM",
        "TMPDIR",
        "TZ",
        "USER",
        # Both
        "PATH",
        "TEMP",
        "TMP",
        # A TLS-intercepting company proxy needs its root certificate trusted.
        "CURL_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
    }
)

_PROXIES = frozenset({"ALL_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"})


def child_env(
    extra: Mapping[str, str] | None = None, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    """What a script or command line starts with: the names in `_PASSED` and the proxy
    addresses from `base` (the server's environment by default), the proxies without a user
    name or password, then `extra` (the conversation's own variables) over them."""
    source = os.environ if base is None else base
    passed: dict[str, str] = {}
    for name, value in source.items():
        upper = name.upper()
        if upper in _PROXIES:
            passed[name] = without_credentials(value)
        elif upper in _PASSED or upper.startswith("LC_"):
            passed[name] = value
    return overlay_env(passed, extra)
