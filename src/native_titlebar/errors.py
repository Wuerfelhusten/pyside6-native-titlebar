# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Public exceptions raised by native title bar integration.
"""


class NativeTitleBarError(RuntimeError):
    """Base exception for native integration and environment failures."""


class UnsupportedPlatformError(NativeTitleBarError):
    """The operating system does not support this backend."""


class RuntimeUnavailableError(NativeTitleBarError):
    """The required Windows App Runtime cannot be loaded."""


class GUIThreadError(NativeTitleBarError):
    """A GUI operation was attempted without the QApplication GUI thread."""


# Retain the original public spelling for existing callers.
GuiThreadError = GUIThreadError
