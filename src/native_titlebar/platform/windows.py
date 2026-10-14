# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Windows App SDK owns the frame; Qt owns and paints the client widgets.

No WM_NCCALCSIZE override, replacement caption painting, or overlay HWND.
Imports of Microsoft.UI must happen AFTER the runtime bootstrap.
"""

# WinRT imports must follow runtime bootstrap; imports must work on Linux.
# pylint: disable=import-outside-toplevel

from __future__ import annotations

import atexit
import logging
import sys
from typing import TYPE_CHECKING
from typing import cast
import weakref

from PySide6 import QtGui

from native_titlebar import errors
from native_titlebar import geometry

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

    from winrt.windows import foundation
    from winui3.microsoft.ui import windowing

_logger = logging.getLogger(__name__)
_MINIMUM_WINDOWS_BUILD = 17763
# The native runtime has process-wide lifetime. Keep its shutdown handle and
# weak attachment registry here so every window detaches before runtime exit.
_runtime: Callable[[], None] | None = None
_backends: weakref.WeakSet[WindowsTitleBar] = weakref.WeakSet()


def ensure_runtime() -> None:
    """Bootstraps the pinned Windows App Runtime once per process.

    Raises:
        UnsupportedPlatformError: If Windows is absent or older than 1809.
        RuntimeUnavailableError: If Python bindings or Runtime 1.7 are missing.
    """
    global _runtime  # noqa: PLW0603 - Bootstrap has process-wide lifetime.
    if sys.platform != "win32":
        msg = "NativeWindow requires Windows 10 1809+ or Windows 11."
        raise errors.UnsupportedPlatformError(msg)
    if sys.getwindowsversion().build < _MINIMUM_WINDOWS_BUILD:
        msg = "Windows 10 version 1809 (build 17763) or newer is required."
        raise errors.UnsupportedPlatformError(msg)
    if _runtime is not None:
        return
    try:
        from winui3.microsoft.windows.applicationmodel.dynamicdependency import (  # noqa: E501 - SDK namespace.
            bootstrap,
        )

        _runtime = bootstrap.initialize()
    except (ImportError, OSError) as exc:
        msg = (
            "Windows App Runtime 1.7 is missing or cannot be initialized. "
            "Install the runtime matching your Python architecture "
            "(x64 recommended), and use a "
            "regular or uv-managed Python, not Microsoft Store Python. "
            "https://learn.microsoft.com/windows/apps/windows-app-sdk/downloads"
            " "
            f"Original error: {exc}"
        )
        raise errors.RuntimeUnavailableError(msg) from exc
    atexit.register(_shutdown)
    _logger.info("Windows App Runtime initialized")


def _shutdown() -> None:
    """Detaches remaining windows before releasing the process runtime."""
    global _runtime  # noqa: PLW0603 - Release the process-wide shutdown handle.
    for backend in list(_backends):
        backend.close()
    if _runtime is not None:
        # The PyWinRT Shutdown object implements the native callable protocol.
        _runtime()  # pylint: disable=not-callable
        _runtime = None


class WindowsTitleBar:
    """Owns an AppWindow attachment to an existing Qt HWND.

    All mutation is serialized by the owning NativeWindow's GUI thread.
    WinRT objects use the installed SDK's generated static type definitions.

    Attributes:
        hwnd: Existing native window handle owned by Qt.
        native: Attached AppWindow, or None after detaching.
    """

    def __init__(self, hwnd: int, changed: Callable[[], None]) -> None:
        """Attaches native controls and registers a weak change callback.

        Args:
            hwnd: Existing Qt window handle.
            changed: Bound method notified when native window metrics change.

        Raises:
            NativeTitleBarError: If runtime loading or customization fails.
        """
        ensure_runtime()
        from winui3.microsoft.ui import interop
        from winui3.microsoft.ui import windowing

        self.hwnd = hwnd
        self.native: windowing.AppWindow | None = None
        self._token: foundation.EventRegistrationToken | None = None
        self._regions: tuple[tuple[int, int, int, int], ...] | None = None
        self._colors: (
            tuple[tuple[str, tuple[int, int, int, int]], ...] | None
        ) = None
        if not windowing.AppWindowTitleBar.is_customization_supported():
            msg = "This Windows runtime cannot customize the native title bar."
            raise errors.NativeTitleBarError(msg)
        self.native = windowing.AppWindow.get_from_window_id(
            interop.get_window_id_from_window(hwnd)
        )
        self._title_bar().extends_content_into_title_bar = True
        # A WinRT callback must not keep a deleted QWidget alive.
        callback = weakref.WeakMethod(changed)

        def on_changed(
            sender: windowing.AppWindow,
            args: windowing.AppWindowChangedEventArgs,
        ) -> None:
            """Notifies the window while its weak method is alive."""
            del sender, args  # Only the notification is needed.
            method = callback()
            if method is not None:
                method()

        self._handler = on_changed
        self._token = self.native.add_changed(on_changed)
        _backends.add(self)
        _logger.info("Attached AppWindow to existing Qt HWND=%s", hwnd)

    @property
    def regions(self) -> tuple[tuple[int, int, int, int], ...]:
        """The last committed physical drag rectangles."""
        return self._regions or ()

    def metrics(self) -> tuple[int, int, int, int]:
        """Returns physical height, left/right insets, and client width."""
        native = self._app_window()
        bar = self._title_bar()
        return (
            bar.height,
            bar.left_inset,
            bar.right_inset,
            native.client_size.width,
        )

    def _app_window(self) -> windowing.AppWindow:
        """Returns the attached SDK window or raises after detachment."""
        if self.native is None:
            message = "No native title bar is attached."
            raise errors.NativeTitleBarError(message)
        return self.native

    def _title_bar(self) -> windowing.AppWindowTitleBar:
        """Returns a live title bar, guarding nulls after HWND destruction."""
        # SDK stubs omit nulls observed after Qt destroys its HWND.
        bar = cast(
            "windowing.AppWindowTitleBar | None", self._app_window().title_bar
        )
        if bar is None:
            message = "The native window no longer has a title bar."
            raise errors.NativeTitleBarError(message)
        return bar

    def set_regions(self, rectangles: Sequence[geometry.Rect]) -> None:
        """Updates drag regions when their physical rectangles change.

        Args:
            rectangles: Draggable rectangles in window-relative physical pixels.
        """
        values = tuple((r.x, r.y, r.width, r.height) for r in rectangles)
        if values == self._regions:
            return
        from winrt import system
        from winrt.windows import graphics

        self._title_bar().set_drag_rectangles(
            system.Array(
                graphics.RectInt32,
                [graphics.RectInt32(*value) for value in values],
            )
        )
        self._regions = values
        _logger.debug("HWND=%s drag rectangles=%s", self.hwnd, values)

    def set_palette(self, palette: QtGui.QPalette) -> None:
        """Synchronizes all native caption button states with the Qt palette.

        Args:
            palette: Active and inactive Window/WindowText colors to apply.
        """
        # Win10 may ignore these colors. Do not paint substitute buttons.
        from winrt.windows import ui

        roles = (
            (
                "button_background_color",
                QtGui.QPalette.ColorGroup.Active,
                QtGui.QPalette.ColorRole.Window,
            ),
            (
                "button_foreground_color",
                QtGui.QPalette.ColorGroup.Active,
                QtGui.QPalette.ColorRole.WindowText,
            ),
            (
                "button_inactive_background_color",
                QtGui.QPalette.ColorGroup.Inactive,
                QtGui.QPalette.ColorRole.Window,
            ),
            (
                "button_inactive_foreground_color",
                QtGui.QPalette.ColorGroup.Inactive,
                QtGui.QPalette.ColorRole.WindowText,
            ),
        )
        colors: dict[str, tuple[int, int, int, int]] = {}
        for name, group, role in roles:
            color = palette.color(group, role)
            colors[name] = (
                color.red(),
                color.green(),
                color.blue(),
                color.alpha(),
            )
        background = colors["button_background_color"]
        foreground = colors["button_foreground_color"]
        # Setting the normal background does not adapt the SDK's hover defaults.
        # Blend toward the palette's text color: lighter in dark themes, darker
        # in light themes. Blending also works on pure black.
        for state, amount in (("hover", 0.08), ("pressed", 0.12)):
            red, green, blue = (
                round(bg + (fg - bg) * amount)
                for bg, fg in zip(background[:3], foreground[:3], strict=True)
            )
            colors[f"button_{state}_background_color"] = (red, green, blue, 255)
            colors[f"button_{state}_foreground_color"] = foreground
        # Windows retains its own close-button hover/pressed background.
        values = tuple(colors.items())
        if values == self._colors:
            return
        bar = self._title_bar()
        native_colors = {
            name: ui.Color(alpha, red, green, blue)
            for name, (red, green, blue, alpha) in values
        }
        # Explicit assignments let static checks validate SDK property names.
        bar.button_background_color = native_colors["button_background_color"]
        bar.button_foreground_color = native_colors["button_foreground_color"]
        bar.button_inactive_background_color = native_colors[
            "button_inactive_background_color"
        ]
        bar.button_inactive_foreground_color = native_colors[
            "button_inactive_foreground_color"
        ]
        bar.button_hover_background_color = native_colors[
            "button_hover_background_color"
        ]
        bar.button_hover_foreground_color = native_colors[
            "button_hover_foreground_color"
        ]
        bar.button_pressed_background_color = native_colors[
            "button_pressed_background_color"
        ]
        bar.button_pressed_foreground_color = native_colors[
            "button_pressed_foreground_color"
        ]
        self._colors = values

    def set_tall(self, *, tall: bool) -> None:
        """Selects the SDK standard or tall caption height.

        Args:
            tall: Whether to request the taller native caption area.
        """
        from winui3.microsoft.ui import windowing

        self._title_bar().preferred_height_option = (
            windowing.TitleBarHeightOption.TALL
            if tall
            else windowing.TitleBarHeightOption.STANDARD
        )

    def close(self) -> None:
        """Detaches once, accepting an HWND that Qt has already destroyed."""
        _logger.debug("Detaching HWND=%s", self.hwnd)
        native, self.native = self.native, None
        if native is None:
            return
        try:
            if self._token is not None:
                native.remove_changed(self._token)
                self._token = None
            bar = native.title_bar
            if bar is not None:
                bar.reset_to_default()
        except OSError:
            # The HWND may already have been destroyed by its owning QWidget.
            _logger.debug(
                "Cannot reset native title bar during detach; HWND=%s",
                self.hwnd,
                exc_info=True,
            )
        _backends.discard(self)
