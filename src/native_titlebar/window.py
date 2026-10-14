# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Public native window API. All mutation belongs on the Qt GUI thread.
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
    from typing import SupportsInt

_logger = logging.getLogger(__name__)
_WM_ENTERSIZEMOVE = 0x0231
_WM_EXITSIZEMOVE = 0x0232


class NativeWindow(QtWidgets.QWidget):
    """A QWidget window with Windows-managed caption controls.

    Qt paints the icon, title, and embedded widgets. Windows App Runtime manages
    the three caption controls on the same top-level HWND.

    Attributes:
        titlebar: Owned TitleBar used to add interactive controls.
        integration_error: Signal carrying a message for asynchronous failures.
            Constructor failures instead raise NativeTitleBarError directly.
    """

    integration_error = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Creates and attaches a decorated native window.

        Args:
            parent: Optional Qt owner. This widget remains a top-level window.

        Raises:
            GUIThreadError: If not on the QApplication GUI thread.
            UnsupportedPlatformError: If the platform is not supported.
            RuntimeUnavailableError: If Windows App Runtime cannot be loaded.
            NativeTitleBarError: If native attachment fails.
        """
        _qt.require_gui_thread()
        windows.ensure_runtime()
        self._backend: windows.WindowsTitleBar | None = None
        self._ready = False
        self._syncing = False
        self._in_move_size = False
        self._last_error: str | None = None
        self._central: QtWidgets.QWidget | None = None
        self._screen_handle: QtGui.QWindow | None = None
        self._tall_titlebar = False
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._sync_safely)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.titlebar = titlebar.TitleBar(self)
        self._layout.addWidget(self.titlebar)
        self.titlebar.geometry_changed.connect(self._schedule_sync)
        self.set_central_widget(QtWidgets.QWidget())
        self._ready = True
        self._attach()

    def _attach(self) -> None:
        """Attaches to the current HWND and reconnects screen notifications."""
        hwnd = int(self.winId())
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
        self._backend.set_tall(tall=self._tall_titlebar)
        self._in_move_size = False
        backend = self._backend
        self.destroyed.connect(backend.close)
        if self._screen_handle is not None and shiboken6.isValid(
            self._screen_handle
        ):
            self._screen_handle.screenChanged.disconnect(self._schedule_sync)
        self._screen_handle = self.windowHandle()
        if self._screen_handle is not None:
            self._screen_handle.screenChanged.connect(self._schedule_sync)
        self._sync()

    def set_central_widget(self, widget: QtWidgets.QWidget | None) -> None:
        """Replaces the content and schedules the previous widget for deletion.

        Args:
            widget: New content owned by this window, or None to remove content.
                Use take_central_widget() first to preserve previous content.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            ValueError: If widget is deleted, an ancestor, or the title bar.
            TypeError: If widget is neither QWidget nor None.
        """
        _qt.require_gui_thread()
        if widget is not None:
            _qt.require_widget(widget)
            if not shiboken6.isValid(widget):
                msg = "Cannot use a deleted central widget."
                raise ValueError(msg)
            if widget is self or widget.isAncestorOf(self):
                msg = "Central content cannot be the window or an ancestor."
                raise ValueError(msg)
        self._refresh_central_widget()
        if widget is self._central:
            return
        if widget is self or widget is getattr(self, "titlebar", None):
            msg = "The window and title bar cannot be central widgets"
            raise ValueError(msg)
        if self._central is not None:
            self._layout.removeWidget(self._central)
            self._central.hide()
            self._central.deleteLater()
        self._central = widget
        if widget is not None:
            self._layout.addWidget(widget, 1)
            widget.show()

    def central_widget(self) -> QtWidgets.QWidget | None:
        """Returns the current central widget, or None if absent.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        self._refresh_central_widget()
        return self._central

    def _refresh_central_widget(self) -> None:
        if self._central is not None and (
            not shiboken6.isValid(self._central)
            or self._central.parentWidget() is not self
        ):
            self._central = None

    def take_central_widget(self) -> QtWidgets.QWidget | None:
        """Detaches content and transfers ownership to the caller.

        Returns:
            The previous content without deleting it, or None if absent.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        self._refresh_central_widget()
        widget = self._central
        if widget is not None:
            self._layout.removeWidget(widget)
            widget.hide()
            widget.setParent(None)
            self._central = None
        return widget

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
            self._backend.set_tall(tall=tall)
        self._schedule_sync()

    def _schedule_sync(self, *_: object) -> None:
        """Coalesces native and Qt notifications into one queued GUI update."""
        if self._ready and not self._syncing and not self._timer.isActive():
            self._timer.start(0)

    def _sync_safely(self) -> None:
        """Reports queued-update failures without unwinding through Qt's C++."""
        try:
            self._sync()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Exceptions must not escape a Qt event callback into C++.
            self._last_error = str(exc)
            _logger.exception("Title bar synchronization failed")
            self.integration_error.emit(str(exc))
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
        if not self.testAttribute(QtCore.Qt.WidgetAttribute.WA_WState_Created):
            return
        if int(self.winId()) != self._backend.hwnd:
            self._attach()
            return
        self._syncing = True
        try:
            height, left, right, width = self._backend.metrics()
            scale = self.devicePixelRatioF()
            if height <= 0 or self.isFullScreen():
                self.titlebar.hide()
                self._backend.set_regions([])
                return
            self.titlebar.show()
            self.titlebar.set_native_metrics(height, left, right, scale)
            self._layout.activate()
            bounds = geometry.Rect(
                left, 0, max(0, width - left - right), height
            )
            regions = geometry.drag_rectangles(
                bounds, self.titlebar.interactive_rectangles(scale)
            )
            # Windows holds the mouse capture during its modal move/size loop.
            # Qt can relayout continuously, but rewriting SDK drag regions here
            # needlessly reconfigures the native input surface on every step.
            # Commit the final hit areas after WM_EXITSIZEMOVE, before the next
            # interaction. Programmatic resize stays live.
            if not self._in_move_size:
                self._backend.set_regions(regions)
            self._backend.set_palette(self.titlebar.palette())
        finally:
            self._syncing = False

    def event(self, event: QtCore.QEvent) -> bool:
        """Coalesces layout, palette, and window-handle changes."""
        result = super().event(event)
        if self._ready and event.type() in (
            QtCore.QEvent.Type.WindowTitleChange,
            QtCore.QEvent.Type.WindowIconChange,
            QtCore.QEvent.Type.ActivationChange,
        ):
            self.titlebar.update()
        if self._ready and event.type() in (
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
        return result

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Reattaches to a recreated HWND when the window is shown again."""
        super().showEvent(event)
        self._attach()
        self._schedule_sync()

    def nativeEvent(
        self,
        event_type: QtCore.QByteArray | bytes | bytearray | memoryview,
        message: int | shiboken6.VoidPtr,
    ) -> object:
        """Observes native resize/theme events without replacing handling."""
        # Qt's stub declares int, but QWidget requires VoidPtr at runtime.
        # VoidPtr's __int__ method is also absent from its shipped stub.
        pointer = (
            shiboken6.VoidPtr(message) if isinstance(message, int) else message
        )
        # The SDK and Qt retain native frame processing.
        if self._ready and event_type == b"windows_generic_MSG":
            address = int(cast("SupportsInt", pointer))
            msg = wintypes.MSG.from_address(address)
            if msg.message == _WM_ENTERSIZEMOVE:
                self._in_move_size = True
                _logger.debug(
                    "Native move/size started; deferring drag-region writes"
                )
            elif msg.message == _WM_EXITSIZEMOVE:
                self._in_move_size = False
                _logger.debug(
                    "Native move/size ended; updating final drag regions"
                )
                self._schedule_sync()
            elif msg.message in (
                0x02E0,
                0x031A,
                0x001A,
            ):  # DPI, theme, settings
                self._schedule_sync()
        return super().nativeEvent(event_type, cast("int", pointer))

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
        if not self.testAttribute(QtCore.Qt.WidgetAttribute.WA_WState_Created):
            msg = "No live native window to inspect."
            raise errors.NativeTitleBarError(msg)
        self._sync()
        if self._backend is None or self._backend.native is None:
            msg = "No native title bar is attached."
            raise errors.NativeTitleBarError(msg)
        info = _win32.inspect_hwnd(int(self.winId()))
        height, left, right, _ = self._backend.metrics()
        return reports.WindowDiagnostics(
            **info,
            qt_dpr=self.devicePixelRatioF(),
            titlebar_height_px=height,
            insets_px=[left, right],
            drag_rectangles_px=list(self._backend.regions),
            interactive_rectangles_px=[
                reports.RectangleInfo(
                    x=rect.x, y=rect.y, width=rect.width, height=rect.height
                )
                for rect in self.titlebar.interactive_rectangles(
                    self.devicePixelRatioF()
                )
            ],
            last_error=self._last_error,
            in_native_move_size=self._in_move_size,
        )

    @property
    def last_error(self) -> str | None:
        """The last asynchronous error, or None after a successful sync."""
        return self._last_error

    # These aliases preserve the Qt-style API provided by release 0.1.
    setCentralWidget = set_central_widget  # noqa: N815
    centralWidget = central_widget  # noqa: N815
    takeCentralWidget = take_central_widget  # noqa: N815
    setTallTitleBar = set_tall_title_bar  # noqa: N815

    @property
    def integrationError(self) -> QtCore.SignalInstance:
        """The Qt-style compatibility alias for integration_error."""
        return self.integration_error
