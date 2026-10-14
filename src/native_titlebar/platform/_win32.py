# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Reads Win32 window ownership, frame styles, and DPI for diagnostics.
"""

import ctypes
from ctypes import wintypes

from native_titlebar import reports

_WS_CAPTION = 0x00C00000


def inspect_hwnd(hwnd: int) -> reports.FrameInfo:
    """Reads child HWND ownership, DPI, and native frame styles.

    Args:
        hwnd: Existing native window handle to inspect on Windows.

    Returns:
        JSON-safe window geometry, frame flags, DPI, and ownership information.

    Raises:
        OSError: If a required Win32 query fails.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT
    user32.GetWindowRect.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.RECT),
    ]
    user32.GetClientRect.argtypes = user32.GetWindowRect.argtypes
    user32.GetWindowRect.restype = user32.GetClientRect.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [
        wintypes.HWND,
        wintypes.LPWSTR,
        ctypes.c_int,
    ]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumChildWindows.argtypes = [
        wintypes.HWND,
        callback_type,
        wintypes.LPARAM,
    ]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.EnumChildWindows.restype = wintypes.BOOL
    pid = wintypes.DWORD()
    if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)):
        raise ctypes.WinError(ctypes.get_last_error())

    def describe(handle: int) -> reports.WindowInfo:
        """Returns class, root ownership, and visibility for one HWND."""
        name = ctypes.create_unicode_buffer(256)
        if not user32.GetClassNameW(handle, name, len(name)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {
            "hwnd": int(handle),
            "class": name.value,
            "root_hwnd": int(user32.GetAncestor(handle, 2)),
            "visible": bool(user32.IsWindowVisible(handle)),
        }

    children: list[reports.WindowInfo] = []
    top_levels: list[reports.WindowInfo] = []

    def child(handle: int, param: int) -> bool:
        del param  # The callback does not use its context argument.
        children.append(describe(handle))
        return True

    def top(handle: int, param: int) -> bool:
        del param  # The callback does not use its context argument.
        other_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(other_pid))
        if other_pid.value == pid.value:
            top_levels.append(describe(handle))
        return True

    # Keep both native callback wrappers alive for synchronous enumeration.
    child_callback = callback_type(child)
    top_callback = callback_type(top)
    user32.EnumChildWindows(hwnd, child_callback, 0)
    if not user32.EnumWindows(top_callback, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    window, client = wintypes.RECT(), wintypes.RECT()
    for function, rect in (
        (user32.GetWindowRect, window),
        (user32.GetClientRect, client),
    ):
        if not function(hwnd, ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())
    style = user32.GetWindowLongW(hwnd, -16) & 0xFFFFFFFF
    return {
        "hwnd": hwnd,
        "dpi": int(user32.GetDpiForWindow(hwnd)),
        "style": hex(style),
        "has_native_caption": bool(style & _WS_CAPTION == _WS_CAPTION),
        "has_system_menu": bool(style & 0x00080000),
        "has_resize_border": bool(style & 0x00040000),
        "window_rect": [window.left, window.top, window.right, window.bottom],
        "client_size": [client.right, client.bottom],
        "children": children,
        "process_top_level_windows": top_levels,
        "visible_top_level_count": sum(w["visible"] for w in top_levels),
    }
