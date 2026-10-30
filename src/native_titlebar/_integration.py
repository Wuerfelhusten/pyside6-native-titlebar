# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Shares native title bar synchronization across Qt window types.
"""

from __future__ import annotations

from ctypes import wintypes
import logging
from typing import TYPE_CHECKING
from typing import cast

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
import shiboken6

from native_titlebar import _qt
from native_titlebar import errors
from native_titlebar import geometry
from native_titlebar import reports
from native_titlebar import titlebar
from native_titlebar.platform import _win32
from native_titlebar.platform import windows

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import SupportsInt

_logger = logging.getLogger(__name__)
_WM_ENTERSIZEMOVE = 0x0231
_WM_EXITSIZEMOVE = 0x0232


class WindowIntegration:
    """Shares native HWND handling between the public Qt window classes."""

    def __init__(
        self,
        window: QtWidgets.QWidget,
        bar: titlebar.TitleBar,
        update_layout: Callable[[], None],
        report_error: Callable[[str], None],
    ) -> None:
        """Prepares native state; attach() runs after the host is initialized.

        Args:
            window: Top-level Qt widget whose HWND receives caption controls.
            bar: Qt title bar owned by the window.
            update_layout: Applies title bar geometry before hit testing.
            report_error: Emits asynchronous failures through the host signal.
        """
        self._window = window
        self._titlebar = bar
        self._update_layout = update_layout
        self._report_error = report_error
        self._backend: windows.WindowsTitleBar | None = None
        self._syncing = False
        self._in_move_size = False
        self._last_error: str | None = None
        self._screen_handle: QtGui.QWindow | None = None
        self._tall_titlebar = False
        self._timer = QtCore.QTimer(window)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.sync_safely)
        bar.geometryChanged.connect(self._schedule_sync)
        bar.buttonColorsChanged.connect(self._schedule_sync)

    def attach(self) -> None:
        """Attaches to the current HWND and reconnects screen notifications."""
        hwnd = int(self._window.winId())
        if (
            self._backend is not None
            and self._backend.native is not None
            and self._backend.hwnd == hwnd
        ):
            return
        if self._backend is not None:
            self._backend.close()
        try:
            self._backend = windows.WindowsTitleBar(hwnd, self._schedule_sync)
        except (ImportError, OSError) as exc:
            msg = f"Cannot attach native title bar to HWND {hwnd}: {exc}"
            raise errors.NativeTitleBarError(msg) from exc
        self._backend.setTall(tall=self._tall_titlebar)
        self._in_move_size = False
        backend = self._backend
        self._window.destroyed.connect(backend.close)
        if self._screen_handle is not None and shiboken6.isValid(
            self._screen_handle
        ):
            self._screen_handle.screenChanged.disconnect(self._schedule_sync)
        self._screen_handle = self._window.windowHandle()
        if self._screen_handle is not None:
            self._screen_handle.screenChanged.connect(self._schedule_sync)
        self._sync()

    # Qt's toggled(bool) signal passes its value positionally.
    def set_tall_title_bar(
        self,
        tall: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Selects tall captions, preserving the choice across HWND recreation.

        Args:
            tall: Whether to use the SDK's taller caption area.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        self._tall_titlebar = tall
        if self._backend is not None and self._backend.native is not None:
            self._backend.setTall(tall=tall)
        self._schedule_sync()

    def _schedule_sync(self, *_: object) -> None:
        """Coalesces native and Qt notifications into one queued GUI update."""
        if not self._syncing and not self._timer.isActive():
            self._timer.start(0)

    def sync_safely(self) -> None:
        """Reports queued-update failures without unwinding through Qt's C++."""
        try:
            self._sync()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Exceptions must not escape a Qt event callback into C++.
            self._last_error = str(exc)
            _logger.exception("Title bar synchronization failed")
            self._report_error(str(exc))
        else:
            self._last_error = None

    def _sync(self) -> None:
        """Updates Qt layout and native regions outside modal resizing."""
        if (
            self._syncing
            or self._backend is None
            or self._backend.native is None
        ):
            return
        # close() can destroy Qt's HWND without deleting the QWidget. Do not
        # accidentally recreate a hidden native window from a queued update.
        if not self._window.testAttribute(
            QtCore.Qt.WidgetAttribute.WA_WState_Created
        ):
            return
        if int(self._window.winId()) != self._backend.hwnd:
            self.attach()
            return
        self._syncing = True
        try:
            height, left, right, width = self._backend.metrics()
            scale = self._window.devicePixelRatioF()
            if height <= 0 or self._window.isFullScreen():
                self._titlebar.hide()
                self._update_layout()
                self._backend.setRegions([])
                return
            self._titlebar.show()
            self._titlebar.setNativeMetrics(height, left, right, scale)
            self._update_layout()
            bounds = geometry.Rect(
                left, 0, max(0, width - left - right), height
            )
            regions = geometry.dragRectangles(
                bounds, self._titlebar.interactiveRectangles(scale)
            )
            # Windows holds the mouse capture during its modal move/size loop.
            # Qt can relayout continuously, but rewriting SDK drag regions here
            # needlessly reconfigures the native input surface on every step.
            # Commit the final hit areas after WM_EXITSIZEMOVE, before the next
            # interaction. Programmatic resize stays live.
            if not self._in_move_size:
                self._backend.setRegions(regions)
            self._backend.setButtonColors(self._titlebar.buttonColors())
        finally:
            self._syncing = False

    def handle_event(self, event: QtCore.QEvent) -> None:
        """Updates the integration after Qt processes a window event."""
        if event.type() == QtCore.QEvent.Type.Show:
            self.attach()
        if event.type() in (
            QtCore.QEvent.Type.WindowTitleChange,
            QtCore.QEvent.Type.WindowIconChange,
            QtCore.QEvent.Type.ActivationChange,
        ):
            self._titlebar.update()
        if event.type() in (
            QtCore.QEvent.Type.WinIdChange,
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.WindowStateChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.StyleChange,
            QtCore.QEvent.Type.LayoutRequest,
        ):
            self._schedule_sync()

    def handle_native_event(
        self,
        event_type: QtCore.QByteArray | bytes | bytearray | memoryview,
        pointer: shiboken6.VoidPtr,
    ) -> None:
        """Observes resize and theme messages without replacing Qt handling."""
        if event_type != b"windows_generic_MSG":
            return
        # VoidPtr's __int__ method is absent from its shipped stub.
        address = int(cast("SupportsInt", pointer))
        msg = wintypes.MSG.from_address(address)
        if msg.message == _WM_ENTERSIZEMOVE:
            self._in_move_size = True
            _logger.debug(
                "Native move/size started; deferring drag-region writes"
            )
        elif msg.message == _WM_EXITSIZEMOVE:
            self._in_move_size = False
            _logger.debug("Native move/size ended; updating final drag regions")
            self._schedule_sync()
        elif msg.message in (0x02E0, 0x031A, 0x001A):  # DPI, theme, settings
            self._schedule_sync()

    def diagnostics(self) -> reports.WindowDiagnostics:
        """Returns a JSON-safe snapshot of native geometry and ownership.

        This flushes pending synchronization on an existing HWND. It does
        not create a hidden window after close(). Numeric checks do not prove
        visual correctness. Snapshot keys may grow in minor releases.

        Returns:
            HWND, DPI, frame styles, child HWNDs, drag/control rectangles,
            native resize-loop state, and the most recent asynchronous error.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            NativeTitleBarError: If the native window was destroyed.
        """
        _qt.require_gui_thread()
        if not self._window.testAttribute(
            QtCore.Qt.WidgetAttribute.WA_WState_Created
        ):
            msg = "No live native window to inspect."
            raise errors.NativeTitleBarError(msg)
        self._sync()
        if self._backend is None or self._backend.native is None:
            msg = "No native title bar is attached."
            raise errors.NativeTitleBarError(msg)
        info = _win32.inspect_hwnd(int(self._window.winId()))
        height, left, right, _ = self._backend.metrics()
        return reports.WindowDiagnostics(
            **info,
            qt_dpr=self._window.devicePixelRatioF(),
            titlebar_height_px=height,
            insets_px=[left, right],
            drag_rectangles_px=list(self._backend.regions()),
            interactive_rectangles_px=[
                reports.RectangleInfo(
                    x=rect.x, y=rect.y, width=rect.width, height=rect.height
                )
                for rect in self._titlebar.interactiveRectangles(
                    self._window.devicePixelRatioF()
                )
            ],
            last_error=self._last_error,
            in_native_move_size=self._in_move_size,
        )

    def last_error(self) -> str | None:
        """Returns the last integration error, or None after recovery."""
        return self._last_error
