"""Prototype for issue #560: can `run_python_script` run under a Windows AppContainer?

Run on Windows only (the CI job in .github/workflows/windows-sandbox-prototype.yml):

    python scripts/prototype_script_sandbox.py

It builds a script venv like tools/exec/script_env.py does (openpyxl and pandas, so a numpy DLL
load is part of the question), creates an AppContainer profile, grants it the folders a
conversation would have (one read-write, one read-only) plus read access to the interpreter, and
runs a probe script inside it. The probe tries what the issue's contract allows and forbids,
directly and through child processes, and prints one JSON line per check. This script compares
each result with what the contract wants, prints a table, and exits 1 when one differs.

Nothing here is product code: it answers whether the mechanism holds before anything is built on
it. The ACEs it adds are removed and the profile deleted at the end.
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

assert sys.platform == "win32", "the AppContainer prototype runs on Windows only"

PROFILE = "coscribe.script-sandbox.prototype"

# The probe runs inside the container. Each check prints {"check", "ok", "detail"}; "ok" is
# whether the operation succeeded, not whether that is good.
PROBE = r"""
import json, os, shutil, socket, subprocess, sys, time, urllib.request

cfg = json.loads(sys.argv[1])
rw, ro, outside = cfg["rw"], cfg["ro"], cfg["outside"]


