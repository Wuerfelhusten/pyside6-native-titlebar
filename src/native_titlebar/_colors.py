# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Resolves palette defaults and explicit native caption color overrides.
"""

from collections.abc import Mapping

from PySide6 import QtGui

from native_titlebar import colors


def _blend(
    background: QtGui.QColor, foreground: QtGui.QColor, amount: float
) -> QtGui.QColor:
    """Returns an opaque RGB blend with the requested foreground fraction."""
    return QtGui.QColor(
        *(
            round(bg + (fg - bg) * amount)
            for bg, fg in zip(
                (background.red(), background.green(), background.blue()),
                (foreground.red(), foreground.green(), foreground.blue()),
                strict=True,
            )
        )
    )


def resolve(
    palette: QtGui.QPalette,
    overrides: Mapping[colors.ButtonColorRole, QtGui.QColor],
) -> dict[colors.ButtonColorRole, QtGui.QColor]:
    """Returns detached colors, deriving unspecified states from the palette.

    An inactive palette foreground different from its active counterpart is
    preserved. Otherwise, inactive symbols retain 40 percent of the active
    foreground contrast. Hover and pressed backgrounds blend 8 and 12 percent
    toward the active foreground. Explicit overrides always take precedence.

    Args:
        palette: Window and WindowText colors for active and inactive groups.
        overrides: Validated per-role colors owned by the caller.

    Returns:
        All eight roles with opaque foregrounds and independent QColor values.
    """
    role = colors.ButtonColorRole
    active_background = palette.color(
        QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Window
    )
    active_foreground = palette.color(
        QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.WindowText
    )
    inactive_background = palette.color(
        QtGui.QPalette.ColorGroup.Inactive, QtGui.QPalette.ColorRole.Window
    )
    inactive_foreground = palette.color(
        QtGui.QPalette.ColorGroup.Inactive, QtGui.QPalette.ColorRole.WindowText
    )
    background = overrides.get(role.BACKGROUND, active_background)
    foreground = overrides.get(role.FOREGROUND, active_foreground)
    if inactive_background == active_background:
        inactive_background = background
    inactive_background = overrides.get(
        role.INACTIVE_BACKGROUND, inactive_background
    )
    if inactive_foreground.rgb() == active_foreground.rgb():
        visible_background = _blend(
            palette.color(
                QtGui.QPalette.ColorGroup.Inactive,
                QtGui.QPalette.ColorRole.Window,
            ),
            inactive_background,
            inactive_background.alphaF(),
        )
        inactive_foreground = _blend(visible_background, foreground, 0.4)
    visible_background = _blend(
        active_background, background, background.alphaF()
    )
    resolved = {
        role.BACKGROUND: background,
        role.FOREGROUND: foreground,
        role.INACTIVE_BACKGROUND: inactive_background,
        role.INACTIVE_FOREGROUND: inactive_foreground,
        role.HOVER_BACKGROUND: _blend(visible_background, foreground, 0.08),
        role.HOVER_FOREGROUND: foreground,
        role.PRESSED_BACKGROUND: _blend(visible_background, foreground, 0.12),
        role.PRESSED_FOREGROUND: foreground,
    }
    resolved.update(overrides)
    result = {key: QtGui.QColor(color) for key, color in resolved.items()}
    for key in (
        role.FOREGROUND,
        role.INACTIVE_FOREGROUND,
        role.HOVER_FOREGROUND,
        role.PRESSED_FOREGROUND,
    ):
        result[key].setAlpha(255)
    return result
