# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Public native window API. All mutation belongs on the Qt GUI thread.
"""

from __future__ import annotations

from typing import cast

from PySide6 import QtCore
from PySide6 import QtWidgets
import shiboken6
import typing_extensions

from native_titlebar import _integration
from native_titlebar import _qt
from native_titlebar import reports
from native_titlebar import titlebar
from native_titlebar.platform import windows


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
        self._ready = False
        self._central: QtWidgets.QWidget | None = None
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.titlebar = titlebar.TitleBar(self)
        self._layout.addWidget(self.titlebar)
        self.setCentralWidget(QtWidgets.QWidget())
        self._integration = _integration.WindowIntegration(
            self,
            self.titlebar,
            self._update_titlebar_layout,
            self.integration_error.emit,
        )
        self._ready = True
        self._integration.attach()

    def _update_titlebar_layout(self) -> None:
        """Applies the layout before native input regions are calculated."""
        self._layout.activate()

    def setCentralWidget(self, widget: QtWidgets.QWidget | None) -> None:
        """Replaces the content and schedules the previous widget for deletion.

        Args:
            widget: New content owned by this window, or None to remove content.
                Use takeCentralWidget() first to preserve previous content.

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

    def centralWidget(self) -> QtWidgets.QWidget | None:
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

    def takeCentralWidget(self) -> QtWidgets.QWidget | None:
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
        self._integration.set_tall_title_bar(tall)

    @typing_extensions.override
    def event(self, event: QtCore.QEvent) -> bool:
        """Updates native geometry after Qt processes a window event."""
        result = super().event(event)
        if self._ready:
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

    @property
    def last_error(self) -> str | None:
        """The last asynchronous error, or None after a successful sync."""
        return self._integration.last_error