def run(name, fn):
    try:
        detail = fn()
        print(json.dumps({"check": name, "ok": True, "detail": str(detail)[:200]}), flush=True)
    except BaseException as exc:
        print(json.dumps({"check": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"[:200]}), flush=True)


def write(path, text="x"):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def child(code):
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip().splitlines()[-1])
    return out.stdout.strip()


def cmd(line):
    out = subprocess.run(["cmd.exe", "/c", line], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"exit {out.returncode}: {(out.stderr or out.stdout).strip()}")
    return out.stdout.strip()


def tcp(host, port):
    socket.create_connection((host, port), timeout=10).close()
    return f"{host}:{port}"


run("import openpyxl", lambda: __import__("openpyxl").__version__)
run("import pandas (numpy DLLs)", lambda: __import__("pandas").DataFrame({"a": [1, 2]}).sum().iloc[0])
run("write rw folder", lambda: write(os.path.join(rw, "made.txt")))
run("mkdir+rmtree in rw folder", lambda: (os.makedirs(os.path.join(rw, "d", "e")), shutil.rmtree(os.path.join(rw, "d"))))
run("read ro folder", lambda: read(os.path.join(ro, "input.txt")))
run("write ro folder", lambda: write(os.path.join(ro, "new.txt")))
run("delete in ro folder", lambda: os.remove(os.path.join(ro, "input.txt")))
run("read outside", lambda: read(os.path.join(outside, "secret.txt")))
run("list outside", lambda: os.listdir(outside))
run("write outside", lambda: write(os.path.join(outside, "new.txt")))
run("delete outside", lambda: os.remove(os.path.join(outside, "secret.txt")))
run("rename outside", lambda: os.rename(os.path.join(outside, "secret.txt"), os.path.join(outside, "moved.txt")))
run("move outside->rw", lambda: shutil.move(os.path.join(outside, "secret.txt"), os.path.join(rw, "stolen.txt")))
run("read user profile Desktop", lambda: os.listdir(os.path.join(cfg["profile"], "Desktop")))
run("write user profile", lambda: write(os.path.join(cfg["profile"], "coscribe-proto.txt")))
run("write TEMP (scratch)", lambda: write(os.path.join(os.environ["TEMP"], "t.txt")))
run("read Windows fonts", lambda: len(os.listdir(os.path.join(os.environ["SystemRoot"], "Fonts"))))
run("child python write rw", lambda: child(f"open({os.path.join(rw, 'c.txt')!r}, 'w').write('x')"))
run("child python write outside", lambda: child(f"open({os.path.join(outside, 'c.txt')!r}, 'w').write('x')"))
run("child python read outside", lambda: child(f"print(open({os.path.join(outside, 'secret.txt')!r}).read())"))
run("cmd echo > rw", lambda: cmd(f'echo x> "{os.path.join(rw, "cmd.txt")}"'))
run("cmd echo > outside", lambda: cmd(f'echo x> "{os.path.join(outside, "cmd.txt")}"'))
run("cmd del outside", lambda: cmd(f'del /f /q "{os.path.join(outside, "secret.txt")}" && if exist "{os.path.join(outside, "secret.txt")}" exit 5'))
run("powershell write outside", lambda: subprocess.run(["powershell.exe", "-NoProfile", "-Command", f"Set-Content -Path '{os.path.join(outside, 'ps.txt')}' -Value x -ErrorAction Stop"], capture_output=True, text=True, timeout=120, check=True).returncode)
run("tcp 1.1.1.1:443", lambda: tcp("1.1.1.1", 443))
run("https example.com", lambda: urllib.request.urlopen("https://example.com", timeout=10).status)
run("dns resolve", lambda: socket.gethostbyname("example.com"))
run("tcp loopback", lambda: tcp("127.0.0.1", cfg["loopback_port"]))
"""

# What the issue's contract wants for each check: True means it must succeed.
EXPECTED = {
    "import openpyxl": True,
    "import pandas (numpy DLLs)": True,
    "write rw folder": True,
    "mkdir+rmtree in rw folder": True,
    "read ro folder": True,
    "write ro folder": False,
    "delete in ro folder": False,
    "read outside": False,
    "list outside": False,
    "write outside": False,
    "delete outside": False,
    "rename outside": False,
    "move outside->rw": False,
    "read user profile Desktop": False,
    "write user profile": False,
    "write TEMP (scratch)": True,
    "read Windows fonts": True,
    "child python write rw": True,
    "child python write outside": False,
    "child python read outside": False,
    "cmd echo > rw": True,
    "cmd echo > outside": False,
    "cmd del outside": False,
    "powershell write outside": False,
    "tcp 1.1.1.1:443": False,
    "https example.com": False,
    "dns resolve": False,
    "tcp loopback": False,
}

# ---- Win32 -------------------------------------------------------------------------------------

userenv = ctypes.WinDLL("userenv")
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PSID = ctypes.c_void_p
HRESULT_ALREADY_EXISTS = ctypes.c_long(0x800700B7).value
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
INFINITE = 0xFFFFFFFF


class SID_AND_ATTRIBUTES(ctypes.Structure):  # noqa: N801 -- the Win32 name
    _fields_ = [("Sid", PSID), ("Attributes", wintypes.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("AppContainerSid", PSID),
        ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
        ("CapabilityCount", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES),
    wintypes.DWORD,
    ctypes.POINTER(PSID),
]
userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
    wintypes.LPCWSTR,
    ctypes.POINTER(PSID),
]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
advapi32.ConvertSidToStringSidW.argtypes = [PSID, ctypes.POINTER(wintypes.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOEXW),
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.LocalFree.argtypes = [ctypes.c_void_p]


def container_sid() -> tuple[PSID, str]:
    sid = PSID()
    hr = userenv.CreateAppContainerProfile(
        PROFILE, PROFILE, "coscribe prototype", None, 0, ctypes.byref(sid)
    )
    if hr == HRESULT_ALREADY_EXISTS:
        hr = userenv.DeriveAppContainerSidFromAppContainerName(PROFILE, ctypes.byref(sid))
    if hr != 0:
        raise OSError(f"AppContainer profile: HRESULT {hr & 0xFFFFFFFF:#010x}")
    text = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
        raise ctypes.WinError(ctypes.get_last_error())
    value = text.value or ""
    kernel32.LocalFree(text)
    return sid, value


def grant(path: Path, sid: str, rights: str) -> None:
    # (OI)(CI) so files the folder already holds and ones made later inherit it; icacls walks
    # the existing tree through the inheritance on its own.
    subprocess.run(
        ["icacls", str(path), "/grant", f"*{sid}:(OI)(CI)({rights})", "/Q"],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def revoke(path: Path, sid: str) -> None:
    subprocess.run(
        ["icacls", str(path), "/remove:g", f"*{sid}", "/Q"], check=False, stdout=subprocess.DEVNULL
    )


def run_in_container(
    sid: PSID, argv: list[str], cwd: Path, env: dict[str, str], log: Path
) -> tuple[int, int]:
    """Start argv in the container, stdout and stderr to `log`. Returns (pid, process handle)."""
    caps = SECURITY_CAPABILITIES(sid, None, 0, 0)
    size = ctypes.c_size_t()
    kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
    attrs = ctypes.create_string_buffer(size.value)
    if not kernel32.InitializeProcThreadAttributeList(attrs, 1, 0, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel32.UpdateProcThreadAttribute(
        attrs,
        0,
        PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
        ctypes.byref(caps),
        ctypes.sizeof(caps),
        None,
        None,
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    import msvcrt

    out = open(log, "wb")  # noqa: SIM115 -- the handle has to outlive this call until the child exits
    handle = msvcrt.get_osfhandle(out.fileno())
    os.set_handle_inheritable(handle, True)

    info = STARTUPINFOEXW()
    info.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    info.StartupInfo.dwFlags = STARTF_USESTDHANDLES
    info.StartupInfo.hStdOutput = handle
    info.StartupInfo.hStdError = handle
    info.lpAttributeList = ctypes.cast(attrs, ctypes.c_void_p)
    block = "".join(f"{k}={v}\0" for k, v in sorted(env.items())) + "\0"
    env_buf = ctypes.create_unicode_buffer(block, len(block))
    proc = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
    if not kernel32.CreateProcessW(
        None,
        cmdline,
        None,
        None,
        True,
        EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
        env_buf,
        str(cwd),
        ctypes.byref(info),
        ctypes.byref(proc),
    ):
        err = ctypes.get_last_error()
        out.close()
        raise ctypes.WinError(err)
    kernel32.CloseHandle(proc.hThread)
    out.close()
    return proc.dwProcessId, proc.hProcess


def wait(process: int, timeout_s: float) -> int:
    kernel32.WaitForSingleObject(process, int(timeout_s * 1000))
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(process, ctypes.byref(code))
    kernel32.CloseHandle(process)
    return code.value


def alive(pid: int) -> bool:
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True
    )
    return str(pid) in out.stdout


# ---- The run -----------------------------------------------------------------------------------


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="coscribe-sandbox-"))
    venv = base / "script-env"
    print(f"Python {sys.version.split()[0]} at {sys.base_prefix}")
    t0 = time.monotonic()
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    py = venv / "Scripts" / "python.exe"
    subprocess.run([str(py), "-m", "pip", "install", "-q", "openpyxl", "pandas"], check=True)
    print(f"venv ready in {time.monotonic() - t0:.0f}s")

    # The folders a conversation would have. "outside" stands for the rest of the user's disk:
    # it sits in the user profile, which AppContainers cannot reach unless granted.
    rw = base / "workspace"
    ro = base / "reference"
    scratch = base / "scratch"
    outside = Path(os.environ["USERPROFILE"]) / "coscribe-sandbox-outside"
    for folder in (rw, ro, scratch, outside):
        folder.mkdir(parents=True, exist_ok=True)
    (ro / "input.txt").write_text("reference", encoding="utf-8")
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    probe = scratch / "probe.py"
    probe.write_text(PROBE, encoding="utf-8")

    sid_ptr, sid = container_sid()
    print(f"AppContainer SID {sid}")
    grants = [(rw, "M"), (scratch, "M"), (ro, "RX"), (venv, "RX"), (Path(sys.base_prefix), "RX")]
    t0 = time.monotonic()
    for folder, rights in grants:
        grant(folder, sid, rights)
    print(f"ACLs granted in {time.monotonic() - t0:.1f}s")

    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    cfg = {
        "rw": str(rw),
        "ro": str(ro),
        "outside": str(outside),
        "profile": os.environ["USERPROFILE"],
        "loopback_port": listener.getsockname()[1],
    }
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {"SYSTEMROOT", "WINDIR", "PATH", "USERPROFILE", "PATHEXT", "COMSPEC", "SYSTEMDRIVE"}
    }
    env.update(TEMP=str(scratch), TMP=str(scratch), PYTHONIOENCODING="utf-8")

    failed = 0
    try:
        log = base / "probe.log"
        pid, handle = run_in_container(
            sid_ptr, [str(py), str(probe), json.dumps(cfg)], rw, env, log
        )
        code = wait(handle, 600)
        text = log.read_text(encoding="utf-8", errors="replace")
        results = {}
        for line in text.splitlines():
            try:
                row = json.loads(line)
                results[row["check"]] = row
            except (ValueError, KeyError):
                print(f"  | {line}")
        print(f"\nprobe exit code {code}\n")
        print(f"{'check':34} {'want':7} {'got':7} detail")
        for check, want in EXPECTED.items():
            row = results.get(check)
            got = None if row is None else row["ok"]
            mark = "ok " if got == want else "BAD"
            failed += got != want
            print(
                f"{mark} {check:30} {'allow' if want else 'deny':7} {'-' if got is None else ('allow' if got else 'deny'):7} {'' if row is None else row['detail']}"
            )
        print(f"\nsecret.txt still outside: {(outside / 'secret.txt').exists()}")
        failed += not (outside / "secret.txt").exists()
        stray = [p.name for p in outside.iterdir() if p.name != "secret.txt"]
        print(f"files the container left outside: {stray}")
        failed += bool(stray)

        # running.py stops a script with `taskkill /T /F`; the tree must still die in a container.
        sleeper = scratch / "tree.py"
        sleeper.write_text(
            "import subprocess, sys, time\n"
            "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
            "print(c.pid, flush=True)\n"
            "time.sleep(300)\n",
            encoding="utf-8",
        )
        tree_log = base / "tree.log"
        pid, handle = run_in_container(sid_ptr, [str(py), str(sleeper)], rw, env, tree_log)
        grandchild = 0
        for _ in range(60):
            time.sleep(0.5)
            first = tree_log.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            if first and first[0].isdigit():
                grandchild = int(first[0])
                break
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
        wait(handle, 10)
        time.sleep(1)
        tree_ok = grandchild > 0 and not alive(pid) and not alive(grandchild)
        print(
            f"taskkill /T stops the container's tree: {tree_ok} (pid {pid}, grandchild {grandchild})"
        )
        failed += not tree_ok
    finally:
        listener.close()
        for folder, _ in grants:
            revoke(folder, sid)
        userenv.DeleteAppContainerProfile(PROFILE)
        shutil.rmtree(outside, ignore_errors=True)
        shutil.rmtree(base, ignore_errors=True)

    print(f"\n{failed} result(s) differ from the contract")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
