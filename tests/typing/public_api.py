# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Static API contracts checked by mypy, without starting a Qt application.

assert_type rejects regressions that silently replace public result types with
Any. The intentionally invalid calls must keep producing their specific errors;
mypy's unused-ignore check fails if those calls ever become accepted.
"""

from typing import assert_type

from PySide6 import QtCore
from PySide6 import QtWidgets

import native_titlebar
from native_titlebar import diagnostics
from native_titlebar import reports


def check_public_types(
    window: native_titlebar.NativeWindow | native_titlebar.NativeMainWindow,
) -> None:
    """Checks public values, signals, and nested report fields."""
    assert_type(window.titleBar(), native_titlebar.TitleBar)
    assert_type(window.titleBar().widgets(), tuple[QtWidgets.QWidget, ...])
    assert_type(window.titleBar().geometryChanged, QtCore.SignalInstance)
    assert_type(window.lastError(), str | None)
    assert_type(window.centralWidget(), QtWidgets.QWidget | None)
    assert_type(window.diagnostics(), reports.WindowDiagnostics)
    assert_type(window.diagnostics()["qt_dpr"], float)
    assert_type(window.diagnostics()["children"][0]["class"], str)
    assert_type(
        window.diagnostics()["interactive_rectangles_px"][0]["width"], int
    )
    assert_type(diagnostics.environmentReport(), reports.EnvironmentReport)
    assert_type(
        diagnostics.environmentReport()["runtime_available"], bool | None
    )

    # These negative contracts are never executed; mypy must reject each one.
    window.titleBar().addWidget("not a widget")  # type: ignore[arg-type]
    window.setTallTitleBar("tall")  # type: ignore[arg-type]
    snapshot = window.diagnostics()
    snapshot["qt_dpr"] = "not a number"  # type: ignore[typeddict-item]


def check_main_window_types(window: native_titlebar.NativeMainWindow) -> None:
    """Checks QMainWindow compatibility without casts or untyped wrappers."""
    main_window: QtWidgets.QMainWindow = window
    assert_type(main_window, QtWidgets.QMainWindow)
    assert_type(window.menuBar(), QtWidgets.QMenuBar)
    assert_type(window.statusBar(), QtWidgets.QStatusBar)
    assert_type(window.saveState(), QtCore.QByteArray)
    window.setContentsMargins(1, 2, 3, 4)
    window.setContentsMargins(QtCore.QMargins(1, 2, 3, 4))
    window.setCentralWidget(QtWidgets.QWidget())
    window.addToolBar(QtWidgets.QToolBar())
    window.addDockWidget(
        QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, QtWidgets.QDockWidget()
    )
