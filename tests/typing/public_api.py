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


def check_public_types(window: native_titlebar.NativeWindow) -> None:
    """Checks public values, nested report fields, and compatibility aliases."""
    assert_type(window.titlebar, native_titlebar.TitleBar)
    assert_type(window.titlebar.widgets, tuple[QtWidgets.QWidget, ...])
    assert_type(window.titlebar.geometry_changed, QtCore.SignalInstance)
    assert_type(window.last_error, str | None)
    assert_type(window.central_widget(), QtWidgets.QWidget | None)
    assert_type(window.centralWidget(), QtWidgets.QWidget | None)
    assert_type(window.diagnostics(), reports.WindowDiagnostics)
    assert_type(window.diagnostics()["qt_dpr"], float)
    assert_type(window.diagnostics()["children"][0]["class"], str)
    assert_type(
        window.diagnostics()["interactive_rectangles_px"][0]["width"], int
    )
    assert_type(diagnostics.environment_report(), reports.EnvironmentReport)
    assert_type(
        diagnostics.environment_report()["runtime_available"], bool | None
    )

    # These negative contracts are never executed; mypy must reject each one.
    window.titlebar.add_widget("not a widget")  # type: ignore[arg-type]
    window.set_tall_title_bar("tall")  # type: ignore[arg-type]
    snapshot = window.diagnostics()
    snapshot["qt_dpr"] = "not a number"  # type: ignore[typeddict-item]
