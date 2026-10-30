# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Defines the color roles supported by native Windows caption buttons.
"""

import enum


class ButtonColorRole(enum.Enum):
    """Identifies a native caption button color for TitleBar.setButtonColor().

    Colors apply to all three caption buttons. Windows retains the close
    button's system hover and pressed backgrounds. Background colors support
    transparency; Windows ignores alpha in foreground colors.

    Attributes:
        BACKGROUND: Background while the window is active.
        FOREGROUND: Symbol color while the window is active.
        INACTIVE_BACKGROUND: Background while the window is inactive.
        INACTIVE_FOREGROUND: Symbol color while the window is inactive.
        HOVER_BACKGROUND: Background under the pointer.
        HOVER_FOREGROUND: Symbol color under the pointer.
        PRESSED_BACKGROUND: Background while a button is pressed.
        PRESSED_FOREGROUND: Symbol color while a button is pressed.
    """

    BACKGROUND = "button_background_color"
    FOREGROUND = "button_foreground_color"
    INACTIVE_BACKGROUND = "button_inactive_background_color"
    INACTIVE_FOREGROUND = "button_inactive_foreground_color"
    HOVER_BACKGROUND = "button_hover_background_color"
    HOVER_FOREGROUND = "button_hover_foreground_color"
    PRESSED_BACKGROUND = "button_pressed_background_color"
    PRESSED_FOREGROUND = "button_pressed_foreground_color"
