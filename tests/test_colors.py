# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks caption contrast and color resolution without loading Windows APIs.
"""

from PySide6 import QtGui
import pytest

import native_titlebar
from native_titlebar import _colors


@pytest.mark.parametrize(
    ("background", "foreground", "inactive"),
    [
        ("#202020", "#ffffff", "#797979"),
        ("#f4f4f4", "#161616", "#9b9b9b"),
        ("#000000", "#ffffff", "#666666"),
    ],
)
def test_identical_palette_groups_produce_dimmed_inactive_symbols(
    background: str, foreground: str, inactive: str
) -> None:
    """Prevents Qt's identical active/inactive colors from hiding focus loss."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(background))
    palette.setColor(
        QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(foreground)
    )
    role = native_titlebar.ButtonColorRole
    result = _colors.resolve(palette, {})
    assert result[role.FOREGROUND].name() == foreground
    assert result[role.INACTIVE_FOREGROUND].name() == inactive
    assert result[role.INACTIVE_BACKGROUND].name() == background


def test_distinct_inactive_palette_foreground_is_preserved() -> None:
    """Keeps a theme's intentional inactive color instead of dimming twice."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("white"))
    palette.setColor(
        QtGui.QPalette.ColorGroup.Inactive,
        QtGui.QPalette.ColorRole.WindowText,
        QtGui.QColor("#b0a090"),
    )
    result = _colors.resolve(palette, {})
    assert (
        result[native_titlebar.ButtonColorRole.INACTIVE_FOREGROUND].name()
        == "#b0a090"
    )


def test_overrides_drive_derived_states_and_copy_mutable_colors() -> None:
    """Checks overrides, derived states, and independent returned colors."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("black"))
    role = native_titlebar.ButtonColorRole
    overrides = {
        role.BACKGROUND: QtGui.QColor("#202020"),
        role.FOREGROUND: QtGui.QColor("white"),
        role.PRESSED_BACKGROUND: QtGui.QColor("#005080"),
    }
    result = _colors.resolve(palette, overrides)
    assert result[role.INACTIVE_BACKGROUND].name() == "#202020"
    assert result[role.INACTIVE_FOREGROUND].name() == "#797979"
    assert result[role.HOVER_BACKGROUND].name() == "#323232"
    assert result[role.PRESSED_BACKGROUND].name() == "#005080"
    result[role.FOREGROUND].setRed(0)
    assert overrides[role.FOREGROUND].name() == "#ffffff"
    assert result[role.HOVER_FOREGROUND].name() == "#ffffff"


def test_transparent_background_preserves_inactive_contrast() -> None:
    """Keeps translucent backgrounds but resolves symbols to opaque RGB."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#202020"))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("white"))
    role = native_titlebar.ButtonColorRole
    result = _colors.resolve(
        palette,
        {
            role.BACKGROUND: QtGui.QColor(255, 0, 0, 0),
            role.FOREGROUND: QtGui.QColor(255, 255, 255, 20),
            role.PRESSED_BACKGROUND: QtGui.QColor(10, 20, 30, 40),
        },
    )
    assert result[role.BACKGROUND].alpha() == 0
    assert result[role.INACTIVE_BACKGROUND].alpha() == 0
    assert result[role.PRESSED_BACKGROUND].getRgb() == (10, 20, 30, 40)
    assert result[role.FOREGROUND].getRgb() == (255, 255, 255, 255)
    assert result[role.INACTIVE_FOREGROUND].name() == "#797979"
