"""A page drawn in the computer's own Chromium-family browser, headless: a screenshot and a report
of what a look would catch (script errors, blocked loads, a page wider than its board, text over
text, text past the board's edge). Edge ships with every Windows, so nothing is installed for it."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The design route's policy, as a meta tag since the page is opened from a file: no network.
_POLICY = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; media-src data: blob:"
)
_TIMEOUT = 45
_WINDOWS_BROWSERS = [
    ("ProgramFiles(x86)", ("Microsoft", "Edge", "Application", "msedge.exe")),
    ("ProgramFiles", ("Microsoft", "Edge", "Application", "msedge.exe")),
    ("LocalAppData", ("Microsoft", "Edge", "Application", "msedge.exe")),
    ("ProgramFiles(x86)", ("Google", "Chrome", "Application", "chrome.exe")),
    ("ProgramFiles", ("Google", "Chrome", "Application", "chrome.exe")),
    ("LocalAppData", ("Google", "Chrome", "Application", "chrome.exe")),
]
_OTHER_BROWSERS = ("chromium", "chromium-browser", "google-chrome", "microsoft-edge")

# First in the head, before the page's own scripts, so their errors are caught too.
_PROBE = (
    '<meta http-equiv="Content-Security-Policy" content="' + _POLICY + '">'
    "<script>window.__coscribeErrors=[];addEventListener('error',function(e){"
    "__coscribeErrors.push(e.message?String(e.message):'could not load '+"
    "((e.target&&(e.target.src||e.target.href))||'a resource'))},true);"
    "document.addEventListener('securitypolicyviolation',function(e){"
    "__coscribeErrors.push('blocked (no network): '+e.blockedURI)});</script>"
)

# Text boxes are the glyph runs of each text node, so inline neighbours never count as overlapping;
# two runs overlap when they share more than a third of the smaller one.
_REPORT = """<script>addEventListener('load',function(){setTimeout(function(){
var W=%(width)d,H=%(height)d,fixed=%(fixed)s,d=document.documentElement,runs=[];
var walk=document.createTreeWalker(document.body||d,NodeFilter.SHOW_TEXT);
while(walk.nextNode()&&runs.length<400){var n=walk.currentNode,t=n.textContent.trim();
if(!t||!n.parentElement||/^(SCRIPT|STYLE)$/.test(n.parentElement.tagName))continue;
var s=getComputedStyle(n.parentElement);if(s.visibility==='hidden'||s.opacity==='0')continue;
var g=document.createRange();g.selectNodeContents(n);var b=g.getBoundingClientRect();
if(b.width<2||b.height<2)continue;runs.push({t:t.slice(0,40),x:b.left,y:b.top,r:b.right,b:b.bottom})}
var over=[],out=[];
for(var i=0;i<runs.length;i++){var a=runs[i];
if(fixed&&(a.x<-1||a.y<-1||a.r>W+1||a.b>H+1))out.push(a.t);
for(var j=i+1;j<runs.length&&over.length<10;j++){var c=runs[j];
var w=Math.min(a.r,c.r)-Math.max(a.x,c.x),h=Math.min(a.b,c.b)-Math.max(a.y,c.y);
if(w>0&&h>0&&w*h>Math.min((a.r-a.x)*(a.b-a.y),(c.r-c.x)*(c.b-c.y))/3)over.push([a.t,c.t])}}
var r={errors:__coscribeErrors.slice(0,10),content_width:d.scrollWidth,
content_height:d.scrollHeight,wider_than_board:d.scrollWidth>W+1,text_overlapping:over,text_past_edge:out.slice(0,10)};
var o=document.createElement('script');o.type='application/json';o.id='coscribe-report';
o.textContent=JSON.stringify(r);(document.body||d).appendChild(o)},400)})</script>"""
_REPORT_IN_DOM = re.compile(
    r'<script type="application/json" id="coscribe-report">(.*?)</script>', re.S
)


class PageShotError(RuntimeError):
    """No browser to draw with, or the browser failed; the text is safe to show."""


@dataclass
class PageShot:
    png: bytes
    report: dict[str, Any] = field(default_factory=dict)


def find_browser() -> str | None:
    """Edge or Chrome where Windows installs them; elsewhere one on PATH. COSCRIBE_PAGE_BROWSER
    names one directly, for development off Windows."""
    override = os.environ.get("COSCRIBE_PAGE_BROWSER")
    if override and Path(override).is_file():
        return override
    if sys.platform == "win32":
        for env_var, segments in _WINDOWS_BROWSERS:
            base = os.environ.get(env_var)
            if base and Path(base, *segments).is_file():
                return str(Path(base, *segments))
        return None
    return next((found for name in _OTHER_BROWSERS if (found := shutil.which(name))), None)


def _with_probe(body: bytes, width: int, height: int, fixed: bool) -> bytes:
    report = _REPORT % {"width": width, "height": height, "fixed": "true" if fixed else "false"}
    head = re.search(rb"<head[^>]*>", body, re.I)
    at = head.end() if head else 0
    body = body[:at] + _PROBE.encode() + body[at:]
    end = body.lower().rfind(b"</body>")
    return body[:end] + report.encode() + body[end:] if end >= 0 else body + report.encode()


@contextmanager
def _no_crash_dialog() -> Iterator[None]:
    """A browser that crashes must not put Windows' "Application Error" box in front of the
    person (seen when a script drew with Edge). A child takes its parent's error mode when it
    starts, so the mode is set just around the start and put back."""
    if sys.platform != "win32":
        yield
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    no_boxes = 0x0001 | 0x0002 | 0x8000  # SEM_FAILCRITICALERRORS, NOGPFAULTERRORBOX, NOOPENFILE
    previous = kernel32.SetErrorMode(no_boxes)
    try:
        yield
    finally:
        kernel32.SetErrorMode(previous)


def _run(browser: str, args: list[str], profile: Path) -> subprocess.CompletedProcess[bytes]:
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--mute-audio",
        "--disable-crash-reporter",
        f"--user-data-dir={profile}",
        *args,
    ]
    # Linux containers (CI, cloud sessions) run as root, where Chromium refuses its own sandbox.
    if sys.platform != "win32" and hasattr(os, "geteuid") and os.geteuid() == 0:
        command.insert(1, "--no-sandbox")
    try:
        with _no_crash_dialog():
            return subprocess.run(
                command,
                capture_output=True,
                timeout=_TIMEOUT,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PageShotError("The browser could not draw the page") from exc


def shoot_page(body: bytes, width: int, height: int, *, fixed: bool) -> PageShot:
    """The page at this viewport size. A `fixed` board (a poster, a phone screen) is also checked
    for text past its edges; a long page is drawn whole."""
    browser = find_browser()
    if browser is None:
        raise PageShotError("No Edge or Chrome on this computer to draw the page with")
    with tempfile.TemporaryDirectory(prefix="coscribe-page-") as folder:
        work = Path(folder)
        page = work / "page.html"
        page.write_bytes(_with_probe(body, width, height, fixed))
        shot = work / "shot.png"
        size = f"--window-size={width},{height}"
        url = page.as_uri()
        dumped = _run(browser, [size, "--virtual-time-budget=3000", "--dump-dom", url], work / "a")
        _run(browser, [size, "--virtual-time-budget=3000", f"--screenshot={shot}", url], work / "b")
        if not shot.is_file():
            raise PageShotError("The browser could not draw the page")
        found = _REPORT_IN_DOM.search(dumped.stdout.decode("utf-8", "replace"))
        try:
            report = json.loads(found.group(1)) if found else {}
        except ValueError:
            report = {}
        return PageShot(png=shot.read_bytes(), report=report)
