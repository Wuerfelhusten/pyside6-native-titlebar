# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Reports the execution environment without creating a Qt window.
"""

import platform
import struct
import sys

import PySide6
from PySide6 import QtCore

from native_titlebar import _version
from native_titlebar import errors
from native_titlebar import reports
from native_titlebar.platform import windows


def environment_report(
    *, check_runtime: bool = False
) -> reports.EnvironmentReport:
    """Collects JSON-safe package, OS, and runtime information.

    Args:
        check_runtime: Whether to attempt loading Windows App Runtime 1.7.
            This loads native libraries but creates no windows or application.

    Returns:
        A mapping of versions, architecture, runtime availability, and an error
        message. runtime_available is None when no check was requested.
    """
    report: reports.EnvironmentReport = {
        "library": _version.__version__,
        "python": platform.python_version(),
        "python_bits": struct.calcsize("P") * 8,
        "platform": sys.platform,
        "os": platform.platform(),
        "pyside6": PySide6.__version__,
        "qt": QtCore.qVersion(),
        "required_runtime": "1.7",
        "runtime_available": None,
        "error": None,
    }
    if check_runtime:
        try:
            windows.ensure_runtime()
        except errors.NativeTitleBarError as exc:
            report["runtime_available"] = False
            report["error"] = str(exc)
        else:
            report["runtime_available"] = True
    return report
