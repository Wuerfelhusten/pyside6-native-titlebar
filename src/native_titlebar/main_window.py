# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Provides a native title bar for Qt main windows.
"""

from __future__ import annotations

from typing import cast
from typing import overload

from PySide6 import QtCore
from PySide6 import QtWidgets
import shiboken6
import typing_extensions

from native_titlebar import _integration
from native_titlebar import _qt
from native_titlebar import reports
from native_titlebar import titlebar
from native_titlebar.platform import windows


class NativeMainWindow(QtWidgets.QMainWindow):
    """A QMainWindow with Windows-managed caption controls and Qt title widgets.

    Menus, toolbars, dock widgets, the status bar, and central content use the
    standard QMainWindow API. The title bar occupies an additional top content
    margin, leaving Qt's main-window layout and ownership rules intact.

    Attributes:
        integrationError: Signal carrying a message for asynchronous failures.
            Constructor failures instead raise NativeTitleBarError directly.
    """

    integrationError = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Creates a top-level main window and attaches its native title bar.

        Args:
            parent: Optional Qt owner. This remains a top-level window.

        Raises:
            GUIThreadError: If not on the QApplication GUI thread.
            UnsupportedPlatformError: If the platform is not supported.
            RuntimeUnavailableError: If Windows App Runtime cannot be loaded.
            NativeTitleBarError: If native attachment fails.
        """
        _qt.require_gui_thread()
        windows.ensureRuntime()
        self._ready = False
        self._content_margins = QtCore.QMargins()
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self._titlebar = titlebar.TitleBar(self)
        self.setCentralWidget(QtWidgets.QWidget())
        self._integration = _integration.WindowIntegration(
            self,
            self._titlebar,
            self._update_titlebar_layout,
            self.integrationError.emit,
        )
        self._ready = True
        self._integration.attach()

    def titleBar(self) -> titlebar.TitleBar:
        """Returns the title bar owned by this window.

        Use its addWidget() and removeWidget() methods to manage controls.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        return self._titlebar

    def _update_titlebar_layout(self) -> None:
        """Reserves caption space above Qt's complete main-window layout."""
        height = 0 if self._titlebar.isHidden() else self._titlebar.height()
        margins = self._content_margins
        super().setContentsMargins(
            margins.left(),
            margins.top() + height,
            margins.right(),
            margins.bottom(),
        )
        self._titlebar.setGeometry(0, 0, self.width(), height)
        self._titlebar.raise_()
        layout = self.layout()
        if layout is not None:
            layout.activate()
        bar_layout = self._titlebar.layout()
        if bar_layout is not None:
            bar_layout.activate()

    @overload
    def setContentsMargins(self, left: QtCore.QMargins) -> None: ...

    @overload
    def setContentsMargins(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> None: ...

    @typing_extensions.override
    def setContentsMargins(
        self,
        left: int | QtCore.QMargins,
        top: int | None = None,
        right: int | None = None,
        bottom: int | None = None,
    ) -> None:
        """Sets application margins in addition to the reserved caption space.

        Inherited contentsMargins() includes the current title bar height.
        Full screen removes only the caption space, preserving these margins.

        Args:
            left: Left margin, or a QMargins object containing all four values.
            top: Top margin when passing four integers.
            right: Right margin when passing four integers.
            bottom: Bottom margin when passing four integers.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            TypeError: If the arguments do not match either Qt overload.
        """
        _qt.require_gui_thread()
        if isinstance(left, QtCore.QMargins):
            if any(value is not None for value in (top, right, bottom)):
                msg = "QMargins must be passed without additional margins."
                raise TypeError(msg)
            self._content_margins = QtCore.QMargins(left)
        elif top is not None and right is not None and bottom is not None:
            self._content_margins = QtCore.QMargins(left, top, right, bottom)
        else:
            msg = "Pass a QMargins object or four integer margins."
            raise TypeError(msg)
        self._update_titlebar_layout()

    @typing_extensions.override
    def setCentralWidget(self, widget: QtWidgets.QWidget | None) -> None:
        """Replaces the content using QMainWindow's ownership rules.

        Args:
            widget: New content owned by this window, or None to remove it.
                Call takeCentralWidget() first to preserve existing content.

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
            if widget is self._titlebar:
                msg = "The window and title bar cannot be central widgets"
                raise ValueError(msg)
        if widget is None:
            previous = super().takeCentralWidget()
            if previous is not None:
                previous.hide()
                previous.deleteLater()
        elif widget is not self.centralWidget():
            super().setCentralWidget(widget)

    # Qt's toggled(bool) signal passes its value positionally.
    def setTallTitleBar(
        self,
        tall: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Selects tall captions, preserving the choice across HWND recreation.

        Args:
            tall: Whether to use the SDK's taller caption area.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        self._integration.set_tall_title_bar(tall)

    @typing_extensions.override
    def event(self, event: QtCore.QEvent) -> bool:
        """Updates native geometry after Qt processes a window event."""
        result = super().event(event)
        if self._ready:
            if event.type() == QtCore.QEvent.Type.Resize:
                self._update_titlebar_layout()
            self._integration.handle_event(event)
        return result

    @typing_extensions.override
    def nativeEvent(
        self,
        event_type: QtCore.QByteArray | bytes | bytearray | memoryview,
        message: int | shiboken6.VoidPtr,
    ) -> object:
        """Observes native messages while preserving Qt's frame handling."""
        # Qt's stub declares int, but QWidget requires VoidPtr at runtime.
        pointer = (
            shiboken6.VoidPtr(message) if isinstance(message, int) else message
        )
        if self._ready:
            self._integration.handle_native_event(event_type, pointer)
        return super().nativeEvent(event_type, cast("int", pointer))

    def diagnostics(self) -> reports.WindowDiagnostics:
        """Returns a JSON-safe snapshot of native geometry and ownership.

        Flushes pending synchronization on an existing HWND. Numeric checks do
        not prove visual correctness. Snapshot keys may grow in minor releases.

        Returns:
            HWND, DPI, frame styles, child HWNDs, drag/control rectangles,
            native resize-loop state, and the most recent asynchronous error.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            NativeTitleBarError: If the native window was destroyed.
        """
        return self._integration.diagnostics()

    def lastError(self) -> str | None:
        """Returns the last integration error, or None after recovery."""
        return self._integration.last_error()
