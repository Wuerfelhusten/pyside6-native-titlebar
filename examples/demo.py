# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Runs a minimal demo; --extended adds a QLineEdit.
"""

import argparse
import json
import logging
import pathlib
import sys

from PySide6 import QtCore
from PySide6 import QtWidgets

import native_titlebar

_logger = logging.getLogger("native_titlebar.demo")


def main() -> int:
    """Runs the interactive title bar example."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--diagnostics", type=pathlib.Path)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--title", help="Window title, useful when comparing demo versions"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    app = QtWidgets.QApplication(sys.argv[:1])
    window = native_titlebar.NativeWindow()
    window.setWindowIcon(
        app.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon
        )
    )
    window.setWindowTitle(
        args.title
        or (
            "Native Titlebar — Input Test"
            if args.extended
            else "Native Titlebar — PySide6"
        )
    )
    button = QtWidgets.QPushButton("Test Qt button")
    button.setMinimumWidth(150)
    window.titlebar.add_widget(button)
    clicks = 0

    def clicked() -> None:
        nonlocal clicks
        clicks += 1
        button.setText(f"Clicks: {clicks}")
        _logger.info("Qt button clicked: %s", clicks)

    button.clicked.connect(clicked)
    if args.extended:
        search = QtWidgets.QLineEdit()
        search.setPlaceholderText("Search …")
        search.setFixedWidth(220)
        window.titlebar.add_widget(search)
    window.set_central_widget(QtWidgets.QWidget())
    window.resize(900, 500)
    window.show()

    def record() -> None:
        info = window.diagnostics()
        _logger.info("Native diagnostics: %s", json.dumps(info))
        if args.diagnostics:
            args.diagnostics.parent.mkdir(parents=True, exist_ok=True)
            args.diagnostics.write_text(
                json.dumps(info, indent=2), encoding="utf-8"
            )

    QtCore.QTimer.singleShot(250, record)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
