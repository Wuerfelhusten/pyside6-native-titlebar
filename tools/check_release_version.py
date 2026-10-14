# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Validates release versions without importing Qt or executing package code.
"""

from __future__ import annotations

import argparse
import ast
import os
import pathlib

from packaging import version

_VERSION_MODULE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "native_titlebar"
    / "_version.py"
)


class _Arguments(argparse.Namespace):
    """Contains the release version supplied through the command line."""

    release: str


def _read_version(module: pathlib.Path) -> str:
    """Reads exactly one literal version assignment without executing code."""
    syntax = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    values: list[str] = []
    for statement in syntax.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in targets
        ):
            continue
        value = statement.value
        if not isinstance(value, ast.Constant) or not isinstance(
            value.value, str
        ):
            message = "__version__ must be a literal string."
            raise TypeError(message)
        values.append(value.value)
    if len(values) != 1:
        message = "The version module must define __version__ exactly once."
        raise ValueError(message)
    return values[0]


def check_release_version(
    release: str, *, version_module: pathlib.Path = _VERSION_MODULE
) -> str:
    """Matches a requested release against the build backend's version source.

    Args:
        release: Canonical package version, optionally prefixed with v.
        version_module: Source file containing the literal package version.

    Returns:
        The validated package version without a v prefix.

    Raises:
        ValueError: If versions differ, are malformed, or use a local suffix.
        TypeError: If the version assignment is not a literal string.
        OSError: If the version source cannot be read.
        SyntaxError: If the version source is not valid Python.
    """
    expected = _read_version(version_module)
    parsed = version.Version(expected)
    if str(parsed) != expected or parsed.local is not None:
        message = (
            "The package version must be canonical and have no local suffix."
        )
        raise ValueError(message)
    if release.removeprefix("v") != expected:
        message = (
            f"Release version {release!r} does not match package version "
            f"{expected!r}."
        )
        raise ValueError(message)
    return expected


def main(argv: list[str] | None = None) -> int:
    """Validates a release and emits version outputs for GitHub Actions.

    Args:
        argv: Arguments excluding the executable name, or None for sys.argv.

    Returns:
        Zero after validating the version and writing any workflow outputs.

    Raises:
        SystemExit: If arguments or the requested release version are invalid.
        OSError: If the GitHub Actions output file cannot be written.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", help="Package version or v-prefixed Git tag")
    arguments = parser.parse_args(argv, namespace=_Arguments())
    try:
        checked = check_release_version(arguments.release)
    except (OSError, SyntaxError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        prerelease = str(version.Version(checked).is_prerelease).lower()
        with pathlib.Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"version={checked}\nprerelease={prerelease}\n")
    print(f"Release version {checked} matches the package.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
