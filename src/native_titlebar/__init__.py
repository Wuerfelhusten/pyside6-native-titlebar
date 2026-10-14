# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Embeds real Qt widgets beside Windows-managed caption controls.

Create a QApplication, instantiate NativeWindow, and add widgets with
window.titlebar.add_widget(). Window creation requires Windows App Runtime 1.7.
Importing this package does not bootstrap the runtime or create a window.
"""

from native_titlebar import _version
from native_titlebar import errors
from native_titlebar import titlebar
from native_titlebar import window

# Keep the package facade while importing modules, as Google style requires.
GUIThreadError = errors.GUIThreadError
GuiThreadError = errors.GuiThreadError
NativeTitleBarError = errors.NativeTitleBarError
NativeWindow = window.NativeWindow
RuntimeUnavailableError = errors.RuntimeUnavailableError
TitleBar = titlebar.TitleBar
UnsupportedPlatformError = errors.UnsupportedPlatformError
__version__ = _version.__version__

__all__ = [
    "GUIThreadError",
    "GuiThreadError",
    "NativeTitleBarError",
    "NativeWindow",
    "RuntimeUnavailableError",
    "TitleBar",
    "UnsupportedPlatformError",
    "__version__",
]
