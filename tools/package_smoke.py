# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks an installed wheel without requiring a desktop or native runtime.
"""

import importlib.metadata
import importlib.resources
import json
import pathlib

import native_titlebar
from native_titlebar import diagnostics


def main() -> int:
    """Checks installed metadata, imports, and the public typing marker.

    Returns:
        Zero after all checks pass and an environment report is printed.

    Raises:
        RuntimeError: If imports, metadata, or the typing marker are incorrect.
        importlib.metadata.PackageNotFoundError: If the wheel is not installed.
    """
    distribution = importlib.metadata.distribution("pyside6-native-titlebar")
    installed_module = pathlib.Path(
        str(distribution.locate_file("native_titlebar/__init__.py"))
    ).resolve()
    imported_module = pathlib.Path(native_titlebar.__file__).resolve()
    source_package = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "native_titlebar"
    )
    if imported_module != installed_module or imported_module.is_relative_to(
        source_package
    ):
        message = "The imported package must come from the installed wheel."
        raise RuntimeError(message)
    if native_titlebar.__version__ != distribution.version:
        message = "The public version does not match the installed metadata."
        raise RuntimeError(message)
    marker = importlib.resources.files(native_titlebar).joinpath("py.typed")
    if not marker.is_file():
        message = "The installed wheel is missing its py.typed marker."
        raise RuntimeError(message)
    report = diagnostics.environment_report()
    if report["runtime_available"] is not None:
        message = "Inspecting package metadata must not bootstrap the runtime."
        raise RuntimeError(message)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
