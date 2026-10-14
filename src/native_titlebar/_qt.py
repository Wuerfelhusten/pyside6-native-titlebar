# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Shared Qt preconditions for public widget operations.
"""

from PySide6 import QtCore
from PySide6 import QtWidgets

from native_titlebar import errors


def require_widget(value: object) -> None:
    """Rejects non-widget values passed by callers without static checking.

    Args:
        value: Value received by a public QWidget parameter.

    Raises:
        TypeError: If value is not a QWidget.
    """
    if not isinstance(value, QtWidgets.QWidget):
        message = "widget must be a QWidget."
        raise TypeError(message)


def require_gui_thread() -> None:
    """Checks that QApplication exists and the current thread owns it.

    Raises:
        GUIThreadError: If not on the QApplication GUI thread.
    """
    application = QtWidgets.QApplication.instance()
    if not isinstance(application, QtWidgets.QApplication):
        msg = "Create QApplication before any widgets."
        raise errors.GUIThreadError(msg)
    if QtCore.QThread.currentThread() != application.thread():
        msg = "Title bar operations require the QApplication GUI thread."
        raise errors.GUIThreadError(msg)
