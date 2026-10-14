# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Provides the Qt content hosted inside the native title bar area.
"""

from __future__ import annotations

import math

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
import shiboken6

from native_titlebar import _qt
from native_titlebar import geometry


class TitleBar(QtWidgets.QWidget):
    """A title bar with real Qt controls and optional window icon/title.

    Obtain this widget from NativeWindow.titlebar. The entire rectangle of each
    registered widget, including its descendants, receives normal Qt input.
    Unoccupied space remains available for native window dragging.

    Attributes:
        geometry_changed: Emitted when native input regions need recalculation.
    """

    geometry_changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Creates the Qt title bar content on the GUI thread.

        Args:
            parent: Owning NativeWindow or another Qt widget for standalone use.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        super().__init__(parent)
        self.setObjectName("nativeTitleBar")
        self.setAutoFillBackground(True)
        self._widgets: list[QtWidgets.QWidget] = []
        self._native_metrics: tuple[int, int, int] | None = None
        self._native_left = 0
        self._native_right = 138
        self._title_visible = True
        self._icon_visible = True
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(8)
        self._layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(32)
        self._layout.setContentsMargins(150, 3, 150, 3)

    @property
    def widgets(self) -> tuple[QtWidgets.QWidget, ...]:
        """The registered, live controls still parented to this title bar."""
        _qt.require_gui_thread()
        self._widgets = [
            widget
            for widget in self._widgets
            if shiboken6.isValid(widget) and widget.parentWidget() is self
        ]
        return tuple(self._widgets)

    def add_widget(
        self,
        widget: QtWidgets.QWidget,
        stretch: int = 0,
        alignment: QtCore.Qt.AlignmentFlag | None = None,
    ) -> None:
        """Adds an existing widget and transfers its Qt ownership here.

        Args:
            widget: A live QWidget. Container widgets may hold child controls.
            stretch: Nonnegative horizontal layout stretch factor.
            alignment: Optional Qt alignment inside the assigned layout cell.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            ValueError: If widget is already registered, deleted, an ancestor,
                or stretch is negative.
            TypeError: If widget is not a QWidget.
        """
        _qt.require_gui_thread()
        _qt.require_widget(widget)
        if not shiboken6.isValid(widget):
            msg = "Cannot add a deleted widget."
            raise ValueError(msg)
        if widget is self or widget.isAncestorOf(self):
            msg = "A title bar cannot contain itself or an ancestor."
            raise ValueError(msg)
        if widget in self.widgets:
            msg = "Widget is already in this title bar."
            raise ValueError(msg)
        if stretch < 0:
            msg = "stretch must be nonnegative."
            raise ValueError(msg)
        self._widgets.append(widget)
        self._layout.addWidget(
            widget,
            stretch,
            QtCore.Qt.AlignmentFlag(0) if alignment is None else alignment,
        )
        widget.installEventFilter(self)
        self.geometry_changed.emit()

    def remove_widget(self, widget: QtWidgets.QWidget) -> None:
        """Removes and hides a control without deleting it.

        Args:
            widget: A currently registered widget. It keeps this Qt parent until
                the caller reparents it or adds it to another layout.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            ValueError: If widget is not currently registered.
        """
        _qt.require_gui_thread()
        if widget not in self.widgets:
            msg = "Widget is not registered in this title bar."
            raise ValueError(msg)
        self._widgets.remove(widget)
        self._layout.removeWidget(widget)
        widget.removeEventFilter(self)
        widget.hide()
        self.geometry_changed.emit()
        self.update()

    def add_stretch(self, stretch: int = 1) -> None:
        """Adds draggable flexible space to the layout.

        Args:
            stretch: Nonnegative horizontal layout stretch factor.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
            ValueError: If stretch is negative.
        """
        _qt.require_gui_thread()
        if stretch < 0:
            msg = "stretch must be nonnegative."
            raise ValueError(msg)
        self._layout.addStretch(stretch)
        self.geometry_changed.emit()

    # Qt's toggled(bool) signal passes its value positionally.
    def set_title_visible(self, visible: bool) -> None:  # noqa: FBT001
        """Shows or hides the painted title, without changing windowTitle().

        Args:
            visible: Whether Qt should paint the window title in the title bar.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        self._title_visible = visible
        self.update()

    # Qt's toggled(bool) signal passes its value positionally.
    def set_icon_visible(self, visible: bool) -> None:  # noqa: FBT001
        """Shows or hides the painted icon, without changing windowIcon().

        Args:
            visible: Whether Qt should paint the window icon in the title bar.

        Raises:
            GUIThreadError: If called outside the QApplication GUI thread.
        """
        _qt.require_gui_thread()
        self._icon_visible = visible
        self.update()

    def set_native_metrics(
        self, height: int, left: int, right: int, scale: float
    ) -> None:
        """Applies physical-pixel metrics with the Qt scale factor.

        Args:
            height: Native title bar height in physical pixels.
            left: Native left inset in physical pixels.
            right: Native right inset in physical pixels.
            scale: Positive Qt device pixel ratio for the owning window.
        """
        metrics = (
            math.ceil(height / scale),
            math.ceil(left / scale),
            math.ceil(right / scale),
        )
        if metrics == self._native_metrics:
            return
        self._native_metrics = metrics
        self._native_left, self._native_right = metrics[1:]
        # Symmetric space keeps a single control centered in the whole window.
        inset = max(self._native_left, self._native_right) + 12
        self.setFixedHeight(metrics[0])
        self._layout.setContentsMargins(inset, 3, inset, 3)
        self._layout.activate()
        self.update()

    def _caption_rect(self) -> QtCore.QRect:
        """Returns logical caption space before the first visible control."""
        left = self._native_left + 8
        right = self.width() - self._native_right - 12
        for widget in self.widgets:
            if not widget.isHidden():
                right = min(right, widget.x() - 12)
        return QtCore.QRect(left, 0, max(0, right - left), self.height())

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paints the Qt-owned title and icon beside native caption buttons."""
        super().paintEvent(event)
        window = self.window()
        rect = self._caption_rect()
        with QtGui.QPainter(self) as painter:
            painter.setClipRect(rect)
            if self._icon_visible:
                icon = window.windowIcon()
                if icon.isNull():
                    icon = self.style().standardIcon(
                        QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
                    )
                icon_rect = QtCore.QRect(
                    rect.left(), (self.height() - 16) // 2, 16, 16
                )
                icon.paint(painter, icon_rect)
            text_rect = rect.adjusted(24 if self._icon_visible else 0, 0, 0, 0)
            if self._title_visible and text_rect.width() > 0:
                group = (
                    QtGui.QPalette.ColorGroup.Active
                    if window.isActiveWindow()
                    else QtGui.QPalette.ColorGroup.Inactive
                )
                painter.setPen(
                    self.palette().color(
                        group, QtGui.QPalette.ColorRole.WindowText
                    )
                )
                text = self.fontMetrics().elidedText(
                    window.windowTitle(),
                    QtCore.Qt.TextElideMode.ElideRight,
                    text_rect.width(),
                )
                painter.drawText(
                    text_rect,
                    QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                    | QtCore.Qt.TextFlag.TextSingleLine,
                    text,
                )

    def interactive_rectangles(self, scale: float) -> list[geometry.Rect]:
        """Returns visible exclusions in window-relative physical pixels.

        Args:
            scale: Positive Qt device pixel ratio for the owning window.

        Returns:
            Physical rectangles enclosing visible registered Qt controls.
        """
        result = []
        for widget in self.widgets:
            if widget.isHidden():
                continue
            position = widget.mapTo(self.window(), QtCore.QPoint(0, 0))
            result.append(
                geometry.physical_rect(
                    position.x(),
                    position.y(),
                    widget.width(),
                    widget.height(),
                    scale,
                )
            )
        return result

    def event(self, event: QtCore.QEvent) -> bool:
        """Schedules input region updates when this widget changes."""
        result = super().event(event)
        if event.type() in (
            QtCore.QEvent.Type.LayoutRequest,
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.ChildRemoved,
        ):
            self.update()
            self.geometry_changed.emit()
        return result

    def eventFilter(
        self, watched: QtCore.QObject, event: QtCore.QEvent
    ) -> bool:
        """Observes embedded widget geometry without consuming its input."""
        if event.type() in (
            QtCore.QEvent.Type.Move,
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.Hide,
            QtCore.QEvent.Type.LayoutRequest,
            QtCore.QEvent.Type.ParentChange,
        ):
            self.update()
            self.geometry_changed.emit()
        return super().eventFilter(watched, event)

    # Qt-style names remain supported for applications written against 0.1.
    addWidget = add_widget  # noqa: N815
    removeWidget = remove_widget  # noqa: N815
    addStretch = add_stretch  # noqa: N815

    @property
    def geometryChanged(self) -> QtCore.SignalInstance:
        """The Qt-style compatibility alias for geometry_changed."""
        return self.geometry_changed
