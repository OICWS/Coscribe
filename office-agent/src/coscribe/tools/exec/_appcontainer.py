"""Starting a process inside a Windows AppContainer, through ctypes.

`subprocess.Popen` cannot pass `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES`, so the process is
started with `CreateProcessW` here and wrapped in the few parts of `Popen` that
`running.RunningCommand` uses (`pid`, `returncode`, `poll`, `wait`, `stdout`, `stderr`).

A container process reaches a file only when both the user and one of its SIDs (the container's
own, or a capability it holds) are allowed by the file's ACL. coscribe grants folders to custom
capability SIDs (`capability_sid`), never to the container's SID, so one run holds only the
folders of its own conversation. Without the `internetClient` family of capabilities it has no
network at all, loopback included.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import BinaryIO

PROFILE = "coscribe.scripts"

# Windows' own capability names: outbound, inbound and the home or company network.
NETWORK_CAPABILITIES = ("internetClient", "internetClientServer", "privateNetworkClientServer")


class ContainerUnavailable(OSError):
    """This machine cannot start a process in an AppContainer."""


if sys.platform == "win32":
    import ctypes
    import msvcrt
    import os
    import threading
    from ctypes import wintypes

    _userenv = ctypes.WinDLL("userenv")
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernelbase = ctypes.WinDLL("kernelbase", use_last_error=True)

    _PSID = ctypes.c_void_p
    _ALREADY_EXISTS = ctypes.c_long(0x800700B7).value
    _EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    _CREATE_UNICODE_ENVIRONMENT = 0x00000400
    _STARTF_USESTDHANDLES = 0x00000100
    _ATTRIBUTE_HANDLE_LIST = 0x00020002
    _ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
    _SE_GROUP_ENABLED = 0x00000004
    _WAIT_TIMEOUT = 0x00000102
    _INFINITE = 0xFFFFFFFF

    class _SidAndAttributes(ctypes.Structure):
        _fields_ = [("Sid", _PSID), ("Attributes", wintypes.DWORD)]

    class _SecurityCapabilities(ctypes.Structure):
        _fields_ = [
            ("AppContainerSid", _PSID),
            ("Capabilities", ctypes.POINTER(_SidAndAttributes)),
            ("CapabilityCount", wintypes.DWORD),
            ("Reserved", wintypes.DWORD),
        ]

    class _StartupInfo(ctypes.Structure):
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

    class _StartupInfoEx(ctypes.Structure):
        _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]

    class _ProcessInformation(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    _userenv.CreateAppContainerProfile.restype = ctypes.c_long
    _userenv.CreateAppContainerProfile.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        ctypes.POINTER(_SidAndAttributes),
        wintypes.DWORD,
        ctypes.POINTER(_PSID),
    ]
    _userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
    _userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(_PSID),
    ]
    _advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    _advapi32.ConvertSidToStringSidW.argtypes = [_PSID, ctypes.POINTER(wintypes.LPWSTR)]
    _kernelbase.DeriveCapabilitySidsFromName.restype = wintypes.BOOL
    _kernelbase.DeriveCapabilitySidsFromName.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(ctypes.POINTER(_PSID)),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(ctypes.POINTER(_PSID)),
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    _kernel32.InitializeProcThreadAttributeList.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    _kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
    _kernel32.UpdateProcThreadAttribute.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    _kernel32.CreateProcessW.restype = wintypes.BOOL
    _kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(_StartupInfoEx),
        ctypes.POINTER(_ProcessInformation),
    ]
    _kernel32.WaitForSingleObject.restype = wintypes.DWORD
    _kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    _kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    # SIDs live as long as the process: they are few and asked for on every run.
    _sids: dict[str, int] = {}
    _sids_lock = threading.Lock()

    def _sid_text(sid: int) -> str:
        text = wintypes.LPWSTR()
        if not _advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        value = text.value or ""
        _kernel32.LocalFree(text)
        return value

    def _container_sid() -> int:
        with _sids_lock:
            if PROFILE in _sids:
                return _sids[PROFILE]
            sid = _PSID()
            hr = _userenv.CreateAppContainerProfile(
                PROFILE, "coscribe scripts", "Scripts coscribe runs", None, 0, ctypes.byref(sid)
            )
            if hr == _ALREADY_EXISTS:
                hr = _userenv.DeriveAppContainerSidFromAppContainerName(PROFILE, ctypes.byref(sid))
            if hr != 0 or not sid.value:
                raise ContainerUnavailable(f"AppContainer profile: HRESULT {hr & 0xFFFFFFFF:#010x}")
            _sids[PROFILE] = sid.value
            return sid.value

    def _capability(name: str) -> int:
        with _sids_lock:
            if name in _sids:
                return _sids[name]
            groups = ctypes.POINTER(_PSID)()
            group_count = wintypes.DWORD()
            sids = ctypes.POINTER(_PSID)()
            sid_count = wintypes.DWORD()
            if not _kernelbase.DeriveCapabilitySidsFromName(
                name,
                ctypes.byref(groups),
                ctypes.byref(group_count),
                ctypes.byref(sids),
                ctypes.byref(sid_count),
            ):
                raise ContainerUnavailable(ctypes.WinError(ctypes.get_last_error()))
            value = sids[0]
            if not value:
                raise ContainerUnavailable(f"no capability SID for {name}")
            _sids[name] = value
            return value

    def capability_sid(name: str) -> str:
        """`S-1-15-3-1024-...`: the SID Windows derives from a custom capability's name."""
        return _sid_text(_capability(name))

    def _environment_block(env: Mapping[str, str]) -> ctypes.Array[ctypes.c_wchar]:
        # Sorted without regard to case, as CreateProcess expects; one NUL after each pair and
        # one at the end.
        pairs = sorted(env.items(), key=lambda kv: kv[0].upper())
        text = "".join(f"{k}={v}\0" for k, v in pairs) + "\0"
        return ctypes.create_unicode_buffer(text, len(text))

    class ContainerProcess:
        """The part of `subprocess.Popen` that `RunningCommand` uses."""

        def __init__(self, handle: int, pid: int, stdout: BinaryIO, stderr: BinaryIO) -> None:
            self._handle: int | None = handle
            self.pid = pid
            self.stdout = stdout
            self.stderr = stderr
            self.returncode: int | None = None
            self._lock = threading.Lock()

        def _settle(self, wait_ms: int) -> int | None:
            with self._lock:
                if self._handle is None:
                    return self.returncode
                if _kernel32.WaitForSingleObject(self._handle, wait_ms) == _WAIT_TIMEOUT:
                    return None
                code = wintypes.DWORD()
                _kernel32.GetExitCodeProcess(self._handle, ctypes.byref(code))
                _kernel32.CloseHandle(self._handle)
                self._handle = None
                # Signed, as Popen reports it on Windows (a crash is a negative NTSTATUS).
                self.returncode = ctypes.c_int32(code.value).value
                return self.returncode

        def poll(self) -> int | None:
            return self._settle(0)

        def wait(self, timeout: float | None = None) -> int:
            wait_ms = _INFINITE if timeout is None else max(0, int(timeout * 1000))
            code = self._settle(wait_ms)
            if code is None:
                raise subprocess.TimeoutExpired(str(self.pid), timeout or 0)
            return code

        def __del__(self) -> None:
            if self._handle is not None:
                _kernel32.CloseHandle(self._handle)

    def start(
        argv: Sequence[str],
        cwd: str,
        env: Mapping[str, str],
        capabilities: Sequence[str],
    ) -> ContainerProcess:
        """Starts `argv` in the container, holding the named capabilities, with stdout and
        stderr on pipes and stdin on NUL."""
        container = _container_sid()
        caps = [_capability(name) for name in capabilities]
        cap_array = (_SidAndAttributes * max(1, len(caps)))(
            *(_SidAndAttributes(sid, _SE_GROUP_ENABLED) for sid in caps)
        )
        security = _SecurityCapabilities(container, cap_array if caps else None, len(caps), 0)

        out_read, out_write = os.pipe()
        err_read, err_write = os.pipe()
        null = os.open(os.devnull, os.O_RDONLY)
        child_ends = (null, out_write, err_write)
        handles = [msvcrt.get_osfhandle(fd) for fd in child_ends]
        for handle in handles:
            os.set_handle_inheritable(handle, True)
        # Only these three are inherited, not every inheritable handle the server holds.
        handle_list = (wintypes.HANDLE * len(handles))(*handles)

        size = ctypes.c_size_t()
        _kernel32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
        attributes = ctypes.create_string_buffer(size.value)
        try:
            if not _kernel32.InitializeProcThreadAttributeList(
                attributes, 2, 0, ctypes.byref(size)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                for attribute, value, value_size in (
                    (
                        _ATTRIBUTE_SECURITY_CAPABILITIES,
                        ctypes.byref(security),
                        ctypes.sizeof(security),
                    ),
                    (_ATTRIBUTE_HANDLE_LIST, handle_list, ctypes.sizeof(handle_list)),
                ):
                    if not _kernel32.UpdateProcThreadAttribute(
                        attributes, 0, attribute, value, value_size, None, None
                    ):
                        raise ctypes.WinError(ctypes.get_last_error())
                info = _StartupInfoEx(
                    _StartupInfo(
                        cb=ctypes.sizeof(_StartupInfoEx),
                        dwFlags=_STARTF_USESTDHANDLES,
                        hStdInput=handles[0],
                        hStdOutput=handles[1],
                        hStdError=handles[2],
                    ),
                    ctypes.cast(attributes, ctypes.c_void_p),
                )
                process = _ProcessInformation()
                # A string is a command line already, for a shell whose quoting is not argv's.
                line = argv if isinstance(argv, str) else subprocess.list2cmdline(list(argv))
                command_line = ctypes.create_unicode_buffer(line)
                block = _environment_block(env)
                if not _kernel32.CreateProcessW(
                    None,
                    command_line,
                    None,
                    None,
                    True,
                    _EXTENDED_STARTUPINFO_PRESENT | _CREATE_UNICODE_ENVIRONMENT,
                    ctypes.cast(block, ctypes.c_void_p),
                    cwd,
                    ctypes.byref(info),
                    ctypes.byref(process),
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                _kernel32.DeleteProcThreadAttributeList(attributes)
        except BaseException:
            for fd in (out_read, err_read):
                os.close(fd)
            raise
        finally:
            # The child holds its own copies now; ours would keep the pipes open after it ends.
            for fd in child_ends:
                os.close(fd)
        _kernel32.CloseHandle(process.hThread)
        return ContainerProcess(
            process.hProcess,
            process.dwProcessId,
            os.fdopen(out_read, "rb"),
            os.fdopen(err_read, "rb"),
        )

else:

    class ContainerProcess:
        pid: int
        returncode: int | None
        stdout: BinaryIO
        stderr: BinaryIO

        def poll(self) -> int | None:
            raise ContainerUnavailable("AppContainer is Windows only")

        def wait(self, timeout: float | None = None) -> int:
            raise ContainerUnavailable("AppContainer is Windows only")

    def capability_sid(name: str) -> str:
        raise ContainerUnavailable("AppContainer is Windows only")

    def start(
        argv: Sequence[str],
        cwd: str,
        env: Mapping[str, str],
        capabilities: Sequence[str],
    ) -> ContainerProcess:
        raise ContainerUnavailable("AppContainer is Windows only")
