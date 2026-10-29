# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Demonstrates native captions with QMainWindow menus, toolbars, and docks.
"""

import sys

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

import native_titlebar


class EditorWindow(native_titlebar.NativeMainWindow):
    """A small editor using Qt's standard main-window components."""

    def __init__(self) -> None:
        """Creates the editor, menus, toolbar, dock, and title bar search."""
        super().__init__()
        self.setWindowTitle("Native Titlebar — Main Window")
        self.setWindowIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_FileIcon
            )
        )
        self._editor = QtWidgets.QTextEdit()
        self._editor.setPlaceholderText("Start writing here…")
        self.setCentralWidget(self._editor)

        clear_action = QtGui.QAction("Clear", self)
        clear_action.setShortcut(QtGui.QKeySequence("Ctrl+N"))
        clear_action.triggered.connect(self._editor.clear)
        close_action = QtGui.QAction("Close", self)
        close_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        close_action.triggered.connect(self.close)
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(clear_action)
        file_menu.addSeparator()
        file_menu.addAction(close_action)

        toolbar = QtWidgets.QToolBar("Editor", self)
        toolbar.setObjectName("editorToolbar")
        toolbar.addAction(clear_action)
        self.addToolBar(toolbar)

        outline = QtWidgets.QListWidget()
        outline.addItems(["Introduction", "Notes", "Next steps"])
        outline.itemActivated.connect(
            lambda item: self._editor.append(item.text())
        )
        dock = QtWidgets.QDockWidget("Outline", self)
        dock.setObjectName("outlineDock")
        dock.setWidget(outline)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(toolbar.toggleViewAction())
        view_menu.addAction(dock.toggleViewAction())

        search = QtWidgets.QLineEdit()
        search.setPlaceholderText("Find text…")
        search.setClearButtonEnabled(True)
        search.setFixedWidth(220)
        search.returnPressed.connect(lambda: self._find_text(search.text()))
        self.titleBar().addWidget(search)
        self.statusBar().showMessage("Ready")
        self.resize(1000, 650)

    def _find_text(self, text: str) -> None:
        """Finds the next occurrence and updates the status bar."""
        found = self._editor.find(text)
        self.statusBar().showMessage(
            "Match found" if found else "No further matches", 3000
        )


def main() -> int:
    """Runs the QMainWindow example."""
    app = QtWidgets.QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
