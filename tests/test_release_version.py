# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Modding Forge

"""Copyright (c) Modding Forge.

Checks that release validation blocks mismatched or unsafe versions.
"""

import pathlib

import pytest

import native_titlebar
from tools import check_release_version


@pytest.mark.parametrize("release", ["0.2.0", "v0.2.0"])
def test_matching_release(release: str, tmp_path: pathlib.Path) -> None:
    """Accepts plain and v-prefixed versions without executing source code."""
    module = tmp_path / "_version.py"
    module.write_text(
        '__version__ = "0.2.0"\nraise RuntimeError("must not execute")\n',
        encoding="utf-8",
    )
    assert (
        check_release_version.check_release_version(
            release, version_module=module
        )
        == "0.2.0"
    )


@pytest.mark.parametrize(
    "release", ["0.2.1", "refs/tags/v0.2.0", "v0.2.0\nx", ""]
)
def test_mismatched_release(release: str, tmp_path: pathlib.Path) -> None:
    """Rejects versions that do not exactly match the package."""
    module = tmp_path / "_version.py"
    module.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        check_release_version.check_release_version(
            release, version_module=module
        )


@pytest.mark.parametrize(
    "source",
    [
        '__version__ = "0.2.0+local"',
        '__version__ = "not-a-version"',
        '__version__ = "v0.2.0"',
        '__version__ = str("0.2.0")',
        '__version__ = "0.2.0"\n__version__ = "0.2.0"',
        'unrelated = "0.2.0"',
    ],
)
def test_invalid_version_source(source: str, tmp_path: pathlib.Path) -> None:
    """Rejects invalid metadata and computed or ambiguous assignments."""
    module = tmp_path / "_version.py"
    module.write_text(source, encoding="utf-8")
    with pytest.raises(
        (TypeError, ValueError),
        match=r"canonical|Invalid version|literal|exactly once",
    ):
        check_release_version.check_release_version(
            "0.2.0", version_module=module
        )


def test_annotated_prerelease(tmp_path: pathlib.Path) -> None:
    """Accepts a canonical prerelease in an annotated version assignment."""
    module = tmp_path / "_version.py"
    module.write_text('__version__: str = "0.2.0rc1"', encoding="utf-8")
    assert (
        check_release_version.check_release_version(
            "v0.2.0rc1", version_module=module
        )
        == "0.2.0rc1"
    )


def test_workflow_outputs(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Writes the validated version and prerelease flag for downstream jobs."""
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert check_release_version.main([f"v{native_titlebar.__version__}"]) == 0
    assert output.read_text(encoding="utf-8") == (
        f"version={native_titlebar.__version__}\nprerelease=false\n"
    )


def test_invalid_cli_version() -> None:
    """Stops the release job with an error exit code on version mismatch."""
    with pytest.raises(SystemExit) as exc:
        check_release_version.main(["invalid-release"])
    assert exc.value.code == 2
