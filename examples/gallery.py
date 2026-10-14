# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Demonstrates title bar widgets, palettes, and runtime configuration.
"""

import sys

from PySide6 import QtGui
from PySide6 import QtWidgets

import native_titlebar


def main() -> int:
    """Runs an interactive configuration example."""
    application = QtWidgets.QApplication(sys.argv[:1])
    window = native_titlebar.NativeWindow()
    window.setWindowTitle("Native Titlebar - Library Gallery")
    window.setWindowIcon(
        application.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon
        )
    )

    search = QtWidgets.QLineEdit()
    search.setPlaceholderText("Real QLineEdit in the title bar")
    search.setFixedWidth(260)
    window.titlebar.add_widget(search)
    action = QtWidgets.QPushButton("Action")
    window.titlebar.add_widget(action)

    content = QtWidgets.QWidget()
    layout = QtWidgets.QFormLayout(content)
    layout.setContentsMargins(24, 24, 24, 24)
    description = QtWidgets.QLabel(
        "Windows manages the caption buttons on the right.\n"
        "The icon, title, and input field are Qt content in the same window."
    )
    description.setWordWrap(True)
    layout.addRow(description)
    title = QtWidgets.QLineEdit(window.windowTitle())
    title.textChanged.connect(window.setWindowTitle)
    layout.addRow("Window title", title)
    theme = QtWidgets.QComboBox()
    theme.addItems(["System", "Dark", "Light"])

    def change_theme(index: int) -> None:
        palette = QtGui.QPalette()
        if index:
            background, foreground = (
                ("#202020", "#ffffff") if index == 1 else ("#f4f4f4", "#161616")
            )
            palette.setColor(
                QtGui.QPalette.ColorRole.Window, QtGui.QColor(background)
            )
            palette.setColor(
                QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(foreground)
            )
        window.setPalette(palette)

    theme.currentIndexChanged.connect(change_theme)
    layout.addRow("Title bar palette", theme)
    tall = QtWidgets.QCheckBox("Taller native title bar")
    tall.toggled.connect(window.set_tall_title_bar)
    layout.addRow(tall)
    show_title = QtWidgets.QCheckBox("Show window title")
    show_title.setChecked(True)
    show_title.toggled.connect(window.titlebar.set_title_visible)
    layout.addRow(show_title)
    show_icon = QtWidgets.QCheckBox("Show window icon")
    show_icon.setChecked(True)
    show_icon.toggled.connect(window.titlebar.set_icon_visible)
    layout.addRow(show_icon)
    status = QtWidgets.QLabel("Ready")
    search.textChanged.connect(status.setText)
    action.clicked.connect(lambda: status.setText("Qt button clicked"))
    window.integration_error.connect(status.setText)
    layout.addRow("Status", status)

    window.set_central_widget(content)
    window.resize(1100, 560)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
