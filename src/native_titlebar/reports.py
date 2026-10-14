# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Defines the JSON-compatible public diagnostic result schemas.

These TypedDicts describe ordinary dictionaries returned by diagnostics methods.
No native imports or runtime initialization are required to use the schemas.
"""

from typing import TypedDict


class RectangleInfo(TypedDict):
    """A physical-pixel rectangle relative to the window's client area.

    Attributes:
        x: Left edge in physical pixels.
        y: Top edge in physical pixels.
        width: Nonnegative width in physical pixels.
        height: Nonnegative height in physical pixels.
    """

    x: int
    y: int
    width: int
    height: int


# Functional syntax preserves the existing JSON key named "class".
WindowInfo = TypedDict(
    "WindowInfo",
    {"hwnd": int, "class": str, "root_hwnd": int, "visible": bool},
)
WindowInfo.__doc__ = """A native window observed during HWND enumeration.

Attributes:
    hwnd: Native window handle.
    class: Native Win32 class name.
    root_hwnd: Root ancestor handle.
    visible: Whether Windows reports the window as visible.
"""


class FrameInfo(TypedDict):
    """A Win32 frame and ownership snapshot.

    Attributes:
        hwnd: Inspected native window handle.
        dpi: Native dots per inch for the window.
        style: Window style bits as a hexadecimal string.
        has_native_caption: Whether the caption style is present.
        has_system_menu: Whether the system-menu style is present.
        has_resize_border: Whether the resizing border style is present.
        window_rect: Screen-space left, top, right, and bottom coordinates.
        client_size: Client width and height in physical pixels.
        children: Descendant native windows.
        process_top_level_windows: Top-level windows in the owning process.
        visible_top_level_count: Number of visible process top-level windows.
    """

    hwnd: int
    dpi: int
    style: str
    has_native_caption: bool
    has_system_menu: bool
    has_resize_border: bool
    window_rect: list[int]
    client_size: list[int]
    children: list[WindowInfo]
    process_top_level_windows: list[WindowInfo]
    visible_top_level_count: int


class WindowDiagnostics(FrameInfo):
    """A synchronized window snapshot extending the native frame information.

    Attributes:
        qt_dpr: Qt device pixel ratio used for layout conversion.
        titlebar_height_px: Native title bar height in physical pixels.
        insets_px: Native left and right caption insets in physical pixels.
        drag_rectangles_px: Committed (x, y, width, height) drag rectangles.
        interactive_rectangles_px: Visible Qt controls excluded from dragging.
        last_error: Most recent asynchronous error, or None after recovery.
        in_native_move_size: Whether Windows is in its modal move/resize loop.
    """

    qt_dpr: float
    titlebar_height_px: int
    insets_px: list[int]
    drag_rectangles_px: list[tuple[int, int, int, int]]
    interactive_rectangles_px: list[RectangleInfo]
    last_error: str | None
    in_native_move_size: bool


class EnvironmentReport(TypedDict):
    """Installation information collected without creating a window.

    Attributes:
        library: Installed library version.
        python: Python version string.
        python_bits: Python process architecture in bits.
        platform: Python platform identifier.
        os: Operating-system description.
        pyside6: Installed PySide6 version.
        qt: Loaded Qt version.
        required_runtime: Required Windows App Runtime release.
        runtime_available: Bootstrap result, or None if not requested.
        error: Bootstrap error text, or None if no error was reported.
    """

    library: str
    python: str
    python_bits: int
    platform: str
    os: str
    pyside6: str
    qt: str
    required_runtime: str
    runtime_available: bool | None
    error: str | None
